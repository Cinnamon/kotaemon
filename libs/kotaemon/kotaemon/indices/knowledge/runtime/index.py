"""Build an in-memory retrieval runtime without evaluation dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from kotaemon.base import Document
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.indices.knowledge.planning.query_planner import (
    QueryPlanner,
    SourceCatalog,
)
from kotaemon.indices.knowledge.retrieval import KnowledgeService
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.storages import InMemoryDocumentStore, InMemoryVectorStore
from kotaemon.storages.docstores.sqlite_fts import SQLiteFTSDocumentStore


@dataclass
class KnowledgeRuntime:
    """One isolated index, its authorization catalog, and retrieval service."""

    service: KnowledgeService
    docstore: Any
    catalog: SourceCatalog
    documents: tuple[Document, ...]
    vector_store: Any
    embedding: BaseEmbeddings
    policy: RetrievalPolicy
    config: Mapping[str, Any] = field(default_factory=dict)

    def close(self) -> None:
        """Release local stores when the caller finishes with this runtime."""
        close = getattr(self.docstore, "close", None)
        if callable(close):
            close()


def build_knowledge_runtime(
    documents: Sequence[Document],
    *,
    catalog: SourceCatalog,
    embedding: BaseEmbeddings,
    reranker,
    policy: RetrievalPolicy,
    lexical: bool = False,
) -> KnowledgeRuntime:
    """Index documents in memory and expose the shared scoped retrieval service.

    The caller owns source-to-chunk visibility in ``catalog``. Local lexical
    retrieval uses an ephemeral SQLite FTS5 document store; unsupported FTS5
    builds remain usable through the dense route and advertise that limitation.
    """
    if isinstance(documents, (str, bytes)) or not isinstance(documents, Sequence):
        raise TypeError("documents must be a sequence of Document values")
    materialized = tuple(documents)
    if any(not isinstance(document, Document) for document in materialized):
        raise TypeError("documents must contain Document values")
    if catalog is None:
        raise TypeError("catalog must be a SourceCatalog")
    if not isinstance(embedding, BaseEmbeddings):
        raise TypeError("embedding must be a BaseEmbeddings instance")
    if not isinstance(policy, RetrievalPolicy):
        raise TypeError("policy must be a RetrievalPolicy")
    if not isinstance(lexical, bool):
        raise TypeError("lexical must be a bool")

    docstore = SQLiteFTSDocumentStore() if lexical else InMemoryDocumentStore()
    vector_store = InMemoryVectorStore()
    indexer = VectorIndexing(
        vector_store=vector_store,
        doc_store=docstore,
        embedding=embedding,
    )
    if materialized:
        indexer.run(list(materialized))

    retrieval = VectorRetrieval(
        vector_store=indexer.vector_store,
        doc_store=indexer.doc_store,
        embedding=embedding,
        rerankers=[] if reranker is None else [reranker],
        top_k=policy.candidate_k,
        first_round_top_k_mult=1,
        retrieval_mode="hybrid" if lexical else "vector",
    )
    service = KnowledgeService(
        planner=QueryPlanner(),
        catalog=catalog,
        retriever=retrieval,
        docstore=indexer.doc_store,
    )
    config = {
        "retrieval_policy": {
            "enabled": policy.enabled,
            "candidate_k": policy.candidate_k,
            "max_fused_candidates": policy.max_fused_candidates,
            "max_variants": policy.max_variants,
            "dense_weight": policy.dense_weight,
            "lexical_weight": policy.lexical_weight,
            "rrf_k": policy.rrf_k,
        },
        "lexical_requested": lexical,
        "lexical_status": (
            "available"
            if lexical and getattr(indexer.doc_store, "supports_lexical_search", False)
            else "unavailable" if lexical else "not_used"
        ),
    }
    return KnowledgeRuntime(
        service=service,
        docstore=indexer.doc_store,
        catalog=catalog,
        documents=materialized,
        vector_store=indexer.vector_store,
        embedding=embedding,
        policy=policy,
        config=config,
    )
