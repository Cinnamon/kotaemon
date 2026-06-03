from __future__ import annotations

from typing import Literal, TypedDict
from typing_extensions import NotRequired

from ktem.embeddings.manager import embedding_models_manager
from ktem.collections.file.types import IndexSettings

from kotaemon.indices.indexing import BaseIndexing
from kotaemon.indices.indexing.impl.rag import (
    IndexDocumentPipeline as _IndexDocumentPipeline,
)

ReaderMode = Literal[
    "default",
    "adobe",
    "azure-di",
    "docling",
    "paddle-struct",
    "paddle-vl",
]


class IndexingUserSettings(TypedDict):
    """User-facing settings consumed by
    :meth:`IndexDocumentPipeline.get_pipeline`.

    All keys are optional; defaults are applied inside ``get_pipeline``
    when a key is absent.
    """

    reader_mode: NotRequired[ReaderMode]
    quick_index_mode: NotRequired[bool]


class IndexDocumentPipeline(_IndexDocumentPipeline):
    """RAG indexing pipeline wired to ktem managers.

    Extends the kotaemon core with ktem-specific factory and settings.
    """

    @classmethod
    def get_user_settings(cls) -> IndexingUserSettings:
        return {
            "reader_mode": {
                "name": "File loader",
                "value": "default",
                "choices": [
                    ("Default (open-source)", "default"),
                    ("Adobe API (figure+table extraction)", "adobe"),
                    (
                        "Azure AI Document Intelligence"
                        " (figure+table extraction)",
                        "azure-di",
                    ),
                    ("Docling (figure+table extraction)", "docling"),
                    (
                        "PaddleOCR PPStructureV3 (table+figure extraction)",
                        "paddle-struct",
                    ),
                    ("PaddleOCR-VL (VLM document parsing)", "paddle-vl"),
                ],
                "component": "dropdown",
            },
        }

    @classmethod
    def get_pipeline(
        cls,
        user_settings: IndexingUserSettings,
        index_settings: IndexSettings,
    ) -> BaseIndexing:
        use_quick_index_mode = user_settings.get(
            "quick_index_mode", False
        )
        print("use_quick_index_mode", use_quick_index_mode)
        return cls(
            embedding=embedding_models_manager[
                index_settings.get(
                    "embedding",
                    embedding_models_manager.get_default_name(),
                )
            ],
            run_embedding_in_thread=use_quick_index_mode,
            reader_mode=user_settings.get("reader_mode", "default"),
        )
