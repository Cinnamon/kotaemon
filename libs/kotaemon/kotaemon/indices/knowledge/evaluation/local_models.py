"""Compatibility exports for the public local BGE adapters.

New product and evaluation code should import from :mod:`kotaemon.models`. This
module retains the former evaluation import path and its established ``run``
identity behavior for callers that still use the old reranker directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kotaemon.base import Document
from kotaemon.models import local_bge as _public

EMBEDDING_MODEL_ID = _public.EMBEDDING_MODEL_ID
RERANKER_MODEL_ID = _public.RERANKER_MODEL_ID
LocalModelMetadata = _public.LocalModelMetadata
LocalModelPaths = _public.LocalModelPaths

_WEIGHT_FILES = _public._WEIGHT_FILES
_TOKENIZER_FILES = _public._TOKENIZER_FILES
_WEIGHT_SHARD_RE = _public._WEIGHT_SHARD_RE
_OFFLINE_PROCESS_ERROR = _public._OFFLINE_PROCESS_ERROR
_read_indexed_weight_files = _public._read_indexed_weight_files
_local_weight_files = _public._local_weight_files
_hash_file = _public._hash_file
_validate_and_hash_model_dir = _public._validate_and_hash_model_dir
_require_offline_inference_process = _public._require_offline_inference_process
_flag_embedding_version = _public._flag_embedding_version
_to_python = _public._to_python
_dense_vectors = _public._dense_vectors
_reranker_scores = _public._reranker_scores


def _load_local_flag_backend(
    model_path: Path,
    model_kind: str,
    *,
    device: str,
    query_max_length: int,
    passage_max_length: int,
) -> Any:
    """Retain the loader hook used by evaluation tests and older callers."""
    return _public._load_local_flag_backend(
        model_path,
        model_kind,
        device=device,
        query_max_length=query_max_length,
        passage_max_length=passage_max_length,
    )


class BgeM3Embeddings(_public.BgeM3Embeddings):
    """Compatibility subclass preserving the old module-level loader hook."""

    def _load_model_backend(self, model_path: Path, model_kind: str, **kwargs):
        return _load_local_flag_backend(model_path, model_kind, **kwargs)


class BgeM3Reranking(_public.BgeM3Reranking):
    """Compatibility reranker retaining legacy object identity from ``run``."""

    def _load_model_backend(self, model_path: Path, model_kind: str, **kwargs):
        return _load_local_flag_backend(model_path, model_kind, **kwargs)

    def run(self, documents: list[Document], query: str) -> list[Document]:
        if not documents:
            return []
        scores = self.score_pairs(query, documents)
        ranked = sorted(zip(scores, documents), key=lambda item: item[0], reverse=True)
        return [document for _, document in ranked]


__all__ = [
    "EMBEDDING_MODEL_ID",
    "RERANKER_MODEL_ID",
    "BgeM3Embeddings",
    "BgeM3Reranking",
    "LocalModelMetadata",
    "LocalModelPaths",
]
