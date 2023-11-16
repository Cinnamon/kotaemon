import os
from pathlib import Path
from typing import List, Sequence

from theflow import Node
from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.base.schema import Document, RetrievedDocument
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.llms import PromptTemplate
from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.agents import BaseAgent
from kotaemon.pipelines.citation import CitationPipeline
from kotaemon.pipelines.reranking import BaseRerankingPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.pipelines.tools import ComponentTool
from kotaemon.storages import (
    BaseDocumentStore,
    BaseVectorStore,
    InMemoryDocumentStore,
    InMemoryVectorStore,
)

from .utils import file_names_to_collection_name


class QuestionAnsweringPipeline(BaseComponent):
    """
    Question Answering pipeline ultilizing a child Retrieving pipeline
    """

    storage_path: Path = Path("./storage")
    retrieval_top_k: int = 3
    file_name_list: List[str]
    """List of filename, incombination with storage_path to
    create persistent path of vectorstore"""
    qa_prompt_template: PromptTemplate = PromptTemplate(
        'Answer the following question: "{question}". '
        "The context is: \n{context}\nAnswer: "
    )

    llm: AzureChatOpenAI = AzureChatOpenAI.withx(
        azure_endpoint="https://bleh-dummy.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_api_version="2023-07-01-preview",
        deployment_name="dummy-q2-16k",
        temperature=0,
        request_timeout=60,
    )

    vector_store: _[BaseVectorStore] = _(InMemoryVectorStore)
    doc_store: _[BaseDocumentStore] = _(InMemoryDocumentStore)
    rerankers: Sequence[BaseRerankingPipeline] = []

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        azure_endpoint="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    @Node.auto(
        depends_on=[
            "vector_store",
            "doc_store",
            "embedding",
            "file_name_list",
            "retrieval_top_k",
        ]
    )
    def retrieving_pipeline(self) -> RetrieveDocumentFromVectorStorePipeline:
        retrieving_pipeline = RetrieveDocumentFromVectorStorePipeline(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            top_k=self.retrieval_top_k,
            rerankers=self.rerankers,
        )
        # load persistent from selected path
        collection_name = file_names_to_collection_name(self.file_name_list)
        retrieving_pipeline.load(self.storage_path / collection_name)
        return retrieving_pipeline

    def _format_doc_text(self, text: str) -> str:
        return text.replace("\n", " ")

    def _format_retrieved_context(self, documents: List[RetrievedDocument]) -> str:
        matched_texts: List[str] = [
            self._format_doc_text(doc.text) for doc in documents
        ]
        return "\n\n".join(matched_texts)

    def run(self, question: str, use_citation: bool = False) -> Document:
        # retrieve relevant documents as context
        documents = self.retrieving_pipeline(question, top_k=int(self.retrieval_top_k))
        context = self._format_retrieved_context(documents)
        self.log_progress(".context", context=context)

        # generate the answer
        prompt = self.qa_prompt_template.populate(
            context=context,
            question=question,
        )
        self.log_progress(".prompt", prompt=prompt)
        answer_text = self.llm(prompt).text
        if use_citation:
            # run citation pipeline
            citation_pipeline = CitationPipeline(llm=self.llm)
            citation = citation_pipeline(context=context, question=question)
        else:
            citation = None

        answer = Document(text=answer_text, metadata={"citation": citation})
        return answer


class AgentQAPipeline(QuestionAnsweringPipeline):
    """
    QA pipeline ultilizing a child Retrieving pipeline and a Agent pipeline
    """

    agent: BaseAgent

    def add_search_tool(self):
        search_tool = ComponentTool(
            name="search_doc",
            description=(
                "A vector store that searches for similar and "
                "related content "
                f"in a document: {' '.join(self.file_name_list)}. "
                "The result is a huge chunk of text related "
                "to your search but can also "
                "contain irrelevant info."
            ),
            postprocessor=self._format_retrieved_context,
            component=self.retrieving_pipeline,
        )
        if search_tool not in self.agent.plugins:
            self.agent.plugins.append(search_tool)

    def run(self, question: str, use_citation: bool = False) -> Document:
        answer = self.agent(question, use_citation=use_citation)
        return answer
