"""Behavior tests for the framework-independent Agent knowledge service."""

import pytest

from kotaemon.base import Document, RetrievedDocument
from kotaemon.indices.knowledge.planning.query_planner import KnowledgeSource
from kotaemon.indices.knowledge.planning.retrieval_plan import RetrievalPlan
from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService


def source(
    source_id,
    *,
    source_type="markdown",
    path=None,
    name=None,
    entity=None,
):
    return KnowledgeSource(
        source_id=source_id,
        source_type=source_type,
        virtual_path=path,
        document_name=name,
        entity=entity or {},
        source_name=name,
    )


class MemoryCatalog:
    def __init__(self, sources, chunks_by_source, source_by_chunk=None):
        self.sources = list(sources)
        self.chunks_by_source = chunks_by_source
        self.source_by_chunk = source_by_chunk or {
            chunk_id: source_id
            for source_id, chunk_ids in chunks_by_source.items()
            for chunk_id in chunk_ids
        }
        self.calls = []

    def list_sources(self, allowed_source_ids=None):
        self.calls.append(("list_sources", allowed_source_ids))
        sources = self.sources
        if allowed_source_ids is not None:
            allowed = set(allowed_source_ids)
            sources = [row for row in sources if row.source_id in allowed]
        return sources

    def chunk_ids(self, source_ids, *, relation_type="document"):
        self.calls.append(("chunk_ids", tuple(source_ids), relation_type))
        assert relation_type == "document"
        return {
            source_id: tuple(self.chunks_by_source.get(source_id, ()))
            for source_id in source_ids
            if self.chunks_by_source.get(source_id)
        }

    def source_ids_for_chunk_ids(self, chunk_ids, *, allowed_source_ids=None):
        self.calls.append(("source_ids_for_chunk_ids", tuple(chunk_ids)))
        allowed = None if allowed_source_ids is None else set(allowed_source_ids)
        return {
            chunk_id: source_id
            for chunk_id in chunk_ids
            if (source_id := self.source_by_chunk.get(chunk_id)) is not None
            and (allowed is None or source_id in allowed)
        }


class FixedPlanner:
    def __init__(self, source_ids=None, confidence=0.0):
        self.source_ids = source_ids
        self.confidence = confidence
        self.calls = []

    def plan(self, query, catalog, **kwargs):
        self.calls.append((query, catalog, kwargs))
        return RetrievalPlan(
            query=query,
            semantic_query=query,
            confidence=self.confidence,
            reason="fixture",
            source_ids=(None if self.source_ids is None else tuple(self.source_ids)),
        )


class FixedRetriever:
    def __init__(self, result=None):
        self.result = list(result or [])
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return list(self.result)


class MemoryDocstore:
    def __init__(self, docs):
        self.docs = list(docs)
        self.calls = []

    def get(self, ids):
        self.calls.append(ids)
        selected = set(ids if isinstance(ids, list) else [ids])
        # Deliberately return reverse order to verify ID-based mapping.
        return [doc for doc in reversed(self.docs) if doc.doc_id in selected]


def make_service(
    *,
    sources=None,
    chunks_by_source=None,
    source_by_chunk=None,
    planner=None,
    retrieved=None,
    docs=None,
):
    catalog = MemoryCatalog(
        sources or [], chunks_by_source or {}, source_by_chunk=source_by_chunk
    )
    planner = planner or FixedPlanner()
    retriever = FixedRetriever(retrieved)
    docstore = MemoryDocstore(docs or [])
    return (
        KnowledgeService(
            planner=planner,
            catalog=catalog,
            retriever=retriever,
            docstore=docstore,
        ),
        catalog,
        planner,
        retriever,
        docstore,
    )


def test_empty_allowlist_returns_before_planner_retriever_and_docstore():
    service, catalog, planner, retriever, docstore = make_service(
        sources=[source("a", path="/team/a.md")], chunks_by_source={"a": ["a1"]}
    )

    assert service.search("question", allowed_source_ids=[]) == []
    assert planner.calls == []
    assert retriever.calls == []
    assert docstore.calls == []
    assert not any(call[0] == "chunk_ids" for call in catalog.calls)


def test_none_allowlist_is_global_over_visible_catalog_and_scopes_planned_chunks():
    rows = [
        source("alice", path="/team/a/alice.md", entity={"person": "Alice"}),
        source("bob", path="/team/b/bob.md", entity={"person": "Bob"}),
    ]
    planned = FixedPlanner(source_ids=["alice", "hidden"], confidence=1.0)
    service, catalog, planner, retriever, _ = make_service(
        sources=rows,
        chunks_by_source={"alice": ["a1", "a2"], "bob": ["b1"]},
        planner=planned,
    )

    assert service.search("Alice report", allowed_source_ids=None) == []
    call = retriever.calls[0]
    assert call["scope"] == ["a1", "a2"]
    assert call["fallback_scope"] == ["a1", "a2", "b1"]
    assert planner.calls[0][2]["allowed_source_ids"] == ["alice", "bob"]
    assert catalog.calls[-1] == ("chunk_ids", ("alice", "bob"), "document")


