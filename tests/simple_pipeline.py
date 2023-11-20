import tempfile
from typing import List

from theflow.utils.modules import ObjectInitDeclaration as _

from kotaemon.base import BaseComponent
from kotaemon.embeddings import AzureOpenAIEmbeddings
from kotaemon.llms.completions.openai import AzureOpenAI
from kotaemon.pipelines.retrieving import RetrieveDocumentFromVectorStorePipeline
from kotaemon.storages import ChromaVectorStore


class Pipeline(BaseComponent):
    llm: AzureOpenAI = AzureOpenAI.withx(
        openai_api_base="https://test.openai.azure.com/",
        openai_api_key="some-key",
        openai_api_version="2023-03-15-preview",
        deployment_name="gpt35turbo",
        temperature=0,
        request_timeout=60,
    )

    retrieving_pipeline: RetrieveDocumentFromVectorStorePipeline = (
        RetrieveDocumentFromVectorStorePipeline.withx(
            vector_store=_(ChromaVectorStore).withx(path=str(tempfile.mkdtemp())),
            embedding=AzureOpenAIEmbeddings.withx(
                model="text-embedding-ada-002",
                deployment="embedding-deployment",
                openai_api_base="https://test.openai.azure.com/",
                openai_api_key="some-key",
            ),
        )
    )

    def run_raw(self, text: str) -> str:
        matched_texts: List[str] = self.retrieving_pipeline(text)
        return self.llm("\n".join(matched_texts)).text

    def run(self):
        ...
