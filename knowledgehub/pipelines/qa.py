import os
from pathlib import Path
from typing import List

from theflow import Node
from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.base.schema import RetrievedDocument
from kotaemon.docstores import InMemoryDocumentStore
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.llms import PromptTemplate
from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.pipelines.agents import BaseAgent
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.pipelines.tools import ComponentTool
from kotaemon.vectorstores import InMemoryVectorStore

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
    prompt_template: PromptTemplate = PromptTemplate(
        'Answer the following question: "{question}". '
        "The context is: \n{context}\nAnswer: "
    )

    llm: AzureChatOpenAI = AzureChatOpenAI.withx(
        openai_api_base="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2-gpt35",
        temperature=0,
        request_timeout=60,
    )

    vector_store: _[InMemoryVectorStore] = _(InMemoryVectorStore)
    doc_store: _[InMemoryDocumentStore] = _(InMemoryDocumentStore)

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        openai_api_base="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    @Node.default()
    def retrieving_pipeline(self) -> RetrieveDocumentFromVectorStorePipeline:
        retrieving_pipeline = RetrieveDocumentFromVectorStorePipeline(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
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

    def run(self, question: str) -> str:
        # retrieve relevant documents as context
        documents = self.retrieving_pipeline(question, top_k=int(self.retrieval_top_k))
        context = self._format_retrieved_context(documents)
        self.log_progress(".context", context=context)

        # generate the answer
        prompt = self.prompt_template.populate(
            context=context,
            question=question,
        )
        self.log_progress(".prompt", prompt=prompt)
        answer = self.llm(prompt).text
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

    def run(self, question: str) -> str:
        answer = self.agent(question).output
        return answer
