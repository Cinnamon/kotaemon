import asyncio
import logging
import warnings
from collections import defaultdict
from functools import partial
from typing import Iterator, Optional

import tiktoken
from ktem.components import embeddings, get_docstore, get_vectorstore, llms
from ktem.db.models import Index, SourceTargetRelation, engine
from kotaemon.base import (
    BaseComponent,
    Document,
    HumanMessage,
    Node,
    RetrievedDocument,
    SystemMessage,
)
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.qa.citation import CitationPipeline
from kotaemon.indices.rankings import BaseReranking, CohereReranking, LLMReranking
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.llms import ChatLLM, PromptTemplate
from llama_index.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.vector_stores.types import VectorStoreQueryMode
from sqlmodel import Session, select
from theflow.settings import settings

logger = logging.getLogger(__name__)


class DocumentRetrievalPipeline(BaseComponent):
    """Retrieve relevant document

    Args:
        vector_retrieval: the retrieval pipeline that return the relevant documents
            given a text query
        reranker: the reranking pipeline that re-rank and filter the retrieved
            documents
        get_extra_table: if True, for each retrieved document, the pipeline will look
            for surrounding tables (e.g. within the page)
    """

    vector_retrieval: VectorRetrieval = VectorRetrieval.withx(
        doc_store=get_docstore(),
        vector_store=get_vectorstore(),
        embedding=embeddings.get_default(),
    )
    reranker: BaseReranking = CohereReranking.withx(
        cohere_api_key=getattr(settings, "COHERE_API_KEY", "")
    ) >> LLMReranking.withx(llm=llms.get_lowest_cost())
    get_extra_table: bool = False

    def run(
        self,
        text: str,
        top_k: int = 5,
        mmr: bool = False,
        doc_ids: Optional[list[str]] = None,
    ) -> list[RetrievedDocument]:
        """Retrieve document excerpts similar to the text

        Args:
            text: the text to retrieve similar documents
            top_k: number of documents to retrieve
            mmr: whether to use mmr to re-rank the documents
            doc_ids: list of document ids to constraint the retrieval
        """
        kwargs = {}
        if doc_ids:
            with Session(engine) as session:
                stmt = select(Index).where(
                    Index.relation_type == SourceTargetRelation.VECTOR,
                    Index.source_id.in_(doc_ids),  # type: ignore
                )
                results = session.exec(stmt)
                vs_ids = [r.target_id for r in results.all()]

            kwargs["filters"] = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="doc_id",
                        value=vs_id,
                        operator=FilterOperator.EQ,
                    )
                    for vs_id in vs_ids
                ],
                condition=FilterCondition.OR,
            )

        if mmr:
            # TODO: double check that llama-index MMR works correctly
            kwargs["mode"] = VectorStoreQueryMode.MMR
            kwargs["mmr_threshold"] = 0.5

        # rerank
        docs = self.vector_retrieval(text=text, top_k=top_k, **kwargs)
        if self.get_from_path("reranker"):
            docs = self.reranker(docs, query=text)

        if not self.get_extra_table:
            return docs

        # retrieve extra nodes relate to table
        table_pages = defaultdict(list)
        retrieved_id = set([doc.doc_id for doc in docs])
        for doc in docs:
            if "page_label" not in doc.metadata:
                continue
            if "file_name" not in doc.metadata:
                warnings.warn(
                    "file_name not in metadata while page_label is in metadata: "
                    f"{doc.metadata}"
                )
            table_pages[doc.metadata["file_name"]].append(doc.metadata["page_label"])

        queries = [
            {"$and": [{"file_name": {"$eq": fn}}, {"page_label": {"$in": pls}}]}
            for fn, pls in table_pages.items()
        ]
        if queries:
            extra_docs = self.vector_retrieval(
                text="",
                top_k=50,
                where={"$or": queries},
            )
            for doc in extra_docs:
                if doc.doc_id not in retrieved_id:
                    docs.append(doc)

        return docs


