"""Contract tests for scoped execution through the existing vector retriever."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Union

import pytest
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
    VectorStoreQuery,
)

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.rankings import BaseReranking
from kotaemon.storages.docstores.base import BaseDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore, LlamaIndexVectorStore


class FakeEmbedding(BaseEmbeddings):
    calls: int = 0

    def run(self, text, *args, **kwargs):
        self.calls += 1
        return [DocumentWithEmbedding(embedding=[0.1, 0.2])]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, responses=None, *, error=None):
        self.responses = responses or {}
        self.error = error
        self.calls = []

    def add(self, embeddings, metadatas=None, ids=None):
        return ids or []

    def delete(self, ids, **kwargs):
        pass

    def query(self, embedding, top_k=1, ids=None, **kwargs):
        self.calls.append(
            {"embedding": embedding, "top_k": top_k, "ids": ids, **kwargs}
        )
        if self.error:
            raise self.error
        result = self.responses.get(
            tuple(ids) if ids is not None else None, ([], [], [])
        )
        return result

    def drop(self):
        pass


class FakeDocumentStore(BaseDocumentStore):
    supports_lexical_search = True

    def __init__(
        self,
        docs=None,
        *,
        lexical=None,
        ignore_scope=False,
        get_order=None,
        error=None,
    ):
        self.docs = {doc.doc_id: doc for doc in (docs or [])}
        self.lexical = lexical or []
        self.ignore_scope = ignore_scope
        self.get_order = get_order
        self.error = error
        self.query_calls = []
        self.get_calls = []

    def add(self, docs, ids=None, **kwargs):
        for doc in docs if isinstance(docs, list) else [docs]:
            self.docs[doc.doc_id] = doc

    def get(self, ids: Union[list[str], str]):
        if not isinstance(ids, list):
            ids = [ids]
        self.get_calls.append(list(ids))
        ordered = list(ids)
        if self.get_order == "reverse":
            ordered.reverse()
        return [self.docs[doc_id] for doc_id in ordered if doc_id in self.docs]

    def get_all(self):
        return list(self.docs.values())

    def count(self):
        return len(self.docs)

    def query(self, query, top_k=10, doc_ids=None):
        self.query_calls.append({"query": query, "top_k": top_k, "doc_ids": doc_ids})
        if self.error:
            raise self.error
        docs = self.lexical
        if doc_ids is not None and not self.ignore_scope:
            docs = [doc for doc in docs if doc.doc_id in doc_ids]
        return docs[:top_k]

    def delete(self, ids):
        pass

    def drop(self):
        self.docs.clear()


class CapturingReranker(BaseReranking):
    output: list[Document] | None = None

    def __init__(self, output=None):
        super().__init__(output=output)
        object.__setattr__(self, "_inputs", [])

    @property
    def inputs(self):
        return self._inputs

    def run(self, documents, query):
        self._inputs.append([doc.doc_id for doc in documents])
        return self.output if self.output is not None else list(reversed(documents))


def make_doc(doc_id, text=None, **metadata):
    return Document(id_=doc_id, text=text or doc_id, metadata=metadata)


def make_retriever(vector, store, embedding=None, **kwargs):
    return VectorRetrieval(
        vector_store=vector,
        doc_store=store,
        embedding=embedding or FakeEmbedding(),
        **kwargs,
    )


@pytest.mark.parametrize("mode", ["vector", "hybrid"])
def test_vector_branches_use_ids_and_hybrid_lexical_uses_same_doc_ids(mode):
    docs = [make_doc("chunk-1"), make_doc("chunk-2")]
    vector = FakeVectorStore(
        {("chunk-1", "chunk-2"): ([], [0.9, 0.8], ["chunk-1", "chunk-2"])}
    )
    store = FakeDocumentStore(docs, lexical=docs)

    result = make_retriever(vector, store, retrieval_mode=mode)(
        text="question", scope=["chunk-1", "chunk-2"]
    )

    assert [doc.doc_id for doc in result] == ["chunk-1", "chunk-2"]
    assert vector.calls[0]["ids"] == ["chunk-1", "chunk-2"]
    assert "doc_ids" not in vector.calls[0]
    if mode == "hybrid":
        assert store.query_calls[0]["doc_ids"] == ["chunk-1", "chunk-2"]


@pytest.mark.parametrize("mode", ["vector", "text", "hybrid"])
def test_explicit_empty_scope_returns_before_embedding_or_store_calls(mode):
    vector = FakeVectorStore()
    store = FakeDocumentStore()
    embedding = FakeEmbedding()

    result = make_retriever(vector, store, embedding, retrieval_mode=mode)(
        text="question", scope=[]
    )

    assert result == []
    assert embedding.calls == 0
    assert vector.calls == []
    assert store.query_calls == []
    assert store.get_calls == []


@pytest.mark.parametrize("mode", ["vector", "text", "hybrid"])
def test_none_scope_runs_global_path_in_each_retrieval_mode(mode):
    document = make_doc("legacy")
    vector = FakeVectorStore({None: ([], [0.9], ["legacy"])})
    store = FakeDocumentStore([document], lexical=[document])
    embedding = FakeEmbedding()

    result = make_retriever(vector, store, embedding, retrieval_mode=mode)(
        text="question", scope=None
    )

    assert [doc.doc_id for doc in result] == ["legacy"]
    if mode == "text":
        assert embedding.calls == 0
        assert vector.calls == []
    else:
        assert embedding.calls == 1
        assert vector.calls[0]["ids"] is None
        assert "doc_ids" not in vector.calls[0]
    if mode == "vector":
        assert store.query_calls == []
    else:
        assert store.query_calls[0]["doc_ids"] is None


def test_scope_postfilters_ignoring_backends_and_reranker_without_losing_candidates():
    allowed = make_doc("allowed")
    outside = make_doc("outside")
    vector = FakeVectorStore({("allowed",): ([], [0.8, 0.99], ["allowed", "outside"])})
    store = FakeDocumentStore(
        [allowed, outside], lexical=[outside, allowed], ignore_scope=True
    )
    reranker = CapturingReranker(output=[outside, allowed])

    result = make_retriever(
        vector, store, retrieval_mode="hybrid", rerankers=[reranker]
    )(text="question", scope=["allowed"], top_k=1)

    assert [doc.doc_id for doc in result] == ["allowed"]
    assert reranker.inputs == [["allowed"]]
    assert vector.calls[0]["ids"] == ["allowed"]
    assert vector.calls[0]["top_k"] >= 10
    assert store.query_calls[0]["top_k"] >= 10
    assert vector.calls[0]["top_k"] == 10


def test_configured_rerankers_run_in_order():
    first = make_doc("first")
    second = make_doc("second")
    vector = FakeVectorStore({None: ([], [0.9, 0.8], ["first", "second"])})
    store = FakeDocumentStore([first, second])
    reranker_one = CapturingReranker(output=[second, first])
    reranker_two = CapturingReranker(output=[first, second])

    result = make_retriever(
        vector,
        store,
        retrieval_mode="vector",
        rerankers=[reranker_one, reranker_two],
    )(text="question")

    assert reranker_one.inputs == [["first", "second"]]
    assert reranker_two.inputs == [["second", "first"]]
    assert [doc.doc_id for doc in result] == ["first", "second"]


def test_vector_scores_stay_attached_to_ids_when_docstore_get_reorders():
    docs = [make_doc("first"), make_doc("second")]
    vector = FakeVectorStore({None: ([], [0.9, 0.2], ["first", "second"])})
    store = FakeDocumentStore(docs, get_order="reverse")

    result = make_retriever(vector, store, retrieval_mode="vector")(text="question")

    assert [(doc.doc_id, doc.score) for doc in result] == [
        ("first", 0.9),
        ("second", 0.2),
    ]


def test_hybrid_merge_deduplicates_by_id_in_lexical_then_vector_order():
    lexical_first = make_doc("lexical-first")
    shared = make_doc("shared")
    vector_only = make_doc("vector-only")
    vector = FakeVectorStore({None: ([], [0.7, 0.6], ["shared", "vector-only"])})
    store = FakeDocumentStore(
        [lexical_first, shared, vector_only], lexical=[lexical_first, shared]
    )

    result = make_retriever(vector, store, retrieval_mode="hybrid")(text="question")

    assert [doc.doc_id for doc in result] == [
        "lexical-first",
        "shared",
        "vector-only",
    ]
    assert len({doc.doc_id for doc in result}) == len(result)


def test_global_lexical_search_receives_none_and_empty_result_is_recorded():
    vector = FakeVectorStore({None: ([], [0.9], ["legacy"])})
    store = FakeDocumentStore([make_doc("legacy")], lexical=[])
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="hybrid")(
        text="question", trace=trace
    )

    assert [doc.doc_id for doc in result] == ["legacy"]
    assert vector.calls[0]["ids"] is None
    assert store.query_calls[0]["doc_ids"] is None
    assert trace["lexical_status"] == "empty"
    assert trace["lexical_result_count"] == 0


def test_lexical_unavailable_backend_is_not_queried_or_described_as_bm25():
    class VectorOnlyDocumentStore(FakeDocumentStore):
        supports_lexical_search = False

    vector = FakeVectorStore({None: ([], [0.9], ["legacy"])})
    store = VectorOnlyDocumentStore([make_doc("legacy")])
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="hybrid")(
        text="question", trace=trace
    )

    assert [doc.doc_id for doc in result] == ["legacy"]
    assert store.query_calls == []
    assert trace["lexical_status"] == "unavailable"


def test_zero_hit_retry_uses_only_the_callers_visible_chunk_ids():
    planned = make_doc("planned")
    allowed = make_doc("allowed")
    forbidden = make_doc("forbidden")
    vector = FakeVectorStore(
        {
            ("planned",): ([], [], []),
            ("planned", "allowed"): (
                [],
                [0.99, 0.8, 0.7],
                ["forbidden", "allowed", "planned"],
            ),
        }
    )
    store = FakeDocumentStore([planned, allowed, forbidden])
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question",
        scope=["planned"],
        fallback_scope=["planned", "allowed"],
        trace=trace,
    )

    assert [doc.doc_id for doc in result] == ["allowed", "planned"]
    assert [call["ids"] for call in vector.calls] == [
        ["planned"],
        ["planned", "allowed"],
    ]
    assert trace["scope_fallback"] is True
    assert trace["scope_fallback_reason"] == "zero_scoped_hits"
    assert trace["candidate_k"] == 50


@pytest.mark.parametrize("mode", ["vector", "text", "hybrid"])
def test_zero_hit_retry_without_a_separate_allowlist_runs_one_global_retry(mode):
    global_doc = make_doc("global-hit")
    vector = FakeVectorStore(
        {
            ("planned",): ([], [], []),
            None: ([], [0.8], ["global-hit"]),
        }
    )
    store = FakeDocumentStore([global_doc], lexical=[global_doc])
    trace = {}

    result = make_retriever(vector, store, retrieval_mode=mode)(
        text="question", scope=["planned"], trace=trace
    )

    assert [doc.doc_id for doc in result] == ["global-hit"]
    assert trace["scope_fallback"] is True
    assert trace["scope_fallback_reason"] == "zero_scoped_hits"
    assert trace["scope_status"] == "fallback"
    assert trace["scope_ids"] is None
    if mode == "text":
        assert vector.calls == []
    else:
        assert [call["ids"] for call in vector.calls] == [["planned"], None]
    if mode == "vector":
        assert store.query_calls == []
    else:
        assert [call["doc_ids"] for call in store.query_calls] == [
            ["planned"],
            None,
        ]


def test_empty_caller_visibility_never_retries_as_global():
    vector = FakeVectorStore({("planned",): ([], [], [])})
    store = FakeDocumentStore()
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", scope=["planned"], fallback_scope=[], trace=trace
    )

    assert result == []
    assert vector.calls == []
    assert trace["scope_fallback"] is False


def test_zero_hit_retry_keeps_explicit_metadata_filters():
    planned_rejected = make_doc("planned-rejected", file_id="source-b")
    global_allowed = make_doc("global-allowed", file_id="source-a")
    global_rejected = make_doc("global-rejected", file_id="source-b")
    vector = FakeVectorStore(
        {
            ("planned",): ([], [0.9], ["planned-rejected"]),
            None: (
                [],
                [0.8, 0.7],
                ["global-allowed", "global-rejected"],
            ),
        }
    )
    store = FakeDocumentStore([planned_rejected, global_allowed, global_rejected])
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="file_id",
                value=["source-a"],
                operator=FilterOperator.IN,
            )
        ]
    )
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", scope=["planned"], filters=filters, trace=trace
    )

    assert [doc.doc_id for doc in result] == ["global-allowed"]
    assert trace["scope_fallback"] is True
    assert [call["ids"] for call in vector.calls] == [["planned"], None]
    assert all(call["filters"] is filters for call in vector.calls)


def test_metadata_filters_are_enforced_when_both_recall_backends_ignore_them():
    allowed = make_doc("allowed", file_id="source-a")
    rejected = make_doc("rejected", file_id="source-b")
    vector = FakeVectorStore({None: ([], [0.9, 0.8], ["allowed", "rejected"])})
    store = FakeDocumentStore([allowed, rejected], lexical=[rejected, allowed])
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="file_id",
                value=["source-a"],
                operator=FilterOperator.IN,
            )
        ],
        condition=FilterCondition.OR,
    )

    result = make_retriever(vector, store, retrieval_mode="hybrid")(
        text="question", filters=filters
    )

    assert [doc.doc_id for doc in result] == ["allowed"]


@pytest.mark.parametrize(
    ("condition", "expected_ids"),
    [
        (FilterCondition.AND, ["both"]),
        (FilterCondition.OR, ["both", "file-only", "type-only"]),
    ],
)
def test_metadata_filter_group_condition_is_enforced(condition, expected_ids):
    docs = [
        make_doc("both", file_id="source-a", source_type="wiki"),
        make_doc("file-only", file_id="source-a", source_type="pdf"),
        make_doc("type-only", file_id="source-b", source_type="wiki"),
        make_doc("neither", file_id="source-b", source_type="pdf"),
    ]
    vector = FakeVectorStore(
        {None: ([], [0.9, 0.8, 0.7, 0.6], [doc.doc_id for doc in docs])}
    )
    store = FakeDocumentStore(docs)
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="file_id", value="source-a"),
            MetadataFilter(key="source_type", value="wiki"),
        ],
        condition=condition,
    )

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", filters=filters
    )

    assert [doc.doc_id for doc in result] == expected_ids


def test_metadata_filter_is_reapplied_after_reranker_output():
    allowed = make_doc("allowed", file_id="source-a")
    rejected = make_doc("rejected", file_id="source-b")
    vector = FakeVectorStore({None: ([], [0.9], ["allowed"])})
    store = FakeDocumentStore([allowed, rejected])
    reranker = CapturingReranker(output=[rejected, allowed])
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="file_id",
                value=["source-a"],
                operator=FilterOperator.IN,
            )
        ],
        condition=FilterCondition.OR,
    )

    result = make_retriever(
        vector, store, retrieval_mode="vector", rerankers=[reranker]
    )(text="question", filters=filters)

    assert [doc.doc_id for doc in result] == ["allowed"]


def test_where_and_or_eq_in_are_enforced_after_vector_retrieval():
    report_page = make_doc("report-page", file_name="report.pdf", page_label="1")
    notes_page = make_doc("notes-page", file_name="notes.pdf", page_label="2")
    rejected_page = make_doc("rejected-page", file_name="report.pdf", page_label="3")
    vector = FakeVectorStore(
        {
            None: (
                [],
                [0.9, 0.8, 0.7],
                ["report-page", "notes-page", "rejected-page"],
            )
        }
    )
    store = FakeDocumentStore([report_page, notes_page, rejected_page])
    where = {
        "$or": [
            {
                "$and": [
                    {"file_name": {"$eq": "report.pdf"}},
                    {"page_label": {"$in": ["1"]}},
                ]
            },
            {
                "$and": [
                    {"file_name": {"$eq": "notes.pdf"}},
                    {"page_label": {"$eq": "2"}},
                ]
            },
        ]
    }

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", where=where
    )

    assert [doc.doc_id for doc in result] == ["report-page", "notes-page"]


@pytest.mark.parametrize(
    "constraint",
    [
        {"file_id": {"$ne": "source-a"}},
        {"$not": [{"file_id": {"$eq": "source-a"}}]},
    ],
)
def test_unsupported_where_operations_fail_closed_before_retrieval(constraint):
    vector = FakeVectorStore()
    store = FakeDocumentStore()
    embedding = FakeEmbedding()

    with pytest.raises(ValueError, match="Unsupported metadata filter"):
        make_retriever(vector, store, embedding, retrieval_mode="vector")(
            text="question", where=constraint
        )

    assert vector.calls == []
    assert embedding.calls == 0


def test_unsupported_metadata_filter_operator_fails_closed():
    vector = FakeVectorStore()
    store = FakeDocumentStore()
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="file_id", value="source-a", operator=FilterOperator.NE)
        ]
    )

    with pytest.raises(ValueError, match="Unsupported metadata filter"):
        make_retriever(vector, store, retrieval_mode="vector")(
            text="question", filters=filters
        )

    assert vector.calls == []


def test_lexical_status_is_empty_when_all_lexical_hits_fail_metadata_filter():
    allowed = make_doc("allowed", file_id="source-a")
    rejected = make_doc("rejected", file_id="source-b")
    vector = FakeVectorStore({None: ([], [0.9], ["allowed"])})
    store = FakeDocumentStore([allowed, rejected], lexical=[rejected])
    trace = {}
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="file_id",
                value=["source-a"],
                operator=FilterOperator.IN,
            )
        ],
        condition=FilterCondition.OR,
    )

    result = make_retriever(vector, store, retrieval_mode="hybrid")(
        text="question", filters=filters, trace=trace
    )

    assert [doc.doc_id for doc in result] == ["allowed"]
    assert trace["lexical_status"] == "empty"
    assert trace["lexical_result_count"] == 0


def test_out_of_scope_thumbnail_link_is_not_fetched_or_returned():
    text = make_doc(
        "text-chunk",
        file_id="source-a",
        thumbnail_doc_id="forged-thumbnail",
    )
    thumbnail = make_doc(
        "forged-thumbnail",
        type="thumbnail",
        file_id="source-b",
        image_origin="private-image-data",
    )
    vector = FakeVectorStore({("text-chunk",): ([], [0.9], ["text-chunk"])})
    store = FakeDocumentStore([text, thumbnail])

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", scope=["text-chunk"]
    )

    assert [doc.doc_id for doc in result] == ["text-chunk"]
    assert all("forged-thumbnail" not in call for call in store.get_calls)
    assert all(
        doc.metadata.get("image_origin") != "private-image-data" for doc in result
    )


def test_cross_source_thumbnail_link_is_not_returned():
    text = make_doc(
        "text-chunk",
        file_id="source-a",
        thumbnail_doc_id="thumbnail-chunk",
    )
    thumbnail = make_doc(
        "thumbnail-chunk",
        type="thumbnail",
        file_id="source-b",
        image_origin="other-source-image",
    )
    vector = FakeVectorStore(
        {("text-chunk", "thumbnail-chunk"): ([], [0.9], ["text-chunk"])}
    )
    store = FakeDocumentStore([text, thumbnail])

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", scope=["text-chunk", "thumbnail-chunk"]
    )

    assert [doc.doc_id for doc in result] == ["text-chunk"]
    assert all(
        doc.metadata.get("image_origin") != "other-source-image" for doc in result
    )


def test_thumbnail_link_inside_scope_and_same_source_replaces_text_result():
    text = make_doc(
        "text-chunk",
        text="the original evidence",
        file_id="source-a",
        thumbnail_doc_id="thumbnail-chunk",
    )
    thumbnail = make_doc(
        "thumbnail-chunk",
        type="thumbnail",
        file_id="source-a",
        image_origin="image-data",
    )
    vector = FakeVectorStore(
        {("text-chunk", "thumbnail-chunk"): ([], [0.9], ["text-chunk"])}
    )
    store = FakeDocumentStore([text, thumbnail])

    result = make_retriever(vector, store, retrieval_mode="vector")(
        text="question", scope=["text-chunk", "thumbnail-chunk"]
    )

    assert [doc.doc_id for doc in result] == ["text-chunk"]
    assert result[0].metadata["type"] == "image"
    assert result[0].metadata["image_origin"] == "image-data"
    assert result[0].content == "the original evidence"


def test_legacy_global_documents_without_canonical_metadata_remain_retrievable():
    legacy = make_doc("legacy", file_id="source-old", file_name="old.pdf")
    vector = FakeVectorStore({None: ([], [0.5], ["legacy"])})
    store = FakeDocumentStore([legacy])

    result = make_retriever(vector, store, retrieval_mode="vector")(text="question")

    assert len(result) == 1
    assert result[0].doc_id == "legacy"
    assert result[0].metadata == {"file_id": "source-old", "file_name": "old.pdf"}


def test_hybrid_worker_exception_is_recorded_and_usable_other_branch_is_returned():
    lexical = make_doc("lexical")
    vector = FakeVectorStore(error=RuntimeError("vector offline"))
    store = FakeDocumentStore([lexical], lexical=[lexical])
    trace = {}

    result = make_retriever(vector, store, retrieval_mode="hybrid")(
        text="question", trace=trace
    )

    assert [doc.doc_id for doc in result] == ["lexical"]
    assert "vector offline" in trace["branch_errors"]["vector"]


def test_hybrid_surfaces_worker_errors_when_neither_branch_has_usable_results():
    vector = FakeVectorStore(error=RuntimeError("vector offline"))
    store = FakeDocumentStore(error=RuntimeError("lexical offline"))

    with pytest.raises(RuntimeError, match="retrieval branches failed"):
        make_retriever(vector, store, retrieval_mode="hybrid")(text="question")


def test_llama_index_adapter_maps_ids_to_node_ids():
    class QueryClient:
        def query(self, *, query, **kwargs):
            self.received = query
            return SimpleNamespace(nodes=[], similarities=[], ids=[])

    class Adapter(LlamaIndexVectorStore):
        _li_class = QueryClient

        def drop(self):
            pass

    adapter = Adapter()
    adapter.query(embedding=[0.1], top_k=4, ids=["chunk-a", "chunk-b"])

    assert isinstance(adapter._client.received, VectorStoreQuery)
    assert adapter._client.received.node_ids == ["chunk-a", "chunk-b"]
