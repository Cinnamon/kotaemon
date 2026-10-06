from __future__ import annotations

import logging
import math
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any, Optional, Sequence, cast

from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from theflow.settings import settings as flowsettings

from kotaemon.base import BaseComponent, Document, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

from .base import BaseIndexing, BaseRetrieval
from .knowledge.retrieval.diversity import select_diverse_documents
from .knowledge.retrieval.contracts import EnrichedQuery, RecallBatch, RetrievalPolicy
from .knowledge.retrieval.fusion import fuse_batches
from .knowledge.retrieval.trace import trace_event, trace_update
from .rankings import BaseReranking, LLMReranking

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"
logger = logging.getLogger(__name__)


class VectorIndexing(BaseIndexing):
    """Ingest the document, run through the embedding, and store the embedding in a
    vector store.

    This pipeline supports the following set of inputs:
        - List of documents
        - List of texts
    """

    cache_dir: Optional[str] = getattr(flowsettings, "KH_CHUNKS_OUTPUT_DIR", None)
    vector_store: BaseVectorStore
    doc_store: Optional[BaseDocumentStore] = None
    embedding: BaseEmbeddings
    count_: int = 0

    def to_retrieval_pipeline(self, *args, **kwargs):
        """Convert the indexing pipeline to a retrieval pipeline"""
        return VectorRetrieval(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            **kwargs,
        )

    def write_chunk_to_file(self, docs: list[Document]):
        # save the chunks content into markdown format
        if self.cache_dir:
            file_name = docs[0].metadata.get("file_name")
            if not file_name:
                return

            file_name = Path(file_name)
            for i in range(len(docs)):
                markdown_content = ""
                if "page_label" in docs[i].metadata:
                    page_label = str(docs[i].metadata["page_label"])
                    markdown_content += f"Page label: {page_label}"
                if "file_name" in docs[i].metadata:
                    filename = docs[i].metadata["file_name"]
                    markdown_content += f"\nFile name: {filename}"
                if "section" in docs[i].metadata:
                    section = docs[i].metadata["section"]
                    markdown_content += f"\nSection: {section}"
                if "type" in docs[i].metadata:
                    if docs[i].metadata["type"] == "image":
                        image_origin = docs[i].metadata["image_origin"]
                        image_origin = f'<p><img src="{image_origin}"></p>'
                        markdown_content += f"\nImage origin: {image_origin}"
                if docs[i].text:
                    markdown_content += f"\ntext:\n{docs[i].text}"

                with open(
                    Path(self.cache_dir) / f"{file_name.stem}_{self.count_+i}.md",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(markdown_content)

    def add_to_docstore(self, docs: list[Document]):
        if self.doc_store:
            print("Adding documents to doc store")
            self.doc_store.add(docs)

    def add_to_vectorstore(self, docs: list[Document]):
        # in case we want to skip embedding
        if self.vector_store:
            print(f"Getting embeddings for {len(docs)} nodes")
            embeddings = self.embedding(docs)
            print("Adding embeddings to vector store")
            self.vector_store.add(
                embeddings=embeddings,
                metadatas=[doc.metadata or {} for doc in docs],
                ids=[t.doc_id for t in docs],
            )

    def run(self, text: str | list[str] | Document | list[Document]):
        input_: list[Document] = []
        if not isinstance(text, list):
            text = [text]

        for item in cast(list, text):
            if isinstance(item, str):
                input_.append(Document(text=item, id_=str(uuid.uuid4())))
            elif isinstance(item, Document):
                input_.append(item)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )

        self.add_to_vectorstore(input_)
        self.add_to_docstore(input_)
        self.write_chunk_to_file(input_)
        self.count_ += len(input_)


