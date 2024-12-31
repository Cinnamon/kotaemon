import threading
from collections import defaultdict
from typing import Generator

import numpy as np
from decouple import config
from theflow.settings import settings as flowsettings

from kotaemon.base import (
    AIMessage,
    BaseComponent,
    Document,
    HumanMessage,
    Node,
    SystemMessage,
)
from kotaemon.llms import ChatLLM, PromptTemplate

from .citation import CitationPipeline
from .format_context import (
    EVIDENCE_MODE_FIGURE,
    EVIDENCE_MODE_TABLE,
    EVIDENCE_MODE_TEXT,
)
from .utils import find_text

try:
    from ktem.llms.manager import llms
    from ktem.reasoning.prompt_optimization.mindmap import CreateMindmapPipeline
    from ktem.utils.render import Render
except ImportError:
    raise ImportError("Please install `ktem` to use this component")

MAX_IMAGES = 10
CITATION_TIMEOUT = 5.0
CONTEXT_RELEVANT_WARNING_SCORE = config(
    "CONTEXT_RELEVANT_WARNING_SCORE", 0.3, cast=float
)

DEFAULT_QA_TEXT_PROMPT = (
    "Use the following pieces of context to answer the question at the end in detail with clear explanation. "  # noqa: E501
    "If you don't know the answer, just say that you don't know, don't try to "
    "make up an answer. Give answer in "
    "{lang}.\n\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)

DEFAULT_QA_TABLE_PROMPT = (
    "Use the given context: texts, tables, and figures below to answer the question, "
    "then provide answer with clear explanation."
    "If you don't know the answer, just say that you don't know, "
    "don't try to make up an answer. Give answer in {lang}.\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)  # noqa

DEFAULT_QA_CHATBOT_PROMPT = (
    "Pick the most suitable chatbot scenarios to answer the question at the end, "
    "output the provided answer text. If you don't know the answer, "
    "just say that you don't know. Keep the answer as concise as possible. "
    "Give answer in {lang}.\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Answer:"
)  # noqa

DEFAULT_QA_FIGURE_PROMPT = (
    "Use the given context: texts, tables, and figures below to answer the question. "
    "If you don't know the answer, just say that you don't know. "
    "Give answer in {lang}.\n\n"
    "Context: \n"
    "{context}\n"
    "Question: {question}\n"
    "Answer: "
)  # noqa


class AnswerWithContextPipeline(BaseComponent):
    """Answer the question based on the evidence

    Args:
        llm: the language model to generate the answer
        citation_pipeline: generates citation from the evidence
        qa_template: the prompt template for LLM to generate answer (refer to
            evidence_mode)
        qa_table_template: the prompt template for LLM to generate answer for table
            (refer to evidence_mode)
        qa_chatbot_template: the prompt template for LLM to generate answer for
            pre-made scenarios (refer to evidence_mode)
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    vlm_endpoint: str = getattr(flowsettings, "KH_VLM_ENDPOINT", "")
    use_multimodal: bool = getattr(flowsettings, "KH_REASONINGS_USE_MULTIMODAL", True)
    citation_pipeline: CitationPipeline = Node(
        default_callback=lambda _: CitationPipeline(llm=llms.get_default())
    )
    create_mindmap_pipeline: CreateMindmapPipeline = Node(
        default_callback=lambda _: CreateMindmapPipeline(llm=llms.get_default())
    )

    qa_template: str = DEFAULT_QA_TEXT_PROMPT
    qa_table_template: str = DEFAULT_QA_TABLE_PROMPT
    qa_chatbot_template: str = DEFAULT_QA_CHATBOT_PROMPT
    qa_figure_template: str = DEFAULT_QA_FIGURE_PROMPT

    enable_citation: bool = False
    enable_mindmap: bool = False
    enable_citation_viz: bool = False

    system_prompt: str = ""
    lang: str = "English"  # support English and Japanese
    n_last_interactions: int = 5

    def get_prompt(self, question, evidence, evidence_mode: int):
        """Prepare the prompt and other information for LLM"""
        if evidence_mode == EVIDENCE_MODE_TEXT:
            prompt_template = PromptTemplate(self.qa_template)
        elif evidence_mode == EVIDENCE_MODE_TABLE:
            prompt_template = PromptTemplate(self.qa_table_template)
        elif evidence_mode == EVIDENCE_MODE_FIGURE:
            if self.use_multimodal:
                prompt_template = PromptTemplate(self.qa_figure_template)
            else:
                prompt_template = PromptTemplate(self.qa_template)
        else:
            prompt_template = PromptTemplate(self.qa_chatbot_template)

        prompt = prompt_template.populate(
            context=evidence,
            question=question,
            lang=self.lang,
        )

        return prompt, evidence

    def run(
        self, question: str, evidence: str, evidence_mode: int = 0, **kwargs
    ) -> Document:
        return self.invoke(question, evidence, evidence_mode, **kwargs)

    def invoke(
        self,
        question: str,
        evidence: str,
        evidence_mode: int = 0,
        images: list[str] = [],
        **kwargs,
    ) -> Document:
        raise NotImplementedError

    async def ainvoke(  # type: ignore
        self,
        question: str,
        evidence: str,
        evidence_mode: int = 0,
        images: list[str] = [],
        **kwargs,
    ) -> Document:
        """Answer the question based on the evidence

        In addition to the question and the evidence, this method also take into
        account evidence_mode. The evidence_mode tells which kind of evidence is.
        The kind of evidence affects:
            1. How the evidence is represented.
            2. The prompt to generate the answer.

        By default, the evidence_mode is 0, which means the evidence is plain text with
        no particular semantic representation. The evidence_mode can be:
            1. "table": There will be HTML markup telling that there is a table
                within the evidence.
            2. "chatbot": There will be HTML markup telling that there is a chatbot.
                This chatbot is a scenario, extracted from an Excel file, where each
                row corresponds to an interaction.

        Args:
            question: the original question posed by user
            evidence: the text that contain relevant information to answer the question
                (determined by retrieval pipeline)
            evidence_mode: the mode of evidence, 0 for text, 1 for table, 2 for chatbot
        """
        raise NotImplementedError

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

        # retrieve the citation
        citation = None
        mindmap = None

        def citation_call():
            nonlocal citation
            citation = self.citation_pipeline(context=evidence, question=question)

        def mindmap_call():
            nonlocal mindmap
            mindmap = self.create_mindmap_pipeline(context=evidence, question=question)

        citation_thread = None
        mindmap_thread = None

        # execute function call in thread
        if evidence:
            if self.enable_citation:
                citation_thread = threading.Thread(target=citation_call)
                citation_thread.start()

            if self.enable_mindmap:
                mindmap_thread = threading.Thread(target=mindmap_call)
                mindmap_thread.start()

        output = ""
        logprobs = []

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

        try:
            # try streaming first
            print("Trying LLM streaming")
            for out_msg in self.llm.stream(messages):
                output += out_msg.text
                logprobs += out_msg.logprobs
                yield Document(channel="chat", content=out_msg.text)
        except NotImplementedError:
            print("Streaming is not supported, falling back to normal processing")
            output = self.llm(messages).text
            yield Document(channel="chat", content=output)

        if logprobs:
            qa_score = np.exp(np.average(logprobs))
        else:
            qa_score = None

        if citation_thread:
            citation_thread.join(timeout=CITATION_TIMEOUT)
        if mindmap_thread:
            mindmap_thread.join(timeout=CITATION_TIMEOUT)

        answer = Document(
            text=output,
            metadata={
                "citation_viz": self.enable_citation_viz,
                "mindmap": mindmap,
                "citation": citation,
                "qa_score": qa_score,
            },
        )

        return answer

    def match_evidence_with_context(self, answer, docs) -> dict[str, list[dict]]:
        """Match the evidence with the context"""
        spans: dict[str, list[dict]] = defaultdict(list)

        if not answer.metadata["citation"]:
            return spans

        evidences = answer.metadata["citation"].evidences
        for quote in evidences:
            matched_excerpts = []
            for doc in docs:
                matches = find_text(quote, doc.text)

                for start, end in matches:
                    if "|" not in doc.text[start:end]:
                        spans[doc.doc_id].append(
                            {
                                "start": start,
                                "end": end,
                            }
                        )
                        matched_excerpts.append(doc.text[start:end])

            # print("Matched citation:", quote, matched_excerpts),
        return spans

    def prepare_citations(self, answer, docs) -> tuple[list[Document], list[Document]]:
        """Prepare the citations to show on the UI"""
        with_citation, without_citation = [], []
        has_llm_score = any("llm_trulens_score" in doc.metadata for doc in docs)

        spans = self.match_evidence_with_context(answer, docs)
        id2docs = {doc.doc_id: doc for doc in docs}
        not_detected = set(id2docs.keys()) - set(spans.keys())

        # render highlight spans
        for _id, ss in spans.items():
            if not ss:
                not_detected.add(_id)
                continue
            cur_doc = id2docs[_id]
            highlight_text = ""

            ss = sorted(ss, key=lambda x: x["start"])
            last_end = 0
            text = cur_doc.text[: ss[0]["start"]]

            for idx, span in enumerate(ss):
                # prevent overlapping between span
                span_start = max(last_end, span["start"])
                span_end = max(last_end, span["end"])

                to_highlight = cur_doc.text[span_start:span_end]
                last_end = span_end

                # append to highlight on PDF viewer
                highlight_text += (" " if highlight_text else "") + to_highlight

                span_idx = span.get("idx", None)
                if span_idx is not None:
                    to_highlight = f"【{span_idx}】" + to_highlight

                text += Render.highlight(
                    to_highlight,
                    elem_id=str(span_idx) if span_idx is not None else None,
                )
                if idx < len(ss) - 1:
                    text += cur_doc.text[span["end"] : ss[idx + 1]["start"]]

            text += cur_doc.text[ss[-1]["end"] :]
            # add to display list
            with_citation.append(
                Document(
                    channel="info",
                    content=Render.collapsible_with_header_score(
                        cur_doc,
                        override_text=text,
                        highlight_text=highlight_text,
                        open_collapsible=True,
                    ),
                )
            )

        print("Got {} cited docs".format(len(with_citation)))

        sorted_not_detected_items_with_scores = [
            (id_, id2docs[id_].metadata.get("llm_trulens_score", 0.0))
            for id_ in not_detected
        ]
        sorted_not_detected_items_with_scores.sort(key=lambda x: x[1], reverse=True)

        for id_, _ in sorted_not_detected_items_with_scores:
            doc = id2docs[id_]
            doc_score = doc.metadata.get("llm_trulens_score", 0.0)
            is_open = not has_llm_score or (
                doc_score
                > CONTEXT_RELEVANT_WARNING_SCORE
                # and len(with_citation) == 0
            )
            without_citation.append(
                Document(
                    channel="info",
                    content=Render.collapsible_with_header_score(
                        doc, open_collapsible=is_open
                    ),
                )
            )
        return with_citation, without_citation
