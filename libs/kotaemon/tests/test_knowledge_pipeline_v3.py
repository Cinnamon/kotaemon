"""Behavior tests for policy-enabled, scope-safe multi-route retrieval."""

from __future__ import annotations

import pytest

from kotaemon.base import Document, DocumentWithEmbedding, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.knowledge.planning.query_planner import KnowledgeSource
from kotaemon.indices.knowledge.planning.retrieval_plan import RetrievalPlan
from kotaemon.indices.knowledge.retrieval.contracts import (
    EnrichedQuery,
    RetrievalPolicy,
)
from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService
from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace
from kotaemon.indices.rankings import BaseReranking
from kotaemon.models import BgeM3Reranking
from kotaemon.storages.docstores.base import BaseDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore

from .test_knowledge_service import (
    MemoryCatalog,
    MemoryDocstore,
    source,
)


class CapturingPlanner:
    def __init__(self, source_ids=None):
        self.source_ids = source_ids
        self.calls = []

    def plan(self, query, catalog, **kwargs):
        visible = catalog.list_sources(kwargs.get("allowed_source_ids"))
        self.calls.append((query, tuple(row.source_id for row in visible), kwargs))
        return RetrievalPlan(
            query=query,
            semantic_query=query,
            reason="test fixture",
            source_ids=(None if self.source_ids is None else tuple(self.source_ids)),
        )


class FakeEmbedding(BaseEmbeddings):
    def __init__(self):
        super().__init__()
        object.__setattr__(self, "_queries", [])

    @property
    def queries(self):
        return self._queries

    def run(self, text, *args, **kwargs):
        query = text if isinstance(text, str) else text.text
        self._queries.append(query)
        return [DocumentWithEmbedding(content=query, embedding=[0.1, 0.2])]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, ids_by_scope=None, *, error=None):
        super().__init__()
        object.__setattr__(self, "_ids_by_scope", ids_by_scope or {})
        object.__setattr__(self, "_error", error)
        object.__setattr__(self, "_calls", [])

    @property
    def calls(self):
        return self._calls

    def query(self, embedding, top_k=1, ids=None, **kwargs):
        self._calls.append({"ids": ids, "top_k": top_k, **kwargs})
        if self._error:
            raise self._error
        result_ids = self._ids_by_scope.get(tuple(ids) if ids is not None else None, [])
        return [], [0.8 - 0.01 * i for i in range(len(result_ids))], result_ids

    def add(self, embeddings, metadatas=None, ids=None):
        return ids or []

    def delete(self, ids, **kwargs):
        pass

    def drop(self):
        pass


class FakeDocumentStore(BaseDocumentStore):
    supports_lexical_search = True

    def __init__(self, documents, *, lexical_ids=None, lexical_error=None):
        self.documents = {document.doc_id: document for document in documents}
        self.lexical_ids = lexical_ids or []
        self.lexical_error = lexical_error
        self.query_calls = []

    def get(self, ids):
        return [self.documents[doc_id] for doc_id in ids if doc_id in self.documents]

    def query(self, query, top_k=10, doc_ids=None):
        self.query_calls.append({"query": query, "top_k": top_k, "doc_ids": doc_ids})
        if self.lexical_error:
            raise self.lexical_error
        return [self.documents[doc_id] for doc_id in self.lexical_ids[:top_k]]

    def add(self, docs, ids=None, **kwargs):
        for document in docs if isinstance(docs, list) else [docs]:
            self.documents[document.doc_id] = document

    def delete(self, ids):
        pass

    def get_all(self):
        return list(self.documents.values())

    def count(self):
        return len(self.documents)

    def drop(self):
        self.documents.clear()


class FakeReranker(BaseReranking):
    def __init__(self, output):
        super().__init__()
        object.__setattr__(self, "_output", output)
        object.__setattr__(self, "_calls", [])

    @property
    def calls(self):
        return self._calls

    def run(self, documents, query):
        self._calls.append((query, tuple(document.doc_id for document in documents)))
        return self._output


def _pipeline_service(
    *,
    sources,
    chunks_by_source,
    docs,
    vector_store,
    planner=None,
    lexical_ids=None,
    lexical_error=None,
    rerankers=(),
    retrieval_mode="hybrid",
):
    catalog = MemoryCatalog(sources, chunks_by_source)
    planner = planner or CapturingPlanner()
    document_store = FakeDocumentStore(
        docs, lexical_ids=lexical_ids, lexical_error=lexical_error
    )
    embedding = FakeEmbedding()
    vector_retriever = VectorRetrieval(
        vector_store=vector_store,
        doc_store=document_store,
        embedding=embedding,
        retrieval_mode=retrieval_mode,
        rerankers=rerankers,
    )
    service = KnowledgeService(
        planner=planner,
        catalog=catalog,
        retriever=vector_retriever,
        docstore=MemoryDocstore(docs),
    )
    return service, planner, vector_retriever, document_store, embedding


