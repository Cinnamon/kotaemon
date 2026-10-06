"""Structured, request-local retrieval trace contract tests."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace
from kotaemon.storages.docstores.base import BaseDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore


class FakeEmbedding(BaseEmbeddings):
    def run(self, text, *args, **kwargs):
        return [DocumentWithEmbedding(embedding=[0.1, 0.2])]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, results, error=None):
        self.results = results
        self.error = error
        self.calls = []

    def add(self, embeddings, metadatas=None, ids=None):
        return ids or []

    def delete(self, ids, **kwargs):
        pass

    def query(self, embedding, top_k=1, ids=None, **kwargs):
        self.calls.append(ids)
        if self.error is not None:
            raise self.error
        return self.results.get(tuple(ids) if ids is not None else None, ([], [], []))

    def drop(self):
        pass


class FakeDocumentStore(BaseDocumentStore):
    supports_lexical_search = True

    def __init__(self, docs, lexical=None, reverse_get=False, error=None):
        self.docs = {doc.doc_id: doc for doc in docs}
        self.lexical = list(lexical or [])
        self.reverse_get = reverse_get
        self.error = error
        self.calls = []

    def add(self, docs, ids=None, **kwargs):
        pass

    def get(self, ids):
        ids = [ids] if isinstance(ids, str) else list(ids)
        if self.reverse_get:
            ids.reverse()
        return [self.docs[doc_id] for doc_id in ids if doc_id in self.docs]

    def get_all(self):
        return list(self.docs.values())

    def count(self):
        return len(self.docs)

    def query(self, query, top_k=10, doc_ids=None):
        self.calls.append(doc_ids)
        if self.error is not None:
            raise self.error
        return [doc for doc in self.lexical if doc_ids is None or doc.doc_id in doc_ids]

    def delete(self, ids):
        pass

    def drop(self):
        pass


def make_doc(doc_id, text=None, **metadata):
    return Document(id_=doc_id, text=text or doc_id, metadata=metadata)


def test_trace_update_and_snapshot_are_json_safe_detached_and_redacted():
    trace = RetrievalTrace()
    source_fields = {
        "original_query": "张三在哪里实习？",
        "explicit_filters": {"path": "/team/rag"},
    }
    trace.update(source_fields)
    trace.update(plan={"semantic_query": "张三 实习"}, scope_ids=["chunk-1"])
    trace.record(
        "evidence",
        context_chunk_ids=["chunk-1"],
        evidence_html="UNIQUE_EVIDENCE_HTML",
        text="UNIQUE_SOURCE_TEXT",
        image_origin="UNIQUE_IMAGE_PAYLOAD",
        file_path="/Users/private/upload.pdf",
    )
    trace.record(
        "unsafe_values",
        answer="UNIQUE_GENERATED_ANSWER",
        metadata={"private_field": "UNIQUE_RAW_METADATA"},
        image_data="UNIQUE_IMAGE_DATA",
        nonfinite_score=float("nan"),
        backend_error=RuntimeError("UNIQUE_BACKEND_ERROR"),
        unsupported=object(),
    )
    source_fields["explicit_filters"]["path"] = "/mutated"

    snapshot = trace.to_dict()
    encoded = trace.to_json()

    assert json.loads(encoded) == snapshot
    assert snapshot["original_query"] == "张三在哪里实习？"
    assert snapshot["explicit_filters"]["path"] == "/team/rag"
    assert "UNIQUE_EVIDENCE_HTML" not in encoded
    assert "UNIQUE_SOURCE_TEXT" not in encoded
    assert "UNIQUE_IMAGE_PAYLOAD" not in encoded
    assert "UNIQUE_GENERATED_ANSWER" not in encoded
    assert "UNIQUE_RAW_METADATA" not in encoded
    assert "UNIQUE_IMAGE_DATA" not in encoded
    assert "UNIQUE_BACKEND_ERROR" not in encoded
    assert "/Users/private/upload.pdf" not in encoded
    assert snapshot["events"][-1] == {
        "stage": "unsafe_values",
        "nonfinite_score": None,
        "backend_error": {"type": "RuntimeError"},
    }
    snapshot["events"].clear()
    assert trace.to_dict()["events"]


def test_trace_content_is_included_only_when_explicitly_enabled():
    redacted = RetrievalTrace()
    included = RetrievalTrace(include_content=True)
    for trace in (redacted, included):
        trace.record("source", id="chunk-1", text="OPT_IN_SOURCE_TEXT")

    assert "OPT_IN_SOURCE_TEXT" not in redacted.to_json()
    assert "OPT_IN_SOURCE_TEXT" in included.to_json()


def test_extra_table_trace_projection_is_isolated_from_main_summary():
    trace = RetrievalTrace()
    main = trace.scoped(query_kind="main")
    extra_table = trace.scoped(query_kind="extra_table")

    main.record("merged", ids=["main-merged"])
    main.record("reranker", name="main-reranker", candidates=["main-ranked"])
    main.record("diversity", selected_ids=["main-diverse"])
    main.record("final", ids=["main-final"])

    extra_table.record("merged", ids=["table-merged"])
    extra_table.record("reranker", name="table-reranker", candidates=["table-ranked"])
    extra_table.record("diversity", selected_ids=["table-diverse"])
    extra_table.record("final", ids=["table-final"])
    extra_table.update(auxiliary_status={"complete": True})

    snapshot = trace.to_dict()
    auxiliary = snapshot["auxiliary_retrievals"]["extra_table"]

    assert snapshot["merged_ids"] == ["main-merged"]
    assert snapshot["rerankers"] == [
        {
            "query_kind": "main",
            "name": "main-reranker",
            "candidates": ["main-ranked"],
        }
    ]
    assert snapshot["diversity_selected_ids"] == ["main-diverse"]
    assert snapshot["final_chunk_ids"] == ["main-final"]
    assert "auxiliary_status" not in snapshot

    assert auxiliary["merged_ids"] == ["table-merged"]
    assert auxiliary["rerankers"][0]["name"] == "table-reranker"
    assert auxiliary["diversity_selected_ids"] == ["table-diverse"]
    assert auxiliary["final_chunk_ids"] == ["table-final"]
    assert auxiliary["auxiliary_status"] == {"complete": True}
    assert [event["stage"] for event in snapshot["events"]] == [
        "merged",
        "reranker",
        "diversity",
        "final",
        "merged",
        "reranker",
        "diversity",
        "final",
    ]
    assert [event["query_kind"] for event in snapshot["events"]] == [
        "main",
        "main",
        "main",
        "main",
        "extra_table",
        "extra_table",
        "extra_table",
        "extra_table",
    ]
    assert json.loads(trace.to_json()) == snapshot


def test_concurrent_traces_keep_independent_ordered_event_histories():
    traces = [RetrievalTrace() for _ in range(2)]

    def record_many(index):
        for item in range(30):
            traces[index].record(
                "candidate", query_id=index, candidate_id=f"{index}-{item}"
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(record_many, range(2)))

    first = traces[0].to_dict()["events"]
    second = traces[1].to_dict()["events"]
    assert len(first) == len(second) == 30
    assert [event["candidate_id"] for event in first] == [f"0-{i}" for i in range(30)]
    assert [event["candidate_id"] for event in second] == [f"1-{i}" for i in range(30)]


def test_vector_trace_records_real_id_aligned_scores_rerank_order_and_final_ids():
    docs = [make_doc("first", "first source"), make_doc("second", "second source")]
    vector = FakeVectorStore({None: ([], [0.91, 0.82], ["first", "second"])})
    store = FakeDocumentStore(docs, reverse_get=True)

    class ReverseReranker:
        def run(self, documents, query):
            return list(reversed(documents))

    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        rerankers=[ReverseReranker()],
        top_k=2,
    )
    trace = RetrievalTrace()

    result = retriever.run(text="question", trace=trace)
    snapshot = trace.to_dict()
    stages = [event["stage"] for event in snapshot["events"]]
    attempt = next(
        event for event in snapshot["events"] if event["stage"] == "recall_attempt"
    )

    assert [document.doc_id for document in result] == ["second", "first"]
    assert [
        (candidate["id"], candidate["score"])
        for candidate in attempt["vector_candidates"]
    ] == [
        ("first", 0.91),
        ("second", 0.82),
    ]
    assert attempt["lexical_status"] == "not_used"
    assert snapshot["rerankers"][0]["candidates"][0]["id"] == "second"
    assert snapshot["final_chunk_ids"] == ["second", "first"]
    assert (
        stages.index("recall_attempt")
        < stages.index("merged")
        < stages.index("reranker")
    )
    assert stages.index("diversity") < stages.index("final")
    json.dumps(snapshot)


def test_trace_and_disabled_retrieval_accept_scoreless_plain_document_reranker_output():
    docs = [make_doc("first", "first source"), make_doc("second", "second source")]

    class PlainDocumentReranker:
        def run(self, documents, query):
            return [
                Document(
                    id_=document.doc_id,
                    text=document.text,
                    metadata=document.metadata,
                )
                for document in reversed(documents)
            ]

    retriever = VectorRetrieval(
        vector_store=FakeVectorStore({None: ([], [0.91, 0.82], ["first", "second"])}),
        doc_store=FakeDocumentStore(docs),
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        rerankers=[PlainDocumentReranker()],
        top_k=2,
    )
    trace = RetrievalTrace()

    traced_result = retriever.run(text="question", trace=trace)
    disabled_result = retriever.run(text="question")
    candidates = trace.to_dict()["rerankers"][0]["candidates"]

    assert (
        [document.doc_id for document in traced_result]
        == [document.doc_id for document in disabled_result]
        == ["second", "first"]
    )
    assert candidates == [
        {"id": "second", "score": None, "score_available": False},
        {"id": "first", "score": None, "score_available": False},
    ]


def test_zero_scoped_hits_preserve_both_recall_attempts_and_fallback_reason():
    legacy = make_doc("legacy", "legacy content")
    vector = FakeVectorStore({None: ([], [0.77], ["legacy"])})
    store = FakeDocumentStore([legacy])
    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
    )
    trace = RetrievalTrace()

    result = retriever.run(
        text="question", scope=["planned"], fallback_scope=None, trace=trace
    )

    attempts = trace.to_dict()["attempts"]
    assert [document.doc_id for document in result] == ["legacy"]
    assert len(attempts) == 2
    assert attempts[0]["scope_ids"] == ["planned"]
    assert attempts[0]["vector_candidates"] == []
    assert attempts[1]["scope_ids"] is None
    assert trace.to_dict()["scope_fallback_reason"] == "zero_scoped_hits"


def test_hybrid_trace_records_unavailable_lexical_scores_and_disabled_parity():
    vector_doc = make_doc("vector-id", "vector result")
    lexical_doc = make_doc("lexical-id", "lexical result")
    vector = FakeVectorStore({None: ([], [0.72], ["vector-id"])})
    store = FakeDocumentStore([vector_doc, lexical_doc], lexical=[lexical_doc])
    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="hybrid",
    )
    trace = RetrievalTrace()

    traced_result = retriever.run(text="question", trace=trace)
    plain_result = retriever.run(text="question")
    snapshot = trace.to_dict()
    attempt = snapshot["attempts"][0]

    assert [doc.doc_id for doc in traced_result] == [doc.doc_id for doc in plain_result]
    assert attempt["lexical_status"] == "available"
    assert attempt["lexical_candidates"] == [
        {"id": "lexical-id", "score": None, "score_available": False}
    ]
    assert {item["id"] for item in attempt["vector_candidates"]} == {"vector-id"}
    assert attempt["vector_candidates"][0]["score"] == 0.72
    assert "source content" not in trace.to_json()


def test_trace_reports_lexical_unavailable_empty_and_error_separately():
    vector_doc = make_doc("vector-id", "vector result")
    vector = FakeVectorStore({None: ([], [0.72], ["vector-id"])})

    unavailable_store = FakeDocumentStore([vector_doc])
    unavailable_store.supports_lexical_search = False
    unavailable_trace = RetrievalTrace()
    VectorRetrieval(
        vector_store=vector,
        doc_store=unavailable_store,
        embedding=FakeEmbedding(),
        retrieval_mode="hybrid",
    ).run(text="question", trace=unavailable_trace)

    empty_trace = RetrievalTrace()
    VectorRetrieval(
        vector_store=vector,
        doc_store=FakeDocumentStore([vector_doc]),
        embedding=FakeEmbedding(),
        retrieval_mode="hybrid",
    ).run(text="question", trace=empty_trace)

    error_trace = RetrievalTrace()
    VectorRetrieval(
        vector_store=vector,
        doc_store=FakeDocumentStore(
            [vector_doc], error=RuntimeError("secret source /Users/private/chunk")
        ),
        embedding=FakeEmbedding(),
        retrieval_mode="hybrid",
    ).run(text="question", trace=error_trace)

    unavailable_attempt = unavailable_trace.to_dict()["attempts"][0]
    empty_attempt = empty_trace.to_dict()["attempts"][0]
    error_attempt = error_trace.to_dict()["attempts"][0]
    assert unavailable_attempt["lexical_status"] == "unavailable"
    assert empty_attempt["lexical_status"] == "empty"
    assert error_attempt["lexical_status"] == "error"
    assert error_attempt["backend_errors"] == {"lexical": {"type": "RuntimeError"}}
    assert "/Users/private/chunk" not in error_trace.to_json()


def test_vector_backend_error_is_traced_while_usable_lexical_results_survive():
    lexical_doc = make_doc("lexical-id", "lexical result")
    trace = RetrievalTrace()
    retriever = VectorRetrieval(
        vector_store=FakeVectorStore({}, error=RuntimeError("private path")),
        doc_store=FakeDocumentStore([lexical_doc], lexical=[lexical_doc]),
        embedding=FakeEmbedding(),
        retrieval_mode="hybrid",
    )

    result = retriever.run(text="question", trace=trace)
    attempt = trace.to_dict()["attempts"][0]

    assert [doc.doc_id for doc in result] == ["lexical-id"]
    assert attempt["vector_status"] == "error"
    assert attempt["backend_errors"] == {"vector": {"type": "RuntimeError"}}


def test_diversity_trace_explains_dropped_candidates_but_not_deferred_fill():
    documents = [
        make_doc("first", "identical sentence", document_id="source-a", parent_id="p"),
        make_doc("duplicate-text", "identical   sentence"),
        make_doc(
            "group-cap",
            "A separate candidate under the same parent.",
            document_id="source-a",
            parent_id="p",
        ),
        make_doc(
            "alternate",
            "A candidate from another parent.",
            document_id="source-a",
            parent_id="q",
        ),
    ]
    vector = FakeVectorStore(
        {None: ([], [0.9, 0.8, 0.7, 0.6], [doc.doc_id for doc in documents])}
    )
    trace = RetrievalTrace()
    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=FakeDocumentStore(documents),
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        top_k=2,
        max_per_parent_or_section=1,
    )

    result = retriever.run(text="question", trace=trace)
    diversity = trace.to_dict()["diversity"]

    assert [doc.doc_id for doc in result] == ["first", "alternate"]
    assert {item["id"]: item["reason"] for item in diversity["excluded"]} == {
        "duplicate-text": "duplicate_text",
        "group-cap": "group_cap",
    }
    assert "group-cap" not in [
        item["id"] for item in diversity["excluded"] if item.get("selected")
    ]


def test_group_cap_candidate_used_to_fill_top_k_is_not_traced_as_excluded():
    documents = [
        make_doc(
            "first", "first unique passage", document_id="source-a", parent_id="p"
        ),
        make_doc(
            "deferred", "second unique passage", document_id="source-a", parent_id="p"
        ),
    ]
    trace = RetrievalTrace()
    retriever = VectorRetrieval(
        vector_store=FakeVectorStore({None: ([], [0.9, 0.8], ["first", "deferred"])}),
        doc_store=FakeDocumentStore(documents),
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        top_k=2,
        max_per_parent_or_section=1,
    )

    result = retriever.run(text="question", trace=trace)

    assert [document.doc_id for document in result] == ["first", "deferred"]
    assert trace.to_dict()["diversity"] == {
        "excluded": [],
        "selected_ids": ["first", "deferred"],
    }


def test_throwing_trace_sink_does_not_interrupt_vector_retrieval():
    doc = make_doc("usable", "usable source")
    vector = FakeVectorStore({None: ([], [0.8], ["usable"])})
    store = FakeDocumentStore([doc])
    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
    )

    class BrokenTrace:
        def update(self, *args, **kwargs):
            raise RuntimeError("trace unavailable")

        def record(self, *args, **kwargs):
            raise RuntimeError("trace unavailable")

    assert [
        doc.doc_id for doc in retriever.run(text="question", trace=BrokenTrace())
    ] == ["usable"]


def test_plain_dict_trace_adapter_still_receives_legacy_scope_and_status_keys():
    doc = make_doc("legacy", "legacy source")
    vector = FakeVectorStore({None: ([], [0.8], ["legacy"])})
    store = FakeDocumentStore([doc])
    retriever = VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
    )
    trace = {}

    retriever.run(text="question", trace=trace)

    assert trace["scope_status"] == "global"
    assert trace["scope_ids"] is None
    assert trace["lexical_status"] == "not_used"
