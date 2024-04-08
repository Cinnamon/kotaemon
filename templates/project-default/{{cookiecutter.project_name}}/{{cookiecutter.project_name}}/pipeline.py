import os
from typing import List

from kotaemon.base import BaseComponent, Document, LLMInterface, Node, Param, lazy
from kotaemon.contribs.promptui.logs import ResultLog
from kotaemon.embeddings import LCAzureOpenAIEmbeddings
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.llms import LCAzureChatOpenAI
from kotaemon.storages import ChromaVectorStore, SimpleFileDocumentStore


class QAResultLog(ResultLog):
    @staticmethod
    def _get_prompt(obj):
        return obj["prompt"]


class QuestionAnsweringPipeline(BaseComponent):

    _promptui_resultlog = QAResultLog
    _promptui_outputs: list = [
        {
            "step": ".prompt",
            "getter": "_get_prompt",
            "component": "text",
            "params": {"label": "Constructed prompt to LLM"},
        },
        {
            "step": ".",
            "getter": "_get_output",
            "component": "text",
            "params": {"label": "Answer"},
        },
    ]

    retrieval_top_k: int = 1
    llm: LCAzureChatOpenAI = LCAzureChatOpenAI.withx(
        azure_endpoint="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", "default-key"),
        openai_api_version="2023-03-15-preview",
        deployment_name="dummy-q2-gpt35",
        temperature=0,
        request_timeout=60,
    )

    retrieving_pipeline: VectorRetrieval = Node(
        VectorRetrieval.withx(
            vector_store=lazy(ChromaVectorStore).withx(path="./tmp"),
            doc_store=lazy(SimpleFileDocumentStore).withx(path="docstore.json"),
            embedding=LCAzureOpenAIEmbeddings.withx(
                model="text-embedding-ada-002",
                deployment="dummy-q2-text-embedding",
                azure_endpoint="https://bleh-dummy-2.openai.azure.com/",
                openai_api_key=os.environ.get("OPENAI_API_KEY", "default-key"),
            ),
        ),
        ignore_ui=True,
    )

    def run(self, text: str) -> LLMInterface:
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


class IndexingPipeline(VectorIndexing):

    vector_store: ChromaVectorStore = Param(
        lazy(ChromaVectorStore).withx(path="./tmp"),
        ignore_ui=True,
    )
    doc_store: SimpleFileDocumentStore = Param(
        lazy(SimpleFileDocumentStore).withx(path="docstore.json"),
        ignore_ui=True,
    )
    embedding: LCAzureOpenAIEmbeddings = LCAzureOpenAIEmbeddings.withx(
        model="text-embedding-ada-002",
        deployment="dummy-q2-text-embedding",
        azure_endpoint="https://bleh-dummy-2.openai.azure.com/",
        openai_api_key=os.environ.get("OPENAI_API_KEY", "default-key"),
    )

    def run(self, text: str) -> Document:
        """Normally, this indexing pipeline returns nothing. For demonstration,
        we want it to return something, so let's return the number of documents
        in the vector store
        """
        super().run(text)

        if self.doc_store is not None:
            # persist to local anytime an indexing is created
            # this can be bypassed when we have a FileDocumentStore
            self.doc_store.save("docstore.json")

        return Document(self.vector_store._collection.count())