class PrepareEvidencePipeline(BaseComponent):
    """Prepare the evidence text from the list of retrieved documents

    This step usually happens after `DocumentRetrievalPipeline`.

    Args:
        trim_func: a callback function or a BaseComponent, that splits a large
            chunk of text into smaller ones. The first one will be retained.
    """

    trim_func: TokenSplitter = TokenSplitter.withx(
        chunk_size=7600,
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
        evidence_mode = 0

        for _id, retrieved_item in enumerate(docs):
            retrieved_content = ""
            page = retrieved_item.metadata.get("page_label", None)
            source = filename = retrieved_item.metadata.get("file_name", "-")
            if page:
                source += f" (Page {page})"
            if retrieved_item.metadata.get("type", "") == "table":
                evidence_mode = 1  # table
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
                evidence_mode = 2  # chatbot
                retrieved_content = retrieved_item.metadata["window"]
                evidence += (
                    f"<br><b>Chatbot scenario from {filename} (Row {page})</b>\n"
                    + retrieved_content
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

        # trim context by trim_len
        print("len (original)", len(evidence))
        if evidence:
            texts = self.trim_func([Document(text=evidence)])
            evidence = texts[0].text
            print("len (trimmed)", len(evidence))

        print(f"PrepareEvidence with input {input}\nOutput: {evidence}\n")

        return Document(content=(evidence_mode, evidence))


DEFAULT_QA_TEXT_PROMPT = (
    "Use the following pieces of context to answer the question at the end. "
    "If you don't know the answer, just say that you don't know, don't try to "
    "make up an answer. Keep the answer as concise as possible. Give answer in "
    "{lang}. {system}\n\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)

DEFAULT_QA_TABLE_PROMPT = (
    "List all rows (row number) from the table context that related to the question, "
    "then provide detail answer with clear explanation and citations. "
    "If you don't know the answer, just say that you don't know, "
    "don't try to make up an answer. Give answer in {lang}. {system}\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Helpful Answer:"
)

DEFAULT_QA_CHATBOT_PROMPT = (
    "Pick the most suitable chatbot scenarios to answer the question at the end, "
    "output the provided answer text. If you don't know the answer, "
    "just say that you don't know. Keep the answer as concise as possible. "
    "Give answer in {lang}. {system}\n\n"
    "Context:\n"
    "{context}\n"
    "Question: {question}\n"
    "Answer:"
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

    llm: ChatLLM = Node(default_callback=lambda _: llms.get_highest_accuracy())
    citation_pipeline: CitationPipeline = Node(
        default_callback=lambda _: CitationPipeline(llm=llms.get_lowest_cost())
    )

    qa_template: str = DEFAULT_QA_TEXT_PROMPT
    qa_table_template: str = DEFAULT_QA_TABLE_PROMPT
    qa_chatbot_template: str = DEFAULT_QA_CHATBOT_PROMPT

    system_prompt: str = ""
    lang: str = "English"  # support English and Japanese

    async def run(  # type: ignore
        self, question: str, evidence: str, evidence_mode: int = 0
    ) -> Document | Iterator[Document]:
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
        if evidence_mode == 0:
            prompt_template = PromptTemplate(self.qa_template)
        elif evidence_mode == 1:
            prompt_template = PromptTemplate(self.qa_table_template)
        else:
            prompt_template = PromptTemplate(self.qa_chatbot_template)

        prompt = prompt_template.populate(
            context=evidence,
            question=question,
            lang=self.lang,
            system=self.system_prompt,
        )

        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content=prompt),
        ]
        output = ""
        for text in self.llm(messages):
            output += text.text
            self.report_output({"output": text.text})
            await asyncio.sleep(0)

        citation = self.citation_pipeline(context=evidence, question=question)
        answer = Document(text=output, metadata={"citation": citation})

        return answer


class FullQAPipeline(BaseComponent):
    """Question answering pipeline. Handle from question to answer"""

    class Config:
        allow_extra = True
        params_publish = True

    retrieval_pipeline: DocumentRetrievalPipeline = DocumentRetrievalPipeline.withx()
    evidence_pipeline: PrepareEvidencePipeline = PrepareEvidencePipeline.withx()
    answering_pipeline: AnswerWithContextPipeline = AnswerWithContextPipeline.withx()

    async def run(self, question: str, **kwargs) -> Document:  # type: ignore
        docs = self.retrieval_pipeline(text=question)
        evidence_mode, evidence = self.evidence_pipeline(docs).content
        answer = await self.answering_pipeline(
            question=question, evidence=evidence, evidence_mode=evidence_mode
        )

        # prepare citation
        from collections import defaultdict

        spans = defaultdict(list)
        for fact_with_evidence in answer.metadata["citation"].answer:
            for quote in fact_with_evidence.substring_quote:
                for doc in docs:
                    start_idx = doc.text.find(quote)
                    if start_idx >= 0:
                        spans[doc.doc_id].append(
                            {
                                "start": start_idx,
                                "end": start_idx + len(quote),
                            }
                        )
                        break

        id2docs = {doc.doc_id: doc for doc in docs}
        for id, ss in spans.items():
            if not ss:
                continue
            ss = sorted(ss, key=lambda x: x["start"])
            text = id2docs[id].text[: ss[0]["start"]]
            for idx, span in enumerate(ss):
                text += (
                    "<mark>" + id2docs[id].text[span["start"] : span["end"]] + "</mark>"
                )
                if idx < len(ss) - 1:
                    text += id2docs[id].text[span["end"] : ss[idx + 1]["start"]]
            text += id2docs[id].text[ss[-1]["end"] :]
            self.report_output(
                {
                    "evidence": (
                        "<details>"
                        f"<summary>{id2docs[id].metadata['file_name']}</summary>"
                        f"{text}"
                        "</details><br>"
                    )
                }
            )

        self.report_output(None)
        return answer

    @classmethod
    def get_pipeline(cls, settings, **kwargs):
        """Get the reasoning pipeline

        Need a base pipeline implementation. Currently the drawback is that we want to
        treat the retrievers as tools. Hence, the reasoning pipelie should just take
        the already initiated tools (retrievers), and do not need to set such logic
        here.
        """
        pipeline = FullQAPipeline(get_extra_table=settings["index.prioritize_table"])
        if not settings["index.use_reranking"]:
            pipeline.retrieval_pipeline.reranker = None  # type: ignore

        pipeline.answering_pipeline.llm = llms.get_highest_accuracy()
        kwargs = {
            ".retrieval_pipeline.top_k": int(settings["index.num_retrieval"]),
            ".retrieval_pipeline.mmr": settings["index.mmr"],
            ".retrieval_pipeline.doc_ids": kwargs.get("files", None),
        }
        pipeline.set_run(kwargs, temp=True)

        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.components import llms

        try:
            citation_llm = llms.get_lowest_cost_name()
            citation_llm_choices = list(llms.options().keys())
            main_llm = llms.get_highest_accuracy_name()
            main_llm_choices = list(llms.options().keys())
        except Exception as e:
            logger.error(e)
            citation_llm = None
            citation_llm_choices = []
            main_llm = None
            main_llm_choices = []

        return {
            "highlight_citation": {
                "name": "Highlight Citation",
                "value": True,
                "component": "checkbox",
            },
            "system_prompt": {
                "name": "System Prompt",
                "value": "This is a question answering system",
            },
            "citation_llm": {
                "name": "LLM for citation",
                "value": citation_llm,
                "component": "dropdown",
                "choices": citation_llm_choices,
            },
            "main_llm": {
                "name": "LLM for main generation",
                "value": main_llm,
                "component": "dropdown",
                "choices": main_llm_choices,
            },
        }
