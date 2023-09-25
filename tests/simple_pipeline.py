import tempfile
from typing import List

from theflow import Node

from kotaemon.base import BaseComponent
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.llms.completions.openai import AzureOpenAI
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.vectorstores import ChromaVectorStore


class Pipeline(BaseComponent):
    vectorstore_path: str = str(tempfile.mkdtemp())
    llm: Node[AzureOpenAI] = Node(
        default=AzureOpenAI,
        default_kwargs={
            "openai_api_base": "https://test.openai.azure.com/",
            "openai_api_key": "some-key",
            "openai_api_version": "2023-03-15-preview",
            "deployment_name": "gpt35turbo",
            "temperature": 0,
            "request_timeout": 60,
        },
    )

    @Node.decorate(depends_on=["vectorstore_path"])
    def retrieving_pipeline(self):
        vector_store = ChromaVectorStore(self.vectorstore_path)
        embedding = AzureOpenAIEmbeddings(
            model="text-embedding-ada-002",
            deployment="embedding-deployment",
            openai_api_base="https://test.openai.azure.com/",
            openai_api_key="some-key",
        )

        return RetrieveDocumentFromVectorStorePipeline(
            vector_store=vector_store, embedding=embedding
        )

    def run_raw(self, text: str) -> str:
        matched_texts: List[str] = self.retrieving_pipeline(text)
        return self.llm("\n".join(matched_texts)).text[0]
