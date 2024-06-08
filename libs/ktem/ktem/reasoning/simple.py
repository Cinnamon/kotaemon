import asyncio
import html
import logging
import re
from collections import defaultdict
from functools import partial
from typing import Generator

import tiktoken
from ktem.llms.manager import llms
from ktem.utils.render import Render
from theflow.settings import settings as flowsettings

from kotaemon.base import (
    AIMessage,
    BaseComponent,
    Document,
    HumanMessage,
    Node,
    RetrievedDocument,
    SystemMessage,
)
from kotaemon.indices.qa.citation import CitationPipeline
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.llms import ChatLLM, PromptTemplate
from kotaemon.loaders.utils.gpt4v import generate_gpt4v, stream_gpt4v

from .base import BaseReasoning

logger = logging.getLogger(__name__)

EVIDENCE_MODE_TEXT = 0
EVIDENCE_MODE_TABLE = 1
EVIDENCE_MODE_CHATBOT = 2
EVIDENCE_MODE_FIGURE = 3


class PrepareEvidencePipeline(BaseComponent):
    """Prepare the evidence text from the list of retrieved documents

    This step usually happens after `DocumentRetrievalPipeline`.

    Args:
        trim_func: a callback function or a BaseComponent, that splits a large
            chunk of text into smaller ones. The first one will be retained.
    """

    trim_func: TokenSplitter = TokenSplitter.withx(
        chunk_size=3000,
        chunk_overlap=0,
        separator=" ",
        tokenizer=partial(
            tiktoken.encoding_for_model("gpt-3.5-turbo").encode,
            allowed_special=set(),
            disallowed_special="all",
        ),
    )

    def run(self, docs: list[RetrievedDocument]) -> Document:
        evidence = ""
        table_found = 0
        evidence_mode = EVIDENCE_MODE_TEXT

        for _id, retrieved_item in enumerate(docs):
            retrieved_content = ""
            page = retrieved_item.metadata.get("page_label", None)
            source = filename = retrieved_item.metadata.get("file_name", "-")
            if page:
                source += f" (Page {page})"
            if retrieved_item.metadata.get("type", "") == "table":
                evidence_mode = EVIDENCE_MODE_TABLE
                if table_found < 5:
                    retrieved_content = retrieved_item.metadata.get("table_origin", "")
                    if retrieved_content not in evidence:
                        table_found += 1
                        evidence += (
                            f"<br><b>Table from {source}</b>\n"
                            + retrieved_content
                            + "\n<br>"
                        )
            elif retrieved_item.metadata.get("type", "") == "chatbot":
                evidence_mode = EVIDENCE_MODE_CHATBOT
                retrieved_content = retrieved_item.metadata["window"]
                evidence += (
                    f"<br><b>Chatbot scenario from {filename} (Row {page})</b>\n"
                    + retrieved_content
                    + "\n<br>"
                )
            elif retrieved_item.metadata.get("type", "") == "image":
                evidence_mode = EVIDENCE_MODE_FIGURE
                retrieved_content = retrieved_item.metadata.get("image_origin", "")
                retrieved_caption = html.escape(retrieved_item.get_content())
                evidence += (
                    f"<br><b>Figure from {source}</b>\n"
                    + f"<img width='85%' src='{retrieved_content}' "
                    + f"alt='{retrieved_caption}'/>"
                    + "\n<br>"
                )
            else:
                if "window" in retrieved_item.metadata:
                    retrieved_content = retrieved_item.metadata["window"]
                else:
                    retrieved_content = retrieved_item.text
                retrieved_content = retrieved_content.replace("\n", " ")
                if retrieved_content not in evidence:
                    evidence += (
                        f"<br><b>Content from {source}: </b> "
                        + retrieved_content
                        + " \n<br>"
                    )

            print("Retrieved #{}: {}".format(_id, retrieved_content))
            print(retrieved_item.metadata)
            print("Score", retrieved_item.metadata.get("relevance_score", None))

        if evidence_mode != EVIDENCE_MODE_FIGURE:
            # trim context by trim_len
            print("len (original)", len(evidence))
            if evidence:
                texts = self.trim_func([Document(text=evidence)])
                evidence = texts[0].text
                print("len (trimmed)", len(evidence))

        print(f"PrepareEvidence with input {docs}\nOutput: {evidence}\n")

        return Document(content=(evidence_mode, evidence))