def _enriched(original="show the requested file", standalone="rewritten query"):
    variants = tuple(dict.fromkeys((standalone, original, "exact-code variant")))
    return EnrichedQuery(
        original_query=original,
        standalone_query=standalone,
        variants=variants,
        reason="test rewrite",
    )


def test_empty_visibility_does_not_enrich_or_retrieve():
    class UnreadableEnrichment:
        @property
        def variants(self):
            raise AssertionError("empty authorization must return before routes")

    rows = [source("visible", path="/team/visible.md")]
    catalog = MemoryCatalog(rows, {"visible": ["visible-chunk"]})
    planner = CapturingPlanner()
    calls = []
    service = KnowledgeService(
        planner=planner,
        catalog=catalog,
        retriever=lambda **kwargs: calls.append(kwargs),
        docstore=MemoryDocstore([]),
    )

    assert (
        service.search(
            "question",
            allowed_source_ids=[],
            enriched_query=UnreadableEnrichment(),
            retrieval_policy=RetrievalPolicy(enabled=True),
        )
        == []
    )
    assert planner.calls == []
    assert calls == []


def test_rewritten_name_cannot_escape_path_filter():
    docs = [
        Document(id_="alice-chunk", text="alice content"),
        Document(id_="bob-chunk", text="bob content"),
    ]
    sources = [
        source("alice", path="/team/alice/report.md"),
        source("bob", path="/team/bob/report.md"),
    ]
    vector = FakeVectorStore({("alice-chunk",): ["bob-chunk", "alice-chunk"]})
    service, planner, _retriever, store, _embedding = _pipeline_service(
        sources=sources,
        chunks_by_source={"alice": ["alice-chunk"], "bob": ["bob-chunk"]},
        docs=docs,
        vector_store=vector,
        planner=CapturingPlanner(source_ids=None),
        lexical_ids=["bob-chunk", "alice-chunk"],
    )

    result = service.search(
        "show the requested file",
        path="/team/alice",
        enriched_query=_enriched(standalone="Bob's report"),
        retrieval_policy=RetrievalPolicy(enabled=True, candidate_k=5),
    )

    assert [document.doc_id for document in result] == ["alice-chunk"]
    assert planner.calls[0][0] == "show the requested file"
    assert planner.calls[0][1] == ("alice",)
    assert vector.calls[0]["ids"] == ["alice-chunk"]
    assert all(call["doc_ids"] == ["alice-chunk"] for call in store.query_calls)
    assert all(
        call["query"]
        in {"Bob's report", "show the requested file", "exact-code variant"}
        for call in store.query_calls
    )


def test_all_variants_use_same_hard_scope():
    docs = [
        Document(id_="alice-a-chunk", text="first authorized chunk"),
        Document(id_="alice-b-chunk", text="second authorized chunk"),
        Document(id_="bob-c", text="out of path"),
    ]
    sources = [
        source("alice-a", path="/team/alice/guide.md"),
        source("alice-b", path="/team/alice/sub/extra.md"),
        source("bob", path="/team/bob/guide.md"),
    ]
    vector = FakeVectorStore(
        {
            ("alice-a-chunk",): [],
            ("alice-a-chunk", "alice-b-chunk"): [
                "alice-b-chunk",
                "bob-c",
            ],
        }
    )
    service, planner, _retriever, store, embedding = _pipeline_service(
        sources=sources,
        chunks_by_source={
            "alice-a": ["alice-a-chunk"],
            "alice-b": ["alice-b-chunk"],
            "bob": ["bob-c"],
        },
        docs=docs,
        vector_store=vector,
        planner=CapturingPlanner(source_ids=["alice-a"]),
        lexical_ids=["alice-b-chunk", "bob-c"],
    )
    trace = RetrievalTrace()

    result = service.search(
        "show Alice guide",
        path="/team/alice",
        enriched_query=_enriched("show Alice guide", "Bob guide"),
        retrieval_policy=RetrievalPolicy(
            enabled=True,
            candidate_k=4,
            max_fused_candidates=10,
            max_variants=3,
        ),
        trace=trace,
    )

    assert planner.calls[0][0] == "show Alice guide"
    assert planner.calls[0][1] == ("alice-a", "alice-b")
    assert [call["ids"] for call in vector.calls] == [["alice-a-chunk"]] * 3 + [
        ["alice-a-chunk", "alice-b-chunk"]
    ] * 3
    assert [call["doc_ids"] for call in store.query_calls] == [
        ["alice-a-chunk"]
    ] * 3 + [["alice-a-chunk", "alice-b-chunk"]] * 3
    assert embedding.queries == [
        "Bob guide",
        "show Alice guide",
        "exact-code variant",
        "Bob guide",
        "show Alice guide",
        "exact-code variant",
    ]
    assert [document.doc_id for document in result] == ["alice-b-chunk"]
    assert trace.to_dict()["scope_fallback"] is True