def test_selected_source_ids_are_intersected_with_malicious_planner_scope():
    service, _, _, retriever, _ = make_service(
        sources=[
            source("allowed", path="/allowed.md"),
            source("other", path="/other.md"),
        ],
        chunks_by_source={"allowed": ["allow-chunk"], "other": ["other-chunk"]},
        planner=FixedPlanner(source_ids=["other"], confidence=1.0),
    )

    service.search("question", allowed_source_ids=["allowed"])

    assert retriever.calls[0]["scope"] == []
    assert retriever.calls[0]["fallback_scope"] == ["allow-chunk"]


def test_search_filters_retriever_results_to_mandatory_authorized_chunks():
    authorized = RetrievedDocument(
        id_="allow-chunk", text="visible result", metadata={"file_id": "allowed"}
    )
    out_of_scope = RetrievedDocument(
        id_="other-chunk", text="private result", metadata={"file_id": "other"}
    )
    service, _, _, retriever, _ = make_service(
        sources=[source("allowed"), source("other")],
        chunks_by_source={"allowed": ["allow-chunk"], "other": ["other-chunk"]},
        planner=FixedPlanner(source_ids=["allowed", "other"], confidence=1.0),
        retrieved=[authorized, out_of_scope],
    )

    result = service.search("question", allowed_source_ids=["allowed"])

    assert [document.doc_id for document in result] == ["allow-chunk"]
    assert retriever.calls[0]["scope"] == ["allow-chunk"]
    assert retriever.calls[0]["fallback_scope"] == ["allow-chunk"]


def test_search_keeps_mandatory_chunks_returned_by_approved_fallback():
    fallback_doc = RetrievedDocument(
        id_="fallback-chunk",
        text="visible fallback result",
        metadata={"file_id": "fallback-source"},
    )
    out_of_scope = RetrievedDocument(
        id_="other-chunk", text="private result", metadata={"file_id": "other"}
    )

    class FallbackRetriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            kwargs["trace"]["scope_fallback"] = True
            return [fallback_doc, out_of_scope]

    retriever = FallbackRetriever()
    catalog = MemoryCatalog(
        [source("planned"), source("fallback-source"), source("other")],
        {
            "planned": ["planned-chunk"],
            "fallback-source": ["fallback-chunk"],
            "other": ["other-chunk"],
        },
    )
    service = KnowledgeService(
        planner=FixedPlanner(source_ids=["planned"], confidence=1.0),
        catalog=catalog,
        retriever=retriever,
        docstore=MemoryDocstore([]),
    )
    trace = {"scope_fallback": False}

    result = service.search(
        "question",
        allowed_source_ids=["planned", "fallback-source"],
        trace=trace,
    )

    assert trace["scope_fallback"] is True
    assert retriever.calls[0]["scope"] == ["planned-chunk"]
    assert retriever.calls[0]["fallback_scope"] == [
        "fallback-chunk",
        "planned-chunk",
    ]
    assert [document.doc_id for document in result] == ["fallback-chunk"]


def test_explicit_segment_path_type_and_entity_filters_are_mandatory():
    rows = [
        source(
            "wanted",
            source_type="markdown",
            path="/team/a/guide.md",
            entity={"person": "Alice"},
        ),
        source(
            "child",
            source_type="markdown",
            path="/team/a/sub/child.md",
            entity={"person": "Alice"},
        ),
        source(
            "sibling-prefix",
            source_type="markdown",
            path="/team/abc/guide.md",
            entity={"person": "Alice"},
        ),
        source(
            "wrong-entity",
            source_type="markdown",
            path="/team/a/no.md",
            entity={"person": "Bob"},
        ),
        source(
            "wrong-type",
            source_type="pdf",
            path="/team/a/file.pdf",
            entity={"person": "Alice"},
        ),
    ]
    service, _, planner, retriever, _ = make_service(
        sources=rows,
        chunks_by_source={
            "wanted": ["w"],
            "child": ["c"],
            "sibling-prefix": ["p"],
            "wrong-entity": ["e"],
            "wrong-type": ["t"],
        },
        planner=FixedPlanner(source_ids=None),
    )

    service.search(
        "question",
        path="/team/a",
        source_types=["markdown"],
        filters={"person": " alice "},
    )

    assert retriever.calls[0]["scope"] is None
    assert retriever.calls[0]["fallback_scope"] == ["c", "w"]
    plan_kwargs = planner.calls[0][2]
    assert plan_kwargs["filters"] == {"person": "alice"}
    assert plan_kwargs["source_types"] == ("markdown",)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"source_types": ["archive"]}, "Unsupported source type"),
        ({"filters": {"unknown": "x"}}, "Unsupported metadata filter"),
        ({"filters": {"person": ["Alice"]}}, "scalar value"),
        ({"path": "/team/../private"}, "parent traversal"),
    ],
)
def test_invalid_explicit_constraints_fail_closed(kwargs, message):
    service, _, _, retriever, _ = make_service(
        sources=[source("a", path="/team/a.md", entity={"person": "Alice"})],
        chunks_by_source={"a": ["a1"]},
    )

    with pytest.raises(ValueError, match=message):
        service.search("question", **kwargs)
    assert retriever.calls == []