DEFAULT_QA_TEXT_PROMPT = (
    "Use the following pieces of context to answer the question at the end. "
    "If you don't know the answer, just say that you don't know, don't try to "
    "make up an answer. Keep the answer as concise as possible. Give answer in "
    "{lang}.\n\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)

DEFAULT_QA_TABLE_PROMPT = (
    "List all rows (row number) from the table context that related to the question, "
    "then provide detail answer with clear explanation and citations. "
    "If you don't know the answer, just say that you don't know, "
    "don't try to make up an answer. Give answer in {lang}.\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)

DEFAULT_QA_CHATBOT_PROMPT = (
    "Pick the most suitable chatbot scenarios to answer the question at the end, "
    "output the provided answer text. If you don't know the answer, "
    "just say that you don't know. Keep the answer as concise as possible. "
    "Give answer in {lang}.\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Answer:"
)

DEFAULT_QA_FIGURE_PROMPT = (
    "Use the given context: texts, tables, and figures below to answer the question. "
    "If you don't know the answer, just say that you don't know. "
    "Give answer in {lang}.\n\n"
    "Context: \n"
    "{context}\n"
    "Question: {question}\n"
    "Answer: "
)

DEFAULT_REWRITE_PROMPT = (
    "Given the following question, rephrase and expand it "
    "to help you do better answering. Maintain all information "
    "in the original question. Keep the question as concise as possible. "
    "Give answer in {lang}\n"
    "Original question: {question}\n"
    "Rephrased question: "
)


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
    citation_pipeline: CitationPipeline = Node(
        default_callback=lambda _: CitationPipeline(llm=llms.get_default())
    )

    qa_template: str = DEFAULT_QA_TEXT_PROMPT
    qa_table_template: str = DEFAULT_QA_TABLE_PROMPT
    qa_chatbot_template: str = DEFAULT_QA_CHATBOT_PROMPT
    qa_figure_template: str = DEFAULT_QA_FIGURE_PROMPT

    enable_citation: bool = False
    system_prompt: str = ""
    lang: str = "English"  # support English and Japanese
    n_last_interactions: int = 5

    def get_prompt(self, question, evidence, evidence_mode: int):
        """Prepare the prompt and other information for LLM"""
        images = []

        if evidence_mode == EVIDENCE_MODE_TEXT:
            prompt_template = PromptTemplate(self.qa_template)
        elif evidence_mode == EVIDENCE_MODE_TABLE:
            prompt_template = PromptTemplate(self.qa_table_template)
        elif evidence_mode == EVIDENCE_MODE_FIGURE:
            prompt_template = PromptTemplate(self.qa_figure_template)
        else:
            prompt_template = PromptTemplate(self.qa_chatbot_template)

        if evidence_mode == EVIDENCE_MODE_FIGURE:
            # isolate image from evidence
            evidence, images = self.extract_evidence_images(evidence)
            prompt = prompt_template.populate(
                context=evidence,
                question=question,
                lang=self.lang,
            )
        else:
            prompt = prompt_template.populate(
                context=evidence,
                question=question,
                lang=self.lang,
            )

        return prompt, images

    def run(
        self, question: str, evidence: str, evidence_mode: int = 0, **kwargs
    ) -> Document:
        return self.invoke(question, evidence, evidence_mode, **kwargs)

    def invoke(
        self, question: str, evidence: str, evidence_mode: int = 0, **kwargs
    ) -> Document:
        history = kwargs.get("history", [])
        prompt, images = self.get_prompt(question, evidence, evidence_mode)

        output = ""
        if evidence_mode == EVIDENCE_MODE_FIGURE:
            output = generate_gpt4v(self.vlm_endpoint, images, prompt, max_tokens=768)
        else:
            messages = []
            if self.system_prompt:
                messages.append(SystemMessage(content=self.system_prompt))
            for human, ai in history[-self.n_last_interactions :]:
                messages.append(HumanMessage(content=human))
                messages.append(AIMessage(content=ai))
            messages.append(HumanMessage(content=prompt))
            output = self.llm(messages).text

        # retrieve the citation
        citation = None
        if evidence and self.enable_citation:
            citation = self.citation_pipeline.invoke(
                context=evidence, question=question
            )

        answer = Document(text=output, metadata={"citation": citation})

        return answer

    async def ainvoke(  # type: ignore
        self, question: str, evidence: str, evidence_mode: int = 0, **kwargs
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
        history = kwargs.get("history", [])
        prompt, images = self.get_prompt(question, evidence, evidence_mode)

        citation_task = None
        if evidence and self.enable_citation:
            citation_task = asyncio.create_task(
                self.citation_pipeline.ainvoke(context=evidence, question=question)
            )
            print("Citation task created")

        output = ""
        if evidence_mode == EVIDENCE_MODE_FIGURE:
            for text in stream_gpt4v(self.vlm_endpoint, images, prompt, max_tokens=768):
                output += text
                self.report_output(Document(channel="chat", content=text))
                await asyncio.sleep(0)
        else:
            messages = []
            if self.system_prompt:
                messages.append(SystemMessage(content=self.system_prompt))
            for human, ai in history[-self.n_last_interactions :]:
                messages.append(HumanMessage(content=human))
                messages.append(AIMessage(content=ai))
            messages.append(HumanMessage(content=prompt))

            try:
                # try streaming first
                print("Trying LLM streaming")
                for text in self.llm.stream(messages):
                    output += text.text
                    self.report_output(Document(content=text.text, channel="chat"))
                    await asyncio.sleep(0)
            except NotImplementedError:
                print("Streaming is not supported, falling back to normal processing")
                output = self.llm(messages).text
                self.report_output(Document(content=output, channel="chat"))

        # retrieve the citation
        print("Waiting for citation task")
        if citation_task is not None:
            citation = await citation_task
        else:
            citation = None

        answer = Document(text=output, metadata={"citation": citation})

        return answer

    def stream(  # type: ignore
        self, question: str, evidence: str, evidence_mode: int = 0, **kwargs
    ) -> Generator[Document, None, Document]:
        history = kwargs.get("history", [])
        prompt, images = self.get_prompt(question, evidence, evidence_mode)

        output = ""
        if evidence_mode == EVIDENCE_MODE_FIGURE:
            for text in stream_gpt4v(self.vlm_endpoint, images, prompt, max_tokens=768):
                output += text
                yield Document(channel="chat", content=text)
        else:
            messages = []
            if self.system_prompt:
                messages.append(SystemMessage(content=self.system_prompt))
            for human, ai in history[-self.n_last_interactions :]:
                messages.append(HumanMessage(content=human))
                messages.append(AIMessage(content=ai))
            messages.append(HumanMessage(content=prompt))

            try:
                # try streaming first
                print("Trying LLM streaming")
                for text in self.llm.stream(messages):
                    output += text.text
                    yield Document(channel="chat", content=text.text)
            except NotImplementedError:
                print("Streaming is not supported, falling back to normal processing")
                output = self.llm(messages).text
                yield Document(channel="chat", content=output)

        # retrieve the citation
        citation = None
        if evidence and self.enable_citation:
            citation = self.citation_pipeline(context=evidence, question=question)

        answer = Document(text=output, metadata={"citation": citation})

        return answer

    def extract_evidence_images(self, evidence: str):
        """Util function to extract and isolate images from context/evidence"""
        image_pattern = r"src='(data:image\/[^;]+;base64[^']+)'"
        matches = re.findall(image_pattern, evidence)
        context = re.sub(image_pattern, "", evidence)
        return context, matches


class RewriteQuestionPipeline(BaseComponent):
    """Rewrite user question

    Args:
        llm: the language model to rewrite question
        rewrite_template: the prompt template for llm to paraphrase a text input
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())
    rewrite_template: str = DEFAULT_REWRITE_PROMPT

    lang: str = "English"

    def run(self, question: str) -> Document:  # type: ignore
        prompt_template = PromptTemplate(self.rewrite_template)
        prompt = prompt_template.populate(question=question, lang=self.lang)
        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content=prompt),
        ]
        return self.llm(messages)


class AddQueryContextPipeline(BaseComponent):

    n_last_interactions: int = 5
    llm: ChatLLM = Node(default_callback=lambda _: llms.get_default())

    def run(self, question: str, history: list) -> Document:
        messages = [
            SystemMessage(
                content="Below is a history of the conversation so far, and a new "
                "question asked by the user that needs to be answered by searching "
                "in a knowledge base.\nYou have access to a Search index "
                "with 100's of documents.\nGenerate a search query based on the "
                "conversation and the new question.\nDo not include cited source "
                "filenames and document names e.g info.txt or doc.pdf in the search "
                "query terms.\nDo not include any text inside [] or <<>> in the "
                "search query terms.\nDo not include any special characters like "
                "'+'.\nIf the question is not in English, rewrite the query in "
                "the language used in the question.\n If the question contains enough "
                "information, return just the number 1\n If it's unnecessary to do "
                "the searching, return just the number 0."
            ),
            HumanMessage(content="How did crypto do last year?"),
            AIMessage(
                content="Summarize Cryptocurrency Market Dynamics from last year"
            ),
            HumanMessage(content="What are my health plans?"),
            AIMessage(content="Show available health plans"),
        ]
        for human, ai in history[-self.n_last_interactions :]:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))

        messages.append(HumanMessage(content=f"Generate search query for: {question}"))

        resp = self.llm(messages).text
        if resp == "0":
            return Document(content="")

        if resp == "1":
            return Document(content=question)

        return Document(content=resp)


class FullQAPipeline(BaseReasoning):
    """Question answering pipeline. Handle from question to answer"""

    class Config:
        allow_extra = True

    retrievers: list[BaseComponent]

    evidence_pipeline: PrepareEvidencePipeline = PrepareEvidencePipeline.withx()
    answering_pipeline: AnswerWithContextPipeline = AnswerWithContextPipeline.withx()
    rewrite_pipeline: RewriteQuestionPipeline = RewriteQuestionPipeline.withx()
    add_query_context: AddQueryContextPipeline = AddQueryContextPipeline.withx()
    trigger_context: int = 150
    use_rewrite: bool = False

    def retrieve(
        self, message: str, history: list
    ) -> tuple[list[RetrievedDocument], list[Document]]:
        """Retrieve the documents based on the message"""
        if len(message) < self.trigger_context:
            # prefer adding context for short user questions, avoid adding context for
            # long questions, as they are likely to contain enough information
            # plus, avoid the situation where the original message is already too long
            # for the model to handle
            query = self.add_query_context(message, history).content
        else:
            query = message
        print(f"Rewritten query: {query}")
        if not query:
            # TODO: previously return [], [] because we think this message as something
            # like "Hello", "I need help"...
            query = message

        docs, doc_ids = [], []
        for idx, retriever in enumerate(self.retrievers):
            retriever_node = self._prepare_child(retriever, f"retriever_{idx}")
            for doc in retriever_node(text=query):
                if doc.doc_id not in doc_ids:
                    docs.append(doc)
                    doc_ids.append(doc.doc_id)

        info = []
        for doc in docs:
            if doc.metadata.get("type", "") == "image":
                info.append(
                    Document(
                        channel="info",
                        content=Render.collapsible(
                            header=doc.metadata["file_name"],
                            content=Render.image(
                                url=doc.metadata["image_origin"], text=doc.text
                            ),
                            open=True,
                        ),
                    )
                )
            else:
                info.append(
                    Document(
                        channel="info",
                        content=Render.collapsible(
                            header=doc.metadata["file_name"],
                            content=Render.table(doc.text),
                            open=True,
                        ),
                    )
                )

        return docs, info

    def prepare_citations(self, answer, docs) -> tuple[list[Document], list[Document]]:
        """Prepare the citations to show on the UI"""
        with_citation, without_citation = [], []
        spans = defaultdict(list)

        if answer.metadata["citation"] is not None:
            for fact_with_evidence in answer.metadata["citation"].answer:
                for quote in fact_with_evidence.substring_quote:
                    for doc in docs:
                        start_idx = doc.text.find(quote)
                        if start_idx == -1:
                            continue

                        end_idx = start_idx + len(quote)

                        current_idx = start_idx
                        if "|" not in doc.text[start_idx:end_idx]:
                            spans[doc.doc_id].append(
                                {"start": start_idx, "end": end_idx}
                            )
                        else:
                            while doc.text[current_idx:end_idx].find("|") != -1:
                                match_idx = doc.text[current_idx:end_idx].find("|")
                                spans[doc.doc_id].append(
                                    {
                                        "start": current_idx,
                                        "end": current_idx + match_idx,
                                    }
                                )
                                current_idx += match_idx + 2
                                if current_idx > end_idx:
                                    break
                        break

        id2docs = {doc.doc_id: doc for doc in docs}
        not_detected = set(id2docs.keys()) - set(spans.keys())
        for id, ss in spans.items():
            if not ss:
                not_detected.add(id)
                continue
            ss = sorted(ss, key=lambda x: x["start"])
            text = id2docs[id].text[: ss[0]["start"]]
            for idx, span in enumerate(ss):
                text += Render.highlight(id2docs[id].text[span["start"] : span["end"]])
                if idx < len(ss) - 1:
                    text += id2docs[id].text[span["end"] : ss[idx + 1]["start"]]
            text += id2docs[id].text[ss[-1]["end"] :]
            with_citation.append(
                Document(
                    channel="info",
                    content=Render.collapsible(
                        header=(
                            f'{id2docs[id].metadata["file_name"]}<br>'
                            "<b>Relevance score:</b>"
                            f' {id2docs[id].metadata.get("relevance_score")}'
                        ),
                        content=Render.table(text),
                        open=True,
                    ),
                )
            )

        for id_ in list(not_detected):
            doc = id2docs[id_]
            if doc.metadata.get("type", "") == "image":
                without_citation.append(
                    Document(
                        channel="info",
                        content=Render.collapsible(
                            header=(
                                f'{doc.metadata["file_name"]}<br>'
                                "<b>Relevance score:</b>"
                                f' {doc.metadata.get("relevance_score")}'
                            ),
                            content=Render.image(
                                url=doc.metadata["image_origin"], text=doc.text
                            ),
                            open=True,
                        ),
                    )
                )
            else:
                without_citation.append(
                    Document(
                        channel="info",
                        content=Render.collapsible(
                            header=(
                                f'{doc.metadata["file_name"]}<br>'
                                "<b>Relevance score:</b>"
                                f' {doc.metadata.get("relevance_score")}'
                            ),
                            content=Render.table(doc.text),
                            open=True,
                        ),
                    )
                )
        return with_citation, without_citation

    async def ainvoke(  # type: ignore
        self, message: str, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Document:  # type: ignore
        if self.use_rewrite:
            rewrite = await self.rewrite_pipeline(question=message)
            message = rewrite.text

        docs, infos = self.retrieve(message, history)
        for _ in infos:
            self.report_output(_)
        await asyncio.sleep(0.1)

        evidence_mode, evidence = self.evidence_pipeline(docs).content
        answer = await self.answering_pipeline(
            question=message,
            history=history,
            evidence=evidence,
            evidence_mode=evidence_mode,
            conv_id=conv_id,
            **kwargs,
        )

        # show the evidence
        with_citation, without_citation = self.prepare_citations(answer, docs)
        if not with_citation and not without_citation:
            self.report_output(Document(channel="info", content="No evidence found.\n"))
        else:
            self.report_output(Document(channel="info", content=None))
            for _ in with_citation:
                self.report_output(_)
            if without_citation:
                self.report_output(
                    Document(
                        channel="info",
                        content="Retrieved segments without matching evidence:\n",
                    )
                )
                for _ in without_citation:
                    self.report_output(_)

        self.report_output(None)
        return answer

    def stream(  # type: ignore
        self, message: str, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Generator[Document, None, Document]:
        if self.use_rewrite:
            message = self.rewrite_pipeline(question=message).text

        # should populate the context
        docs, infos = self.retrieve(message, history)
        for _ in infos:
            yield _

        evidence_mode, evidence = self.evidence_pipeline(docs).content
        answer = yield from self.answering_pipeline.stream(
            question=message,
            history=history,
            evidence=evidence,
            evidence_mode=evidence_mode,
            conv_id=conv_id,
            **kwargs,
        )

        # show the evidence
        with_citation, without_citation = self.prepare_citations(answer, docs)
        if not with_citation and not without_citation:
            yield Document(channel="info", content="No evidence found.\n")
        else:
            yield Document(channel="info", content=None)
            for _ in with_citation:
                yield _
            if without_citation:
                yield Document(
                    channel="info",
                    content="Retrieved segments without matching evidence:\n",
                )
                for _ in without_citation:
                    yield _

        return answer

    @classmethod
    def get_pipeline(cls, settings, states, retrievers):
        """Get the reasoning pipeline

        Args:
            settings: the settings for the pipeline
            retrievers: the retrievers to use
        """
        prefix = f"reasoning.options.{cls.get_info()['id']}"
        pipeline = cls(retrievers=retrievers)

        llm_name = settings.get(f"{prefix}.llm", None)
        llm = llms.get(llm_name, llms.get_default())

        # answering pipeline configuration
        answer_pipeline = pipeline.answering_pipeline
        answer_pipeline.llm = llm
        answer_pipeline.citation_pipeline.llm = llm
        answer_pipeline.n_last_interactions = settings[f"{prefix}.n_last_interactions"]
        answer_pipeline.enable_citation = settings[f"{prefix}.highlight_citation"]
        answer_pipeline.system_prompt = settings[f"{prefix}.system_prompt"]
        answer_pipeline.qa_template = settings[f"{prefix}.qa_prompt"]
        answer_pipeline.lang = {"en": "English", "ja": "Japanese"}.get(
            settings["reasoning.lang"], "English"
        )

        pipeline.add_query_context.llm = llm
        pipeline.add_query_context.n_last_interactions = settings[
            f"{prefix}.n_last_interactions"
        ]

        pipeline.trigger_context = settings[f"{prefix}.trigger_context"]
        pipeline.use_rewrite = states.get("app", {}).get("regen", False)
        pipeline.rewrite_pipeline.llm = llm
        pipeline.rewrite_pipeline.lang = {"en": "English", "ja": "Japanese"}.get(
            settings["reasoning.lang"], "English"
        )
        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.llms.manager import llms

        llm = ""
        choices = [("(default)", "")]
        try:
            choices += [(_, _) for _ in llms.options().keys()]
        except Exception as e:
            logger.exception(f"Failed to get LLM options: {e}")

        return {
            "llm": {
                "name": "Language model",
                "value": llm,
                "component": "dropdown",
                "choices": choices,
                "info": (
                    "The language model to use for generating the answer. If None, "
                    "the application default language model will be used."
                ),
            },
            "highlight_citation": {
                "name": "Highlight Citation",
                "value": False,
                "component": "checkbox",
            },
            "system_prompt": {
                "name": "System Prompt",
                "value": "This is a question answering system",
            },
            "qa_prompt": {
                "name": "QA Prompt (contains {context}, {question}, {lang})",
                "value": DEFAULT_QA_TEXT_PROMPT,
            },
            "n_last_interactions": {
                "name": "Number of interactions to include",
                "value": 5,
                "component": "number",
                "info": "The maximum number of chat interactions to include in the LLM",
            },
            "trigger_context": {
                "name": "Maximum message length for context rewriting",
                "value": 150,
                "component": "number",
                "info": (
                    "The maximum length of the message to trigger context addition. "
                    "Exceeding this length, the message will be used as is."
                ),
            },
        }

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "simple",
            "name": "Simple QA",
            "description": "Simple QA pipeline",
        }