class VectorRetrieval(BaseRetrieval):
    """Retrieve list of documents from vector store"""

    vector_store: BaseVectorStore
    doc_store: Optional[BaseDocumentStore] = None
    embedding: BaseEmbeddings
    rerankers: Sequence[BaseReranking] = []
    top_k: int = 5
    first_round_top_k_mult: int = 10
    retrieval_mode: str = "hybrid"  # vector, text, hybrid
    max_per_parent_or_section: Optional[int] = 2

    def _filter_docs(
        self, documents: list[RetrievedDocument], top_k: int | None = None
    ):
        if top_k:
            documents = documents[:top_k]
        return documents

    @staticmethod
    def _normalize_ids(ids: Sequence[str] | None) -> list[str] | None:
        if ids is None:
            return None
        if isinstance(ids, str):
            return [ids]
        return list(dict.fromkeys(str(doc_id) for doc_id in ids if doc_id is not None))

    @staticmethod
    def _deduplicate_docs(
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        unique: list[RetrievedDocument] = []
        seen: set[str] = set()
        for document in documents:
            doc_id = document.doc_id
            if doc_id is not None and doc_id in seen:
                continue
            if doc_id is not None:
                seen.add(doc_id)
            unique.append(document)
        return unique

    @staticmethod
    def _filter_to_scope(
        documents: list[RetrievedDocument], scope: list[str] | None
    ) -> list[RetrievedDocument]:
        if scope is None:
            return documents
        allowed = set(scope)
        return [document for document in documents if document.doc_id in allowed]

    @staticmethod
    def _metadata_predicate(
        filters: Any = None, where: Any = None
    ) -> Callable[[Mapping[str, Any]], bool] | None:
        """Build a fail-closed predicate for the supported metadata-filter subset."""

        def unsupported(detail: str) -> ValueError:
            return ValueError(f"Unsupported metadata filter: {detail}")

        def combine(
            predicates: list[Callable[[Mapping[str, Any]], bool]], condition: Any
        ) -> Callable[[Mapping[str, Any]], bool]:
            if not predicates:
                raise unsupported("empty filter group")
            if condition == FilterCondition.AND:
                return lambda metadata: all(
                    predicate(metadata) for predicate in predicates
                )
            if condition == FilterCondition.OR:
                return lambda metadata: any(
                    predicate(metadata) for predicate in predicates
                )
            raise unsupported(f"unknown condition {condition!r}")

        def parse_llama_filters(
            node: Any,
        ) -> Callable[[Mapping[str, Any]], bool]:
            if isinstance(node, MetadataFilter):
                key = node.key
                operator = node.operator
                expected = node.value
                if not isinstance(key, str) or not key:
                    raise unsupported("metadata key must be a non-empty string")
                if operator == FilterOperator.EQ:
                    return (
                        lambda metadata: key in metadata and metadata[key] == expected
                    )
                if operator == FilterOperator.IN:
                    if not isinstance(expected, (list, tuple)):
                        raise unsupported("IN requires a list of values")
                    return lambda metadata: key in metadata and any(
                        metadata[key] == value for value in expected
                    )
                raise unsupported(f"operator {operator!r}")

            if isinstance(node, MetadataFilters):
                return combine(
                    [parse_llama_filters(child) for child in node.filters],
                    node.condition,
                )

            raise unsupported(f"expected MetadataFilter(s), got {type(node).__name__}")

        def parse_chroma_where(
            node: Any,
        ) -> Callable[[Mapping[str, Any]], bool]:
            if not isinstance(node, Mapping) or not node:
                raise unsupported("where must be a non-empty mapping")

            if len(node) == 1:
                operator, children = next(iter(node.items()))
                if operator in {"$and", "$or"}:
                    if not isinstance(children, (list, tuple)):
                        raise unsupported(f"{operator} requires a list of filters")
                    return combine(
                        [parse_chroma_where(child) for child in children],
                        (
                            FilterCondition.AND
                            if operator == "$and"
                            else FilterCondition.OR
                        ),
                    )

            if len(node) != 1:
                raise unsupported("where clauses must use one explicit operator")
            key, constraint = next(iter(node.items()))
            if not isinstance(key, str) or not key or key.startswith("$"):
                raise unsupported("metadata key must be a non-empty string")
            if not isinstance(constraint, Mapping) or len(constraint) != 1:
                raise unsupported(f"where clause for {key!r} must use one operator")
            operator, expected = next(iter(constraint.items()))
            if operator == "$eq":
                return lambda metadata: key in metadata and metadata[key] == expected
            if operator == "$in":
                if not isinstance(expected, (list, tuple)):
                    raise unsupported("$in requires a list of values")
                return lambda metadata: key in metadata and any(
                    metadata[key] == value for value in expected
                )
            raise unsupported(f"where operator {operator!r}")

        predicates = []
        if filters is not None:
            predicates.append(parse_llama_filters(filters))
        if where is not None:
            predicates.append(parse_chroma_where(where))
        if not predicates:
            return None
        return combine(predicates, FilterCondition.AND)

    @staticmethod
    def _filter_to_metadata(
        documents: list[RetrievedDocument],
        predicate: Callable[[Mapping[str, Any]], bool] | None,
    ) -> list[RetrievedDocument]:
        if predicate is None:
            return documents
        return [
            document for document in documents if predicate(document.metadata or {})
        ]

    @staticmethod
    def _lexical_available(doc_store: BaseDocumentStore) -> bool:
        """Honor an explicit backend capability flag and retain legacy adapters."""
        capability = getattr(doc_store, "supports_lexical_search", None)
        if capability is not None:
            return bool(capability)
        query_method = getattr(type(doc_store), "query", None)
        return callable(query_method) and query_method is not BaseDocumentStore.query

    @staticmethod
    def _trace_update(trace: Any | None, **fields):
        trace_update(trace, **fields)

    @staticmethod
    def _trace_event(trace: Any | None, stage: str, **fields):
        trace_event(trace, stage, **fields)

    @staticmethod
    def _candidate_trace_records(
        documents: list[RetrievedDocument],
        *,
        branch: str,
        score_availability: Mapping[str, bool] | None = None,
    ) -> list[dict[str, Any]]:
        candidates = []
        for document in documents:
            doc_id = document.doc_id
            if branch == "vector":
                available = (
                    doc_id is not None
                    and score_availability is not None
                    and score_availability.get(doc_id, False)
                )
            elif branch == "reranker":
                rerank_score = (getattr(document, "retrieval_metadata", {}) or {}).get(
                    "rerank_score"
                )
                if rerank_score is not None:
                    try:
                        available = math.isfinite(float(rerank_score))
                    except (TypeError, ValueError):
                        available = False
                    score = rerank_score if available else None
                else:
                    # The legacy lexical branch stores -1.0 as a missing-score
                    # sentinel. Other reranker output scores are real at this point.
                    try:
                        document_score = getattr(document, "score", None)
                        available = (
                            document_score is not None and float(document_score) != -1.0
                        )
                    except (TypeError, ValueError):
                        available = False
                    score = getattr(document, "score", None) if available else None
            else:
                available = False
            if branch != "reranker":
                score = getattr(document, "score", None) if available else None
            candidates.append(
                {
                    "id": doc_id,
                    "score": score,
                    "score_available": bool(available),
                }
            )
        return candidates

    def _vector_candidates(
        self,
        embedding: list[float],
        candidate_k: int,
        scope: list[str] | None,
        query_kwargs: dict[str, Any],
        score_availability: dict[str, bool] | None = None,
    ) -> list[RetrievedDocument]:
        assert self.doc_store is not None
        _, scores, ids = self.vector_store.query(
            embedding=embedding,
            top_k=candidate_k,
            ids=scope,
            **query_kwargs,
        )

        # Store adapters may return documents in a different order than requested.
        # Associate every score with the vector result ID before loading documents.
        score_by_id: dict[str, float] = {}
        unique_ids: list[str] = []
        seen: set[str] = set()
        for index, doc_id in enumerate(ids):
            if doc_id is None or doc_id in seen:
                continue
            if scope is not None and doc_id not in scope:
                continue
            seen.add(doc_id)
            unique_ids.append(doc_id)
            score_by_id[doc_id] = scores[index] if index < len(scores) else -1.0
            if score_availability is not None:
                score_availability[doc_id] = (
                    index < len(scores) and scores[index] is not None
                )

        if not unique_ids:
            return []

        docs_by_id = {doc.doc_id: doc for doc in self.doc_store.get(unique_ids)}
        return [
            RetrievedDocument(**docs_by_id[doc_id].to_dict(), score=score_by_id[doc_id])
            for doc_id in unique_ids
            if doc_id in docs_by_id
        ]

    def _policy_routes(
        self,
        *,
        routes: list[str],
        policy: RetrievalPolicy,
        candidate_k: int,
        scope: list[str] | None,
        fallback_scope: list[str] | None,
        metadata_filter: Callable[[Mapping[str, Any]], bool] | None,
        query_kwargs: dict[str, Any],
        trace: Any | None,
    ):
        """Run bounded dense/lexical routes and fuse only authorized records."""
        if self.doc_store is None:
            raise ValueError(
                "doc_store is not provided. Please provide a doc_store to "
                "retrieve the documents"
            )

        policy_for_fusion = replace(policy, candidate_k=candidate_k)
        lexical_available = self._lexical_available(self.doc_store)
        dense_enabled = self.retrieval_mode in {"vector", "hybrid"}
        lexical_enabled = self.retrieval_mode in {"text", "hybrid"}
        if not dense_enabled and not lexical_enabled:
            raise ValueError(f"Unknown retrieval mode: {self.retrieval_mode}")

        def collect(query_scope):
            batches: list[RecallBatch] = []
            errors: dict[str, Exception] = {}
            dense_documents: list[RetrievedDocument] = []
            lexical_documents: list[RetrievedDocument] = []
            for query_index, route_query in enumerate(routes):
                if dense_enabled:
                    score_availability: dict[str, bool] = {}
                    documents: list[RetrievedDocument] = []
                    try:
                        query_embedding = self.embedding(route_query)[0].embedding
                        documents = self._vector_candidates(
                            query_embedding,
                            candidate_k,
                            query_scope,
                            query_kwargs,
                            score_availability=score_availability,
                        )
                        documents = self._filter_to_scope(documents, query_scope)
                        documents = self._filter_to_metadata(documents, metadata_filter)
                        status = "available" if documents else "empty"
                    except Exception as exc:
                        errors.setdefault("dense", exc)
                        status = "error"
                    dense_documents.extend(documents)
                    batches.append(
                        RecallBatch(
                            branch="dense",
                            query_index=query_index,
                            query=route_query,
                            documents=tuple(documents),
                            status=status,
                            error_type=(
                                type(errors["dense"]).__name__
                                if status == "error"
                                else None
                            ),
                        )
                    )
                    self._trace_event(
                        trace,
                        "recall_route",
                        branch="dense",
                        query_index=query_index,
                        status=status,
                        scope_ids=query_scope,
                        requested_candidate_depth=candidate_k,
                        observed_candidate_depth=len(documents),
                        candidates=self._candidate_trace_records(
                            documents,
                            branch="vector",
                            score_availability=score_availability,
                        ),
                        error_type=(
                            type(errors["dense"]).__name__
                            if status == "error"
                            else None
                        ),
                    )

                if lexical_enabled:
                    if not lexical_available:
                        batches.append(
                            RecallBatch(
                                branch="lexical",
                                query_index=query_index,
                                query=route_query,
                                documents=(),
                                status="unavailable",
                            )
                        )
                        status = "unavailable"
                        documents = []
                    else:
                        documents = []
                        try:
                            lexical_results = self.doc_store.query(
                                route_query,
                                top_k=candidate_k,
                                doc_ids=query_scope,
                            )
                            documents = [
                                RetrievedDocument(**document.to_dict(), score=-1.0)
                                for document in lexical_results
                            ]
                            documents = self._filter_to_scope(documents, query_scope)
                            documents = self._filter_to_metadata(
                                documents, metadata_filter
                            )
                            documents = self._deduplicate_docs(documents)
                            status = "available" if documents else "empty"
                        except Exception as exc:
                            errors.setdefault("lexical", exc)
                            status = "error"
                        batches.append(
                            RecallBatch(
                                branch="lexical",
                                query_index=query_index,
                                query=route_query,
                                documents=tuple(documents),
                                status=status,
                                error_type=(
                                    type(errors["lexical"]).__name__
                                    if status == "error"
                                    else None
                                ),
                            )
                        )
                    lexical_documents.extend(documents)
                    self._trace_event(
                        trace,
                        "recall_route",
                        branch="lexical",
                        query_index=query_index,
                        status=status,
                        scope_ids=query_scope,
                        requested_candidate_depth=candidate_k,
                        observed_candidate_depth=len(documents),
                        candidates=self._candidate_trace_records(
                            documents, branch="lexical"
                        ),
                        score_available=False,
                        error_type=(
                            type(errors["lexical"]).__name__
                            if status == "error"
                            else None
                        ),
                    )
            fused = fuse_batches(batches, policy_for_fusion)
            fused = self._deduplicate_docs(self._filter_to_scope(fused, query_scope))
            fused = self._filter_to_metadata(fused, metadata_filter)
            self._trace_event(
                trace,
                "fusion",
                ids=[document.doc_id for document in fused],
                scores=[
                    (document.retrieval_metadata or {}).get("fusion_score")
                    for document in fused
                ],
                candidate_depth=candidate_k,
                max_fused_candidates=policy.max_fused_candidates,
            )
            return fused, batches, errors, dense_documents, lexical_documents

        result, batches, errors, dense_docs, lexical_docs = collect(scope)
        fallback_used = False
        if (
            not result
            and not errors
            and scope is not None
            and (fallback_scope is None or bool(fallback_scope))
            and set(scope) != set(fallback_scope or ())
        ):
            fallback_used = True
            self._trace_event(
                trace,
                "scope_fallback",
                reason="zero_scoped_hits",
                fallback_scope_ids=fallback_scope,
            )
            result, batches, errors, dense_docs, lexical_docs = collect(fallback_scope)
            scope = fallback_scope

        had_successful_route = any(
            batch.status in {"available", "empty"} for batch in batches
        )
        if errors:
            self._trace_update(
                trace,
                branch_errors={
                    branch: f"{type(error).__name__}: {error}"
                    for branch, error in errors.items()
                },
            )
        if errors and not had_successful_route:
            details = "; ".join(
                f"{branch}: {type(error).__name__}: {error}"
                for branch, error in errors.items()
            )
            raise RuntimeError(f"retrieval branches failed: {details}") from next(
                iter(errors.values())
            )

        lexical_statuses = [
            batch.status for batch in batches if batch.branch == "lexical"
        ]
        if not lexical_enabled:
            lexical_status = "not_used"
        elif lexical_statuses and all(
            status == "unavailable" for status in lexical_statuses
        ):
            lexical_status = "unavailable"
        elif "error" in lexical_statuses:
            lexical_status = "error"
        elif any(status == "available" for status in lexical_statuses):
            lexical_status = "available"
        else:
            lexical_status = "empty"

        dense_statuses = [batch.status for batch in batches if batch.branch == "dense"]
        if not dense_enabled:
            dense_status = "not_used"
        elif "error" in dense_statuses:
            dense_status = "error"
        elif any(status == "available" for status in dense_statuses):
            dense_status = "available"
        else:
            dense_status = "empty"

        self._trace_update(
            trace,
            scope_status=(
                "fallback"
                if fallback_used
                else ("scoped" if scope is not None else "global")
            ),
            scope_ids=scope,
            candidate_k=candidate_k,
            lexical_status=lexical_status,
            lexical_result_count=len(lexical_docs),
            scope_fallback=fallback_used,
            scope_fallback_reason="zero_scoped_hits" if fallback_used else None,
            route_statuses=[
                {
                    "branch": batch.branch,
                    "query_index": batch.query_index,
                    "status": batch.status,
                    "error_type": batch.error_type,
                }
                for batch in batches
            ],
        )
        if trace is not None:
            self._trace_event(
                trace,
                "merged",
                ids=[document.doc_id for document in result],
                dense_status=dense_status,
                lexical_status=lexical_status,
                fusion_order=[document.doc_id for document in result],
            )
        return (
            result,
            lexical_status,
            errors,
            len(lexical_docs),
            dense_docs,
            lexical_docs,
            dense_status,
            had_successful_route,
            fallback_used,
        )

    def run(
        self,
        text: str | Document,
        top_k: Optional[int] = None,
        scope: Sequence[str] | None = None,
        fallback_scope: Sequence[str] | None = None,
        trace: Any | None = None,
        enriched_query: EnrichedQuery | None = None,
        retrieval_policy: RetrievalPolicy | None = None,
        candidate_k: int | None = None,
        **kwargs,
    ) -> list[RetrievedDocument]:
        """Retrieve a list of documents from vector store

        Args:
            text: the text to retrieve similar documents
            top_k: number of top similar documents to return

        Returns:
            list[RetrievedDocument]: list of retrieved documents
        """
        if top_k is None:
            top_k = self.top_k
        if candidate_k is not None and (
            isinstance(candidate_k, bool)
            or not isinstance(candidate_k, int)
            or candidate_k < 1
        ):
            raise ValueError("candidate_k must be a positive integer")
        explicit_candidate_k = candidate_k
        if retrieval_policy is not None and not isinstance(
            retrieval_policy, RetrievalPolicy
        ):
            raise TypeError("retrieval_policy must be a RetrievalPolicy")
        if enriched_query is not None and not isinstance(enriched_query, EnrichedQuery):
            raise TypeError("enriched_query must be an EnrichedQuery")
        policy_enabled = bool(retrieval_policy and retrieval_policy.enabled)

        do_extend = kwargs.pop("do_extend", False)
        thumbnail_count = kwargs.pop("thumbnail_count", 3)
        legacy_doc_ids = kwargs.pop("doc_ids", None)
        if scope is None and legacy_doc_ids is not None:
            scope = legacy_doc_ids

        metadata_filter = self._metadata_predicate(
            filters=kwargs.get("filters"), where=kwargs.get("where")
        )
        if kwargs.get("where_document") is not None:
            raise ValueError(
                "Unsupported metadata filter: where_document is not supported"
            )

        # ``scope`` is the planner's exact chunk scope. ``fallback_scope`` is the
        # caller-visible chunk allowlist. Even a global/ambiguous plan is restricted
        # to that allowlist when one was provided.
        requested_scope = self._normalize_ids(scope)
        visible_scope = self._normalize_ids(fallback_scope)
        if requested_scope is not None and visible_scope is not None:
            visible_ids = set(visible_scope)
            requested_scope = [
                doc_id for doc_id in requested_scope if doc_id in visible_ids
            ]
        elif requested_scope is None:
            requested_scope = visible_scope

        if requested_scope == []:
            self._trace_update(
                trace,
                scope_status="empty",
                lexical_status="not_queried",
                scope_fallback=False,
            )
            self._trace_event(trace, "no_search", reason="empty_scope", scope_ids=[])
            return []

        if do_extend:
            top_k_first_round = top_k * self.first_round_top_k_mult
        else:
            top_k_first_round = top_k

        # Scoped calls need spare candidates so post-filtering remains effective
        # when a backend ignores IDs or metadata filters.
        candidate_k = explicit_candidate_k or top_k_first_round
        if requested_scope is not None:
            if explicit_candidate_k is None:
                candidate_k = max(candidate_k, top_k * self.first_round_top_k_mult)

        if self.doc_store is None:
            raise ValueError(
                "doc_store is not provided. Please provide a doc_store to "
                "retrieve the documents"
            )

        query = text.text if isinstance(text, Document) else text
        self._trace_event(trace, "retrieval_query", semantic_query=query)
        if policy_enabled:
            variants = (
                list(enriched_query.variants) if enriched_query is not None else [query]
            )
            normalized_routes: list[str] = []
            seen_routes: set[str] = set()
            for route_query in variants:
                normalized = " ".join(route_query.casefold().split())
                if normalized in seen_routes:
                    continue
                seen_routes.add(normalized)
                normalized_routes.append(route_query)
                if len(normalized_routes) >= retrieval_policy.max_variants:
                    break
            if not normalized_routes:
                normalized_routes = [query]
            if enriched_query is not None:
                rerank_query = enriched_query.standalone_query
            else:
                rerank_query = query
            policy_candidate_k = (
                explicit_candidate_k
                if explicit_candidate_k is not None
                else retrieval_policy.candidate_k
            )
        else:
            normalized_routes = []
            rerank_query = query
            policy_candidate_k = candidate_k
        lexical_available = self._lexical_available(self.doc_store)
        lexical_status = "not_used"
        branch_errors: dict[str, Exception] = {}
        policy_route_succeeded = False
        policy_fallback_used = False
        query_embedding = None
        if self.retrieval_mode in {"vector", "hybrid"} and not policy_enabled:
            try:
                query_embedding = self.embedding(text)[0].embedding
            except Exception as exc:
                self._trace_update(
                    trace, branch_errors={"vector": f"{type(exc).__name__}: {exc}"}
                )
                self._trace_event(
                    trace,
                    "backend_error",
                    branch="vector_embedding",
                    error_type=type(exc).__name__,
                )
                raise

        attempt_number = 0

        def record_recall_attempt(
            query_scope,
            vector_docs,
            lexical_docs,
            lexical_status,
            vector_status,
            errors,
            score_availability,
        ):
            nonlocal attempt_number
            if trace is None:
                return
            attempt_number += 1
            self._trace_event(
                trace,
                "recall_attempt",
                attempt=attempt_number,
                scope_ids=query_scope,
                vector_status=vector_status,
                lexical_status=lexical_status,
                vector_candidates=self._candidate_trace_records(
                    vector_docs,
                    branch="vector",
                    score_availability=score_availability,
                ),
                lexical_candidates=self._candidate_trace_records(
                    lexical_docs, branch="lexical"
                ),
                backend_errors={
                    branch: {"type": type(error).__name__}
                    for branch, error in errors.items()
                },
            )

        def retrieve_candidates(
            query_scope: list[str] | None,
        ) -> tuple[
            list[RetrievedDocument],
            str,
            dict[str, Exception],
            int,
            list[RetrievedDocument],
            list[RetrievedDocument],
            str,
        ]:
            nonlocal policy_route_succeeded, policy_fallback_used, requested_scope
            if policy_enabled:
                (
                    policy_result,
                    policy_lexical_status,
                    policy_errors,
                    policy_lexical_count,
                    policy_dense_docs,
                    policy_lexical_docs,
                    policy_dense_status,
                    policy_route_succeeded,
                    policy_fallback_used,
                ) = self._policy_routes(
                    routes=normalized_routes,
                    policy=retrieval_policy,
                    candidate_k=policy_candidate_k,
                    scope=query_scope,
                    fallback_scope=visible_scope,
                    metadata_filter=metadata_filter,
                    query_kwargs=kwargs,
                    trace=trace,
                )
                if policy_fallback_used:
                    requested_scope = visible_scope
                return (
                    policy_result,
                    policy_lexical_status,
                    policy_errors,
                    policy_lexical_count,
                    policy_dense_docs,
                    policy_lexical_docs,
                    policy_dense_status,
                )

            errors: dict[str, Exception] = {}
            vector_docs: list[RetrievedDocument] = []
            lexical_docs: list[RetrievedDocument] = []
            status = "not_used"
            vector_status = "not_used"
            vector_score_availability: dict[str, bool] | None = (
                {} if trace is not None else None
            )

            if self.retrieval_mode == "vector":
                try:
                    vector_docs = self._vector_candidates(
                        query_embedding,
                        candidate_k,
                        query_scope,
                        kwargs,
                        score_availability=vector_score_availability,
                    )
                except Exception as exc:
                    errors["vector"] = exc
                vector_docs = self._filter_to_metadata(
                    self._filter_to_scope(vector_docs, query_scope), metadata_filter
                )
                vector_status = (
                    "error"
                    if "vector" in errors
                    else ("available" if vector_docs else "empty")
                )
                record_recall_attempt(
                    query_scope,
                    vector_docs,
                    [],
                    status,
                    vector_status,
                    errors,
                    vector_score_availability,
                )
                return (
                    vector_docs,
                    status,
                    errors,
                    0,
                    vector_docs,
                    [],
                    vector_status,
                )

            if self.retrieval_mode == "text":
                if not lexical_available:
                    record_recall_attempt(
                        query_scope,
                        [],
                        [],
                        "unavailable",
                        "not_used",
                        errors,
                        vector_score_availability,
                    )
                    return [], "unavailable", errors, 0, [], [], "not_used"
                try:
                    docs = self.doc_store.query(
                        query, top_k=candidate_k, doc_ids=query_scope
                    )
                    lexical_docs = [
                        RetrievedDocument(**doc.to_dict(), score=-1.0) for doc in docs
                    ]
                except Exception as exc:
                    errors["lexical"] = exc
                    status = "error"
                lexical_docs = self._filter_to_scope(lexical_docs, query_scope)
                lexical_docs = self._filter_to_metadata(lexical_docs, metadata_filter)
                if status != "error":
                    status = "available" if lexical_docs else "empty"
                lexical_docs = self._deduplicate_docs(lexical_docs)
                record_recall_attempt(
                    query_scope,
                    [],
                    lexical_docs,
                    status,
                    "not_used",
                    errors,
                    vector_score_availability,
                )
                return (
                    lexical_docs,
                    status,
                    errors,
                    len(lexical_docs),
                    [],
                    lexical_docs,
                    "not_used",
                )

            if self.retrieval_mode != "hybrid":
                raise ValueError(f"Unknown retrieval mode: {self.retrieval_mode}")

            if not lexical_available:
                status = "unavailable"

            def query_vectorstore():
                nonlocal vector_docs
                try:
                    vector_docs = self._vector_candidates(
                        query_embedding,
                        candidate_k,
                        query_scope,
                        kwargs,
                        score_availability=vector_score_availability,
                    )
                except Exception as exc:
                    errors["vector"] = exc

            def query_docstore():
                nonlocal lexical_docs
                nonlocal status
                if not lexical_available:
                    return
                try:
                    docs = self.doc_store.query(
                        query, top_k=candidate_k, doc_ids=query_scope
                    )
                    lexical_docs = [
                        RetrievedDocument(**doc.to_dict(), score=-1.0) for doc in docs
                    ]
                except Exception as exc:
                    errors["lexical"] = exc
                    status = "error"

            vector_thread = threading.Thread(target=query_vectorstore)
            vector_thread.start()
            lexical_thread = None
            if lexical_available:
                lexical_thread = threading.Thread(target=query_docstore)
                lexical_thread.start()

            vector_thread.join()
            if lexical_thread is not None:
                lexical_thread.join()

            lexical_docs = self._filter_to_scope(lexical_docs, query_scope)
            lexical_docs = self._filter_to_metadata(lexical_docs, metadata_filter)
            if lexical_available and "lexical" not in errors:
                status = "available" if lexical_docs else "empty"
            vector_docs = self._filter_to_scope(vector_docs, query_scope)
            vector_docs = self._filter_to_metadata(vector_docs, metadata_filter)
            vector_status = (
                "error"
                if "vector" in errors
                else ("available" if vector_docs else "empty")
            )
            merged = self._deduplicate_docs(lexical_docs + vector_docs)
            record_recall_attempt(
                query_scope,
                vector_docs,
                lexical_docs,
                status,
                vector_status,
                errors,
                vector_score_availability,
            )
            return (
                merged,
                status,
                errors,
                len(lexical_docs),
                vector_docs,
                lexical_docs,
                vector_status,
            )

        (
            result,
            lexical_status,
            branch_errors,
            lexical_result_count,
            vector_candidates,
            lexical_candidates,
            vector_status,
        ) = retrieve_candidates(requested_scope)
        result = self._deduplicate_docs(self._filter_to_scope(result, requested_scope))
        result = self._filter_to_metadata(result, metadata_filter)

        # A missing caller allowlist means the caller has not supplied an
        # additional visibility boundary, so a zero-hit planned scope may retry
        # globally. An explicit empty allowlist returned above and never reaches
        # this point.
        fallback_ids = visible_scope
        should_retry = (
            not policy_enabled
            and scope is not None
            and not result
            and not branch_errors
            and (fallback_ids is None or bool(fallback_ids))
            and set(requested_scope or ()) != set(fallback_ids or ())
        )
        self._trace_update(
            trace,
            scope_status=(
                "fallback"
                if policy_enabled and policy_fallback_used
                else ("scoped" if requested_scope is not None else "global")
            ),
            scope_ids=requested_scope,
            candidate_k=policy_candidate_k if policy_enabled else candidate_k,
            lexical_status=lexical_status,
            lexical_result_count=lexical_result_count,
            scope_fallback=policy_fallback_used if policy_enabled else False,
        )
        if should_retry:
            self._trace_update(
                trace,
                scope_fallback=True,
                scope_fallback_reason="zero_scoped_hits",
            )
            self._trace_event(
                trace,
                "scope_fallback",
                reason="zero_scoped_hits",
                fallback_scope_ids=fallback_ids,
            )
            (
                result,
                lexical_status,
                branch_errors,
                lexical_result_count,
                vector_candidates,
                lexical_candidates,
                vector_status,
            ) = retrieve_candidates(fallback_ids)
            result = self._deduplicate_docs(self._filter_to_scope(result, fallback_ids))
            result = self._filter_to_metadata(result, metadata_filter)
            requested_scope = fallback_ids
            self._trace_update(
                trace,
                scope_status="fallback",
                scope_ids=fallback_ids,
                lexical_status=lexical_status,
                lexical_result_count=lexical_result_count,
            )

        if branch_errors:
            error_summary = {
                branch: f"{type(error).__name__}: {error}"
                for branch, error in branch_errors.items()
            }
            self._trace_update(trace, branch_errors=error_summary)
            self._trace_event(
                trace,
                "backend_error",
                errors={
                    branch: {"type": type(error).__name__}
                    for branch, error in branch_errors.items()
                },
            )
            if not result and not (policy_enabled and policy_route_succeeded):
                if self.retrieval_mode == "hybrid":
                    details = "; ".join(
                        f"{branch}: {message}"
                        for branch, message in error_summary.items()
                    )
                    raise RuntimeError(
                        f"retrieval branches failed: {details}"
                    ) from next(iter(branch_errors.values()))
                raise next(iter(branch_errors.values()))

        if lexical_status == "unavailable":
            self._trace_update(trace, lexical_status="unavailable")
        elif lexical_status == "empty":
            self._trace_update(trace, lexical_status="empty")

        if trace is not None:
            self._trace_event(trace, "merged", ids=[doc.doc_id for doc in result])

        # use additional reranker to re-order the document list
        if self.rerankers and text:
            policy_candidate_ids = {document.doc_id for document in result}
            for reranker in self.rerankers:
                # if reranker is LLMReranking, limit the document with top_k items only
                if isinstance(reranker, LLMReranking):
                    result = self._filter_docs(result, top_k=top_k)
                result = reranker.run(
                    documents=result,
                    query=(rerank_query if policy_enabled else text),
                )
                result = self._deduplicate_docs(
                    self._filter_to_scope(result, requested_scope)
                )
                result = self._filter_to_metadata(result, metadata_filter)
                if policy_enabled:
                    result = [
                        document
                        for document in result
                        if document.doc_id in policy_candidate_ids
                    ]
                reranker_name = getattr(
                    reranker,
                    "name",
                    type(reranker).__name__,
                )
                if trace is not None:
                    model_metadata = getattr(reranker, "metadata", None)
                    model_provenance = {
                        key: getattr(model_metadata, key)
                        for key in (
                            "model_id",
                            "revision",
                            "query_max_length",
                            "passage_max_length",
                            "device",
                        )
                        if getattr(model_metadata, key, None) is not None
                    }
                    self._trace_event(
                        trace,
                        "reranker",
                        name=str(reranker_name),
                        model_provenance=model_provenance,
                        candidates=self._candidate_trace_records(
                            result,
                            branch="reranker",
                        ),
                    )

        diversity_exclusions = []

        def record_diversity_exclusion(doc_id, reason):
            diversity_exclusions.append({"id": doc_id, "reason": reason})

        result = select_diverse_documents(
            result,
            top_k=top_k,
            parent_section_cap=self.max_per_parent_or_section,
            on_exclusion=(record_diversity_exclusion if trace is not None else None),
        )
        if trace is not None:
            self._trace_update(
                trace,
                diversity_selected_ids=[doc.doc_id for doc in result],
            )
            self._trace_event(
                trace,
                "diversity",
                excluded=diversity_exclusions,
                selected_ids=[doc.doc_id for doc in result],
            )
        print(f"Got raw {len(result)} retrieved documents")

        # add page thumbnails to the result if exists
        thumbnail_doc_ids: list[str] = []
        seen_thumbnail_ids: set[str] = set()
        # we should copy the text from retrieved text chunk
        # to the thumbnail to get relevant LLM score correctly
        text_thumbnail_docs: dict[str, RetrievedDocument] = {}
        allowed_thumbnail_ids = (
            set(requested_scope) if requested_scope is not None else None
        )

        raw_thumbnail_docs = []
        for doc in result:
            if doc.metadata.get("type") == "thumbnail":
                # change type to image to display on UI
                raw_thumbnail_docs.append(doc)
                continue
            thumbnail_id = doc.metadata.get("thumbnail_doc_id")
            if not isinstance(thumbnail_id, str) or not thumbnail_id:
                continue
            if (
                allowed_thumbnail_ids is not None
                and thumbnail_id not in allowed_thumbnail_ids
            ):
                continue
            if (
                len(thumbnail_doc_ids) < max(0, thumbnail_count)
                and thumbnail_id not in seen_thumbnail_ids
            ):
                thumbnail_doc_ids.append(thumbnail_id)
                seen_thumbnail_ids.add(thumbnail_id)
                text_thumbnail_docs[thumbnail_id] = doc

        linked_thumbnail_docs = (
            self.doc_store.get(list(thumbnail_doc_ids)) if thumbnail_doc_ids else []
        )
        print(
            "thumbnail docs",
            len(linked_thumbnail_docs),
            "non-thumbnail docs",
            len(result) - len(raw_thumbnail_docs),
            "raw-thumbnail docs",
            len(raw_thumbnail_docs),
        )
        linked_thumbnails_by_text_id: dict[str, RetrievedDocument] = {}

        thumbnails_by_id = {
            thumbnail_doc.doc_id: thumbnail_doc
            for thumbnail_doc in linked_thumbnail_docs
        }
        for thumbnail_id in thumbnail_doc_ids:
            thumbnail_doc = thumbnails_by_id.get(thumbnail_id)
            if thumbnail_doc is None:
                continue
            text_doc = text_thumbnail_docs.get(thumbnail_doc.doc_id)
            if text_doc is None:
                continue

            text_file_id = text_doc.metadata.get(
                "document_id"
            ) or text_doc.metadata.get("file_id")
            thumbnail_file_id = thumbnail_doc.metadata.get(
                "document_id"
            ) or thumbnail_doc.metadata.get("file_id")
            if (
                text_file_id is None
                or thumbnail_file_id is None
                or str(text_file_id) != str(thumbnail_file_id)
            ):
                continue

            doc_dict = thumbnail_doc.to_dict()
            doc_dict["id_"] = text_doc.doc_id
            doc_dict["content"] = text_doc.content
            doc_dict["metadata"]["type"] = "image"
            for key in text_doc.metadata:
                if key not in doc_dict["metadata"]:
                    doc_dict["metadata"][key] = text_doc.metadata[key]

            image_doc = RetrievedDocument(**doc_dict, score=text_doc.score)
            if metadata_filter is not None and not metadata_filter(
                image_doc.metadata or {}
            ):
                continue
            linked_thumbnails_by_text_id[text_doc.doc_id] = image_doc

        raw_thumbnail_count = 0
        final_result = []
        for doc in result:
            if doc.metadata.get("type") == "thumbnail":
                if raw_thumbnail_count >= max(0, thumbnail_count):
                    continue
                doc.metadata["type"] = "image"
                raw_thumbnail_count += 1
                final_result.append(doc)
            else:
                final_result.append(linked_thumbnails_by_text_id.get(doc.doc_id, doc))

        final_result = final_result[: max(0, top_k)]
        if trace is not None:
            self._trace_event(
                trace,
                "final",
                ids=[doc.doc_id for doc in final_result],
            )
        return final_result


class TextVectorQA(BaseComponent):
    retrieving_pipeline: BaseRetrieval
    qa_pipeline: BaseComponent

    def run(self, question, **kwargs):
        retrieved_documents = self.retrieving_pipeline(question, **kwargs)
        return self.qa_pipeline(question, retrieved_documents, **kwargs)
