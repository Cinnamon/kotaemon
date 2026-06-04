from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional, TypedDict

from decouple import config
from fastapi import Path
from ktem.collections.file.types import IndexSettings
from ktem.embeddings.manager import embedding_models_manager
from ktem.llms.manager import llms
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

from kotaemon.indices.rankings import LLMReranking, LLMTrulensScoring
from kotaemon.indices.retriever.impl.rag import (
    DocumentRetrievalPipeline as _DocumentRetrievalPipeline,
)
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

logger = logging.getLogger(__name__)

RetrievalMode = Literal["vector", "text", "hybrid"]


class RetrievalUserSettings(TypedDict):
    """User-facing settings consumed by
    :meth:`DocumentRetrievalPipeline.get_pipeline`.

    All keys must be present; ``get_user_settings`` provides the
    defaults that are persisted before ``get_pipeline`` is called.
    """

    reranking_llm: Optional[str]
    num_retrieval: int
    retrieval_mode: RetrievalMode
    prioritize_table: bool
    mmr: bool
    use_reranking: bool
    use_llm_reranking: bool


@dataclass(kw_only=True)
class DocumentRetrievalPipeline(_DocumentRetrievalPipeline):
    """RAG retrieval pipeline wired to ktem managers.

    Extends the kotaemon core with ktem-specific factory and settings.
    """

    @classmethod
    def get_user_settings(cls) -> dict:
        try:
            reranking_llm = llms.get_default_name()
            reranking_llm_choices = list(llms.options().keys())
        except Exception as e:
            logger.error(e)
            reranking_llm = None
            reranking_llm_choices = []

        return {
            "reranking_llm": {
                "name": "LLM for relevant scoring",
                "value": reranking_llm,
                "component": "dropdown",
                "choices": reranking_llm_choices,
                "special_type": "llm",
            },
            "num_retrieval": {
                "name": "Number of document chunks to retrieve",
                "value": 10,
                "component": "number",
            },
            "retrieval_mode": {
                "name": "Retrieval mode",
                "value": "hybrid",
                "choices": ["vector", "text", "hybrid"],
                "component": "dropdown",
            },
            "prioritize_table": {
                "name": "Prioritize table",
                "value": False,
                "choices": [True, False],
                "component": "checkbox",
            },
            "mmr": {
                "name": "Use MMR",
                "value": False,
                "choices": [True, False],
                "component": "checkbox",
            },
            "use_reranking": {
                "name": "Use reranking",
                "value": True,
                "choices": [True, False],
                "component": "checkbox",
            },
            "use_llm_reranking": {
                "name": "Use LLM relevant scoring",
                "value": not config("USE_LOW_LLM_REQUESTS", default=False, cast=bool),
                "choices": [True, False],
                "component": "checkbox",
            },
        }

    @classmethod
    def get_pipeline(
        cls,
        user_settings: RetrievalUserSettings,
        index_settings: IndexSettings,
        Source: type[DeclarativeBase],
        Index: type[DeclarativeBase],
        VS: BaseVectorStore,
        DS: BaseDocumentStore,
        FSPath: Path,
        user_id: int,
        engine: Engine,
        selected: Optional[list] = None,
    ) -> "DocumentRetrievalPipeline":
        use_llm_reranking = user_settings.get("use_llm_reranking", False)
        retriever = cls(
            Source=Source,
            Index=Index,
            VS=VS,
            DS=DS,
            FSPath=FSPath,
            user_id=user_id,
            engine=engine,
            get_extra_table=user_settings["prioritize_table"],
            top_k=user_settings["num_retrieval"],
            mmr=user_settings["mmr"],
            embedding=embedding_models_manager[
                index_settings.get(
                    "embedding", embedding_models_manager.get_default_name()
                )
            ],
            retrieval_mode=user_settings["retrieval_mode"],
            llm_scorer=(LLMTrulensScoring() if use_llm_reranking else None),
            rerankers=[
                # reranking_models_manager[
                #     index_settings.get(
                #         "reranking",
                #         reranking_models_manager.get_default_name(),
                #     )
                # ]
            ],
            doc_ids=selected,
        )
        if not user_settings["use_reranking"]:
            retriever.rerankers = []  # type: ignore

        reranking_llm_name: str = (
            user_settings.get("reranking_llm") or llms.get_default_name()
        )
        for reranker in retriever.rerankers:
            if isinstance(reranker, LLMReranking):
                reranker.llm = llms.get(reranking_llm_name, llms.get_default())

        if retriever.llm_scorer:
            retriever.llm_scorer.llm = llms.get(reranking_llm_name, llms.get_default())

        # retriever.set_run({".doc_ids": selected}, temp=False)
        return retriever
