import base64
import json
import os
from pathlib import Path
from typing import Optional, Sequence

import requests
import yaml

from kotaemon.base import RetrievedDocument
from kotaemon.indices.rankings import BaseReranking, LLMReranking, LLMTrulensScoring

from ..pipelines import BaseFileIndexRetriever, IndexDocumentPipeline, IndexPipeline


class KnetIndexingPipeline(IndexDocumentPipeline):
    """Knowledge Network specific indexing pipeline"""

    # collection name for external indexing call
    collection_name: str = "default"

    @classmethod
    def get_user_settings(cls):
        return {
            "reader_mode": {
                "name": "Index parser",
                "value": "knowledge_network",
                "choices": [
                    ("Default (KN)", "knowledge_network"),
                ],
                "component": "dropdown",
            },
        }

    def route(self, file_path: Path) -> IndexPipeline:
        """Simply disable the splitter (chunking) for this pipeline"""
        pipeline = super().route(file_path)
        pipeline.splitter = None
        # assign IndexPipeline collection name to parse to loader
        pipeline.collection_name = self.collection_name

        return pipeline


class KnetRetrievalPipeline(BaseFileIndexRetriever):
    DEFAULT_KNET_ENDPOINT: str = "http://127.0.0.1:8081/retrieve"

    collection_name: str = "default"
    rerankers: Sequence[BaseReranking] = [LLMReranking.withx()]

    def encode_image_base64(self, image_path: str | Path) -> bytes | str:
        """Convert image to base64"""
        img_base64 = "data:image/png;base64,{}"
        with open(image_path, "rb") as image_file:
            return img_base64.format(
                base64.b64encode(image_file.read()).decode("utf-8")
            )

    def run(
        self,
        text: str,
        doc_ids: Optional[list[str]] = None,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        """Retrieve document excerpts similar to the text

        Args:
            text: the text to retrieve similar documents
            doc_ids: list of document ids to constraint the retrieval
        """
        print("searching in doc_ids", doc_ids)
        if not doc_ids:
            return []

        docs: list[RetrievedDocument] = []
        params = {
            "query": text,
            "collection": self.collection_name,
            "meta_filters": {"doc_name": doc_ids},
        }
        params["meta_filters"] = json.dumps(params["meta_filters"])
        response = requests.get(self.DEFAULT_KNET_ENDPOINT, params=params)
        metadata_translation = {
            "TABLE": "table",
            "FIGURE": "image",
        }

        if response.status_code == 200:
            # Load YAML content from the response content
            chunks = yaml.safe_load(response.content)
            for chunk in chunks:
                metadata = chunk["node"]["metadata"]
                metadata["type"] = metadata_translation.get(
                    metadata.pop("content_type", ""), ""
                )
                metadata["file_name"] = metadata.pop("company_name", "")

                # load image from returned path
                image_path = metadata.get("image_path", "")
                if image_path and os.path.isfile(image_path):
                    base64_im = self.encode_image_base64(image_path)
                    # explicitly set document type
                    metadata["type"] = "image"
                    metadata["image_origin"] = base64_im

                docs.append(
                    RetrievedDocument(text=chunk["node"]["text"], metadata=metadata)
                )
        else:
            raise IOError(f"{response.status_code}: {response.text}")

        for reranker in self.rerankers:
            docs = reranker(documents=docs, query=text)

        return docs

    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.llms.manager import llms

        try:
            reranking_llm = llms.get_default_name()
            reranking_llm_choices = list(llms.options().keys())
        except Exception:
            reranking_llm = None
            reranking_llm_choices = []

        return {
            "reranking_llm": {
                "name": "LLM for scoring",
                "value": reranking_llm,
                "component": "dropdown",
                "choices": reranking_llm_choices,
                "special_type": "llm",
            },
            "retrieval_mode": {
                "name": "Retrieval mode",
                "value": "hybrid",
                "choices": ["vector", "text", "hybrid"],
                "component": "dropdown",
            },
        }

    @classmethod
    def get_pipeline(cls, user_settings, index_settings, selected):
        """Get retriever objects associated with the index

        Args:
            settings: the settings of the app
            kwargs: other arguments
        """
        from ktem.llms.manager import llms

        retriever = cls(
            rerankers=[LLMTrulensScoring()],
        )

        # hacky way to input doc_ids to retriever.run() call (through theflow)
        kwargs = {".doc_ids": selected}
        retriever.set_run(kwargs, temp=False)

        for reranker in retriever.rerankers:
            if isinstance(reranker, LLMReranking):
                reranker.llm = llms.get(
                    user_settings["reranking_llm"], llms.get_default()
                )

        return retriever