def test_low_confidence_plan_uses_only_visible_chunk_fallback():
    service, _, _, retriever, _ = make_service(
        sources=[
            source("visible", path="/visible.md"),
            source("hidden", path="/hidden.md"),
        ],
        chunks_by_source={"visible": ["v1"], "hidden": ["h1"]},
        planner=FixedPlanner(source_ids=None),
    )

    service.search("ambiguous", allowed_source_ids=["visible"])

    assert retriever.calls[0]["scope"] is None
    assert retriever.calls[0]["fallback_scope"] == ["v1"]


def test_read_authorizes_by_document_relation_not_forged_chunk_metadata():
    forged = Document(
        id_="chunk-a", text="authorized text", metadata={"file_id": "source-b"}
    )
    service, _, _, _, docstore = make_service(
        sources=[source("source-a"), source("source-b")],
        chunks_by_source={"source-a": ["chunk-a"], "source-b": ["chunk-b"]},
        docs=[forged],
    )

    result = service.read("chunk-a", allowed_source_ids=["source-a"])

    assert result is forged
    assert docstore.calls == [["chunk-a"]]


def test_read_returns_none_for_denied_missing_or_unrelated_chunk():
    doc = Document(id_="chunk-a", text="secret", metadata={})
    service, _, _, _, docstore = make_service(
        sources=[source("source-a"), source("source-b")],
        chunks_by_source={"source-a": ["chunk-a"], "source-b": ["chunk-b"]},
        source_by_chunk={"chunk-a": "source-a", "chunk-b": "source-b"},
        docs=[doc],
    )

    assert service.read("chunk-a", allowed_source_ids=["source-b"]) is None
    assert service.read("missing", allowed_source_ids=None) is None
    assert service.read("vector-only", allowed_source_ids=None) is None
    assert docstore.calls == []


def test_read_finds_requested_id_when_docstore_reorders_results():
    first = Document(id_="chunk-a", text="A", metadata={})
    second = Document(id_="chunk-b", text="B", metadata={})
    service, _, _, _, _ = make_service(
        sources=[source("source-a")],
        chunks_by_source={"source-a": ["chunk-a", "chunk-b"]},
        docs=[first, second],
    )

    assert service.read("chunk-a") is first


def test_list_returns_immediate_children_without_exposing_storage_paths():
    rows = [
        source("a", path="/team/a/doc.md", name="doc.md"),
        source("b", path="/team/abc/other.md", name="other.md"),
        source("c", path="/team/a/sub/leaf.md", name="leaf.md"),
        source("legacy", name="/tmp/upload-993/old.md"),
    ]
    service, _, _, _, _ = make_service(sources=rows)

    root = service.list("/")
    team = service.list("/team")
    branch = service.list("/team/a")

    assert [(item["kind"], item["name"]) for item in root] == [
        ("directory", "team"),
        ("source", "old.md"),
    ]
    assert [(item["kind"], item["name"]) for item in team] == [
        ("directory", "a"),
        ("directory", "abc"),
    ]
    assert [(item["kind"], item["name"]) for item in branch] == [
        ("directory", "sub"),
        ("source", "doc.md"),
    ]
    serialized = repr(root + team + branch)
    assert "/tmp/upload-993" not in serialized


def test_list_applies_visible_allowlist_and_has_stable_order():
    service, _, _, _, _ = make_service(
        sources=[
            source("z", path="/z.md", name="z.md"),
            source("a", path="/a.md", name="a.md"),
        ]
    )

    assert [
        item["source_id"] for item in service.list(allowed_source_ids=["z", "a"])
    ] == [
        "a",
        "z",
    ]
    assert service.list(allowed_source_ids=[]) == []
