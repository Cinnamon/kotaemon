import re
from collections import defaultdict
from typing import Generator

import numpy as np

from kotaemon.base import AIMessage, Document, HumanMessage, SystemMessage
from kotaemon.llms import PromptTemplate

from .citation import CiteEvidence
from .citation_qa import AnswerWithContextPipeline
from .format_context import EVIDENCE_MODE_FIGURE
from .utils import find_start_end_phrase

MAX_IMAGES = 10
CITATION_TIMEOUT = 5.0

DEFAULT_QA_CITATION_PROMPT = """
Use the following pieces of context to answer the question at the end.
Provide DETAILED ansswer with clear explanation.
Format answer with easy to follow bullets / paragraphs.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Use the same language as the question to response.

CONTEXT:
----
{context}
----

Answer using this format:
CITATION LIST

// the index in this array
CITATION【number】

// output 2 phrase to mark start and end of the relevant span
// each has ~ 6 words
// MUST COPY EXACTLY from the CONTEXT
// NO CHANGE or REPHRASE
// RELEVANT_SPAN_FROM_CONTEXT
START_PHRASE: string
END_PHRASE: string

// When you answer, ensure to add citations from the documents
// in the CONTEXT with a number that corresponds to the answersInText array.
// (in the form [number])
// Try to include the number after each facts / statements you make.
// You can create as many citations as you need.
FINAL ANSWER
string

STRICTLY FOLLOW THIS EXAMPLE:
CITATION LIST

CITATION【1】

START_PHRASE: Known as fixed-size chunking , the traditional
END_PHRASE: not degrade the final retrieval performance.

CITATION【2】

START_PHRASE: Fixed-size Chunker This is our baseline chunker
END_PHRASE: this shows good retrieval quality.

FINAL ANSWER
An alternative to semantic chunking is fixed-size chunking. This traditional method involves splitting documents into chunks of a predetermined or user-specified size, regardless of semantic content, which is computationally efficient【1】. However, it may result in the fragmentation of semantically related content, thereby potentially degrading retrieval performance【2】.

QUESTION: {question}\n
ANSWER:
"""  # noqa


class AnswerWithInlineCitation(AnswerWithContextPipeline):
    """Answer the question based on the evidence with inline citation"""

    qa_citation_template: str = DEFAULT_QA_CITATION_PROMPT

    def get_prompt(self, question, evidence, evidence_mode: int):
        """Prepare the prompt and other information for LLM"""
        prompt_template = PromptTemplate(self.qa_citation_template)

        prompt = prompt_template.populate(
            context=evidence,
            question=question,
            safe=False,
        )

        return prompt, evidence

    def answer_to_citations(self, answer):
        evidences = []
        lines = answer.split("\n")
        for line in lines:
            for keyword in ["START_PHRASE:", "END_PHRASE:"]:
                if line.startswith(keyword):
                    evidences.append(line[len(keyword) :].strip())

        return CiteEvidence(evidences=evidences)

    def replace_citation_with_link(self, answer: str):
        # Define the regex pattern to match 【number】
        pattern = r"【\d+】"
        matches = re.finditer(pattern, answer)

        matched_citations = set()
        for match in matches:
            citation = match.group()
            matched_citations.add(citation)

        for citation in matched_citations:
            print("Found citation:", citation)
            answer = answer.replace(
                citation,
                (
                    "<a href='#' class='citation' "
                    f"id='mark-{citation[1:-1]}'>{citation}</a>"
                ),
            )

        print("Replaced answer:", answer)
        return answer

    def stream(  # type: ignore
        self,
        question: str,
        evidence: str,
        evidence_mode: int = 0,
        images: list[str] = [],
        **kwargs,
    ) -> Generator[Document, None, Document]:
        history = kwargs.get("history", [])
        print(f"Got {len(images)} images")
        # check if evidence exists, use QA prompt
        if evidence:
            prompt, evidence = self.get_prompt(question, evidence, evidence_mode)
        else:
            prompt = question

        output = ""
        logprobs = []

        citation = None
        mindmap = None

        messages = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        for human, ai in history[-self.n_last_interactions :]:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))

        if self.use_multimodal and evidence_mode == EVIDENCE_MODE_FIGURE:
            # create image message:
            messages.append(
                HumanMessage(
                    content=[
                        {"type": "text", "text": prompt},
                    ]
                    + [
                        {
                            "type": "image_url",
                            "image_url": {"url": image},
                        }
                        for image in images[:MAX_IMAGES]
                    ],
                )
            )
        else:
            # append main prompt
            messages.append(HumanMessage(content=prompt))

        START_ANSWER = "FINAL ANSWER"
        start_of_answer = True
        final_answer = ""

        try:
            # try streaming first
            print("Trying LLM streaming")
            for out_msg in self.llm.stream(messages):
                if START_ANSWER in output:
                    final_answer += (
                        out_msg.text.lstrip() if start_of_answer else out_msg.text
                    )
                    start_of_answer = False
                    yield Document(channel="chat", content=out_msg.text)

                output += out_msg.text
                logprobs += out_msg.logprobs
        except NotImplementedError:
            print("Streaming is not supported, falling back to normal processing")
            output = self.llm(messages).text
            yield Document(channel="chat", content=output)

        if logprobs:
            qa_score = np.exp(np.average(logprobs))
        else:
            qa_score = None

        citation = self.answer_to_citations(output)

        print(output)
        # convert citation to link
        answer = Document(
            text=final_answer,
            metadata={
                "citation_viz": self.enable_citation_viz,
                "mindmap": mindmap,
                "citation": citation,
                "qa_score": qa_score,
            },
        )

        # yield the final answer
        final_answer = self.replace_citation_with_link(final_answer)
        yield Document(channel="chat", content=None)
        yield Document(channel="chat", content=final_answer)

        return answer

    def match_evidence_with_context(self, answer, docs) -> dict[str, list[dict]]:
        """Match the evidence with the context"""
        spans: dict[str, list[dict]] = defaultdict(list)

        if not answer.metadata["citation"]:
            return spans

        evidences = answer.metadata["citation"].evidences

        for start_idx in range(0, len(evidences), 2):
            start_phrase, end_phrase = evidences[start_idx : start_idx + 2]
            best_match = None
            best_match_length = 0
            best_match_doc_idx = None

            for doc in docs:
                match, match_length = find_start_end_phrase(
                    start_phrase, end_phrase, doc.text
                )
                if best_match is None or (
                    match is not None and match_length > best_match_length
                ):
                    best_match = match
                    best_match_length = match_length
                    best_match_doc_idx = doc.doc_id

            if best_match is not None and best_match_doc_idx is not None:
                spans[best_match_doc_idx].append(
                    {
                        "start": best_match[0],
                        "end": best_match[1],
                        "idx": start_idx // 2,  # implicitly set from the start_idx
                    }
                )
        return spans
