import os
from typing import List

from theflow import Param
from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.llms.completions.openai import AzureOpenAI
from kotaemon.pipelines.indexing import IndexVectorStoreFromDocumentPipeline
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.storages import ChromaVectorStore, InMemoryDocumentStore


class QuestionAnsweringPipeline(BaseComponent):
    retrieval_top_k: int = 1

    llm: AzureOpenAI = AzureOpenAI.withx(
        openai_api_base="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2-gpt35",
        temperature=0,
        request_timeout=60,
    )

    retrieving_pipeline: RetrieveDocumentFromVectorStorePipeline = (
        RetrieveDocumentFromVectorStorePipeline.withx(
            vector_store=_(ChromaVectorStore).withx(path="./tmp"),
            embedding=AzureOpenAIEmbeddings.withx(
                model="text-embedding-ada-002",
                deployment="dummy-q2-text-embedding",
                openai_api_base="https://bleh-dummy-2.openai.azure.com/",
                openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            ),
        )
    )

    def run_raw(self, text: str) -> str:
        # reload the document store, in case it has been updated
        doc_store = InMemoryDocumentStore()
        doc_store.load("docstore.json")
        self.retrieving_pipeline.doc_store = doc_store

        # retrieve relevant documents as context
        matched_texts: List[str] = [
            _.text
            for _ in self.retrieving_pipeline(text, top_k=int(self.retrieval_top_k))
        ]
        context = "\n".join(matched_texts)

        # generate the answer
        prompt = f'Answer the following question: "{text}". The context is: \n{context}'
        self.log_progress(".prompt", prompt=prompt)

        return self.llm(prompt).text


class IndexingPipeline(IndexVectorStoreFromDocumentPipeline):
    # Expose variables for users to switch in prompt ui
    embedding_model: str = "text-embedding-ada-002"
    vector_store: _[ChromaVectorStore] = _(ChromaVectorStore).withx(path="./tmp")

    @Param.auto()
    def doc_store(self) -> InMemoryDocumentStore:
        doc_store = InMemoryDocumentStore()
        if os.path.isfile("docstore.json"):
            doc_store.load("docstore.json")
        return doc_store

    embedding: AzureOpenAIEmbeddings = AzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        openai_api_base="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
    )

    def run_raw(self, text: str) -> int:  # type: ignore
        """Normally, this indexing pipeline returns nothing. For demonstration,
        we want it to return something, so let's return the number of documents
        in the vector store
        """
        super().run_raw(text)

        if self.doc_store is not None:
            # persist to local anytime an indexing is created
            # this can be bypassed when we have a FileDocumentStore
            self.doc_store.save("docstore.json")

        return self.vector_store._collection.count()
