import pytest

from kotaemon.contribs.promptui.config import export_pipeline_to_config
from kotaemon.contribs.promptui.ui import build_from_dict


@pytest.fixture()
def simple_pipeline_cls(tmp_path):
    """Create a pipeline class that can be used"""
    from typing import List

    from theflow import Node

    from kotaemon.base import BaseComponent
    from kotaemon.embeddings import AzureOpenAIEmbeddings
    from kotaemon.llms.completions.openai import AzureOpenAI
    from kotaemon.pipelines.retrieving import (
        RetrieveDocumentFromVectorStorePipeline,
    )
    from kotaemon.vectorstores import ChromaVectorStore

    class Pipeline(BaseComponent):
        vectorstore_path: str = str(tmp_path)
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

    return Pipeline


Pipeline = simple_pipeline_cls


class TestPromptConfig:
    def test_export_prompt_config(self, simple_pipeline_cls):
        """Test if the prompt config is exported correctly"""
        pipeline = simple_pipeline_cls()
        config_dict = export_pipeline_to_config(pipeline)
        config = list(config_dict.values())[0]

        assert "inputs" in config, "inputs should be in config"
        assert "text" in config["inputs"], "inputs should have config"

        assert "params" in config, "params should be in config"
        assert "vectorstore_path" in config["params"]
        assert "llm.deployment_name" in config["params"]
        assert "llm.openai_api_base" in config["params"]
        assert "llm.openai_api_key" in config["params"]
        assert "llm.openai_api_version" in config["params"]
        assert "llm.request_timeout" in config["params"]
        assert "llm.temperature" in config["params"]


class TestPromptUI:
    def test_uigeneration(self, simple_pipeline_cls):
        """Test if the gradio UI is exposed without any problem"""
        pipeline = simple_pipeline_cls()
        config = export_pipeline_to_config(pipeline)

        build_from_dict(config)