def test_one_branch_failure_degrades_to_the_other():
    allowed = Document(id_="allowed", text="lexical result")
    service, _planner, _retriever, _store, _embedding = _pipeline_service(
        sources=[source("source-a", path="/a.md")],
        chunks_by_source={"source-a": ["allowed"]},
        docs=[allowed],
        vector_store=FakeVectorStore(error=RuntimeError("dense failed")),
        planner=CapturingPlanner(source_ids=None),
        lexical_ids=["allowed"],
    )
    trace = RetrievalTrace()

    result = service.search(
        "query",
        enriched_query=_enriched("query", "query"),
        retrieval_policy=RetrievalPolicy(enabled=True),
        trace=trace,
    )

    assert [document.doc_id for document in result] == ["allowed"]
    route_statuses = trace.to_dict()["route_statuses"]
    assert {item["branch"]: item["status"] for item in route_statuses} == {
        "dense": "error",
        "lexical": "available",
    }
    assert trace.to_dict()["branch_errors"]["dense"]["type"] == "RuntimeError"


def test_both_branches_fail_raises():
    service, _planner, _retriever, _store, _embedding = _pipeline_service(
        sources=[source("source-a", path="/a.md")],
        chunks_by_source={"source-a": ["allowed"]},
        docs=[Document(id_="allowed", text="content")],
        vector_store=FakeVectorStore(error=RuntimeError("dense failed")),
        planner=CapturingPlanner(source_ids=None),
        lexical_error=ValueError("lexical failed"),
    )

    with pytest.raises(RuntimeError, match="retrieval branches failed"):
        service.search(
            "query",
            enriched_query=_enriched("query", "query"),
            retrieval_policy=RetrievalPolicy(enabled=True),
        )


def test_disabled_policy_retains_legacy_lexical_first_merge():
    lexical_first = Document(id_="lexical-first", text="lexical")
    shared = Document(id_="shared", text="both")
    vector_only = Document(id_="vector-only", text="dense")
    service, _planner, _retriever, store, _embedding = _pipeline_service(
        sources=[source("source-a", path="/a.md")],
        chunks_by_source={"source-a": ["lexical-first", "shared", "vector-only"]},
        docs=[lexical_first, shared, vector_only],
        vector_store=FakeVectorStore(
            {("lexical-first", "shared", "vector-only"): ["shared", "vector-only"]}
        ),
        planner=CapturingPlanner(source_ids=None),
        lexical_ids=["lexical-first", "shared"],
    )

    result = service.search(
        "query",
        enriched_query=_enriched("query", "ignored rewritten query"),
        retrieval_policy=RetrievalPolicy(enabled=False),
    )

    assert [document.doc_id for document in result] == [
        "lexical-first",
        "shared",
        "vector-only",
    ]
    assert [call["query"] for call in store.query_calls] == ["query"]


def test_malicious_reranker_id_is_filtered_after_reranking():
    allowed = Document(id_="allowed", text="authorized candidate")
    malicious = RetrievedDocument(id_="attacker-id", text="not a route candidate")
    reranker = FakeReranker([malicious, allowed])
    service, _planner, _retriever, _store, _embedding = _pipeline_service(
        sources=[source("source-a", path="/a.md")],
        chunks_by_source={"source-a": ["allowed"]},
        docs=[allowed],
        vector_store=FakeVectorStore({("allowed",): ["allowed"]}),
        planner=CapturingPlanner(source_ids=None),
        rerankers=[reranker],
    )

    result = service.search(
        "original query",
        enriched_query=_enriched("original query", "standalone query"),
        retrieval_policy=RetrievalPolicy(enabled=True),
    )

    assert [document.doc_id for document in result] == ["allowed"]
    assert reranker.calls == [("standalone query", ("allowed",))]


def test_trace_records_fusion_rerank_score_and_model_revision(tmp_path):
    class Backend:
        def compute_score(self, pairs, **kwargs):
            assert pairs == [("standalone query", "authorized candidate")]
            return [0.42]

    allowed = Document(id_="allowed", text="authorized candidate")
    reranker = BgeM3Reranking(tmp_path, backend=Backend(), revision="fixture-revision")
    service, _planner, _retriever, _store, _embedding = _pipeline_service(
        sources=[source("source-a", path="/a.md")],
        chunks_by_source={"source-a": ["allowed"]},
        docs=[allowed],
        vector_store=FakeVectorStore({("allowed",): ["allowed"]}),
        planner=CapturingPlanner(source_ids=None),
        rerankers=[reranker],
    )
    trace = RetrievalTrace()

    result = service.search(
        "original query",
        enriched_query=_enriched("original query", "standalone query"),
        retrieval_policy=RetrievalPolicy(enabled=True),
        trace=trace,
    )

    snapshot = trace.to_dict()
    rerank_event = next(
        event for event in snapshot["events"] if event["stage"] == "reranker"
    )
    fusion_event = next(
        event for event in snapshot["events"] if event["stage"] == "fusion"
    )
    assert [document.doc_id for document in result] == ["allowed"]
    assert fusion_event["ids"] == ["allowed"]
    assert rerank_event["model_provenance"]["revision"] == "fixture-revision"
    assert rerank_event["candidates"] == [
        {"id": "allowed", "score": 0.42, "score_available": True}
    ]
