"""Pure weighted reciprocal-rank fusion for bounded recall batches."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from collections.abc import Sequence
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from .contracts import RecallBatch, RetrievalPolicy

if TYPE_CHECKING:
    from kotaemon.base import RetrievedDocument


def _normalized_route(query: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", query).casefold().split())


def _document_id(document: RetrievedDocument) -> str:
    doc_id = document.doc_id
    return str(doc_id) if doc_id is not None else ""


def fuse_batches(
    batches: Sequence[RecallBatch], policy: RetrievalPolicy
) -> list[RetrievedDocument]:
    """Fuse route rankings without allowing extra variants to inflate a branch.

    A scheduled route is identified by its branch and normalized query. Its
    configured branch weight is divided across all unique scheduled routes,
    including routes that did not return candidates.
    """
    routes: list[RecallBatch] = []
    seen_routes: set[tuple[str, str]] = set()
    for batch in batches:
        route_key = (batch.branch, _normalized_route(batch.query))
        if route_key in seen_routes:
            continue
        seen_routes.add(route_key)
        routes.append(batch)

    route_counts = defaultdict(int)
    for batch in routes:
        route_counts[batch.branch] += 1

    contributions: dict[str, dict[str, Any]] = {}
    weights = {"dense": policy.dense_weight, "lexical": policy.lexical_weight}
    for route_order, batch in enumerate(routes):
        if batch.status != "available":
            continue

        unique_documents: list[RetrievedDocument] = []
        seen_ids: set[str] = set()
        for document in batch.documents:
            doc_id = _document_id(document)
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            unique_documents.append(document)
            if len(unique_documents) >= policy.candidate_k:
                break

        route_weight = weights[batch.branch] / route_counts[batch.branch]
        for rank, document in enumerate(unique_documents, start=1):
            doc_id = _document_id(document)
            entry = contributions.get(doc_id)
            if entry is None:
                entry = {
                    "document": deepcopy(document),
                    "fusion_score": 0.0,
                    "first_route": route_order,
                    "raw_scores": [],
                    "route_ranks": [],
                }
                contributions[doc_id] = entry

            entry["fusion_score"] += route_weight / (policy.rrf_k + rank)
            entry["raw_scores"].append(
                {
                    "branch": batch.branch,
                    "query_index": batch.query_index,
                    "score": deepcopy(document.score),
                }
            )
            entry["route_ranks"].append(
                {
                    "branch": batch.branch,
                    "query_index": batch.query_index,
                    "rank": rank,
                }
            )

    ranked_entries = sorted(
        contributions.items(),
        key=lambda item: (
            -item[1]["fusion_score"],
            item[1]["first_route"],
            item[0],
        ),
    )

    fused: list[RetrievedDocument] = []
    for _doc_id, entry in ranked_entries[: policy.max_fused_candidates]:
        document = entry["document"]
        metadata = deepcopy(document.retrieval_metadata or {})
        metadata["fusion_score"] = entry["fusion_score"]
        metadata["raw_scores"] = entry["raw_scores"]
        metadata["route_ranks"] = entry["route_ranks"]
        document.retrieval_metadata = metadata
        fused.append(document)
    return fused
