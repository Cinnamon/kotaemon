import tempfile
from typing import List

from kotaemon.base import BaseComponent, LLMInterface, lazy
from kotaemon.embeddings import LCAzureOpenAIEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.llms import AzureOpenAI
from kotaemon.storages import ChromaVectorStore


class Pipeline(BaseComponent):
    llm: AzureOpenAI = AzureOpenAI.withx(
        azure_endpoint="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )

    retrieving_pipeline: VectorRetrieval = VectorRetrieval.withx(
        vector_store=lazy(ChromaVectorStore).withx(path=str(tempfile.mkdtemp())),
        embedding=LCAzureOpenAIEmbeddings.withx(
            model="text-embedding-ada-002",
            deployment="embedding-deployment",
            azure_endpoint="https://test.openai.azure.com/",
            openai_api_key="some-key",
        ),
    )

    def run(self, text: str) -> LLMInterface:
        matched_texts: List[str] = self.retrieving_pipeline(text)
        return self.llm("\n".join(matched_texts))
