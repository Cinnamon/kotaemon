"""Behavior tests for post-rerank diversity and thumbnail ordering."""

from __future__ import annotations

from typing import Union

import pytest
from llama_index.core.vector_stores import (
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.rankings import BaseReranking
from kotaemon.storages.docstores.base import BaseDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore


class FakeEmbedding(BaseEmbeddings):
    def run(self, text, *args, **kwargs):
        return [DocumentWithEmbedding(embedding=[0.1])]


class FakeVectorStore(BaseVectorStore):
    def __init__(self, ids):
        self.ids = list(ids)

    def add(self, embeddings, metadatas=None, ids=None):
        return ids or []

    def delete(self, ids, **kwargs):
        pass

    def query(self, embedding, top_k=1, ids=None, **kwargs):
        selected = (
            self.ids
            if ids is None
            else [doc_id for doc_id in self.ids if doc_id in ids]
        )
        return (
            [],
            [1.0 - index / 100 for index in range(len(selected))],
            selected[:top_k],
        )

    def drop(self):
        pass


class FakeDocumentStore(BaseDocumentStore):
    supports_lexical_search = False

    def __init__(self, documents, *, reverse_get=False):
        self.documents = {doc.doc_id: doc for doc in documents}
        self.reverse_get = reverse_get
        self.get_calls = []

    def add(self, docs, ids=None, **kwargs):
        for doc in docs if isinstance(docs, list) else [docs]:
            self.documents[doc.doc_id] = doc

    def get(self, ids: Union[list[str], str]):
        ids = [ids] if isinstance(ids, str) else list(ids)
        self.get_calls.append(ids)
        if self.reverse_get:
            ids.reverse()
        return [self.documents[doc_id] for doc_id in ids if doc_id in self.documents]

    def get_all(self):
        return list(self.documents.values())

    def count(self):
        return len(self.documents)

    def query(self, query, top_k=10, doc_ids=None):
        return []

    def delete(self, ids):
        pass

    def drop(self):
        self.documents.clear()


class FixedReranker(BaseReranking):
    def __init__(self, order):
        super().__init__()
        object.__setattr__(self, "_order", list(order))

    def run(self, documents, query):
        by_id = {doc.doc_id: doc for doc in documents}
        return [by_id[doc_id] for doc_id in self._order if doc_id in by_id]


def make_doc(doc_id, text=None, **metadata):
    return Document(
        id_=doc_id, text=text if text is not None else doc_id, metadata=metadata
    )


def retrieve(documents, *, ids=None, top_k=5, rerankers=None, **kwargs):
    store = FakeDocumentStore(documents, reverse_get=kwargs.pop("reverse_get", False))
    pipeline = VectorRetrieval(
        vector_store=FakeVectorStore(ids or [doc.doc_id for doc in documents]),
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        rerankers=rerankers or [],
        **kwargs,
    )
    return (
        pipeline,
        store,
        pipeline(
            text="question", top_k=top_k, scope=kwargs.get("scope"), do_extend=True
        ),
    )


def test_normalized_exact_content_is_deduplicated_before_top_k():
    first = make_doc("first", "The answer is on page seven.", file_id="source-a")
    same = make_doc("same", "  THE answer   is on page seven. ", file_id="source-b")
    other = make_doc("other", "A distinct and useful answer.", file_id="source-c")

    _, _, result = retrieve([first, same, other], top_k=2)

    assert [doc.doc_id for doc in result] == ["first", "other"]


def test_high_overlap_siblings_are_suppressed_but_short_text_is_kept():
    body = (
        "The service accepts requests from the internal employee portal and "
        "returns a detailed status report. " * 3
    )
    sibling = make_doc(
        "sibling", body + "The user may also retry later.", file_id="src", parent_id="p"
    )
    overlap = make_doc(
        "overlap", body + "The user may retry later.", file_id="src", parent_id="p"
    )
    tiny_a = make_doc("tiny-a", "yes", file_id="src", parent_id="short")
    tiny_b = make_doc("tiny-b", "no", file_id="src", parent_id="short")

    _, _, result = retrieve(
        [sibling, overlap, tiny_a, tiny_b], top_k=4, max_per_parent_or_section=None
    )

    assert [doc.doc_id for doc in result] == ["sibling", "tiny-a", "tiny-b"]


def test_parent_cap_prefers_diverse_candidate_and_refills_in_rank_order():
    first = make_doc("first", "first content", file_id="src", parent_id="p")
    second = make_doc("second", "second content", file_id="src", parent_id="p")
    deferred = make_doc("deferred", "deferred content", file_id="src", parent_id="p")
    diverse = make_doc("diverse", "different section", file_id="src", parent_id="q")

    _, _, result = retrieve(
        [first, second, deferred, diverse], top_k=3, max_per_parent_or_section=2
    )

    assert [doc.doc_id for doc in result] == ["first", "second", "diverse"]


def test_parent_cap_refills_when_there_are_not_enough_alternatives():
    first = make_doc("first", "first", file_id="src", parent_id="p")
    second = make_doc("second", "second", file_id="src", parent_id="p")
    third = make_doc("third", "third", file_id="src", parent_id="p")

    _, _, result = retrieve(
        [first, second, third], top_k=3, max_per_parent_or_section=2
    )

    assert [doc.doc_id for doc in result] == ["first", "second", "third"]


def test_same_parent_label_in_different_sources_does_not_share_cap():
    first = make_doc("first", "first", file_id="src-a", parent_id="p")
    second = make_doc("second", "second", file_id="src-b", parent_id="p")

    _, _, result = retrieve([first, second], top_k=2, max_per_parent_or_section=1)

    assert [doc.doc_id for doc in result] == ["first", "second"]


def test_section_cap_applies_when_each_chunk_has_a_distinct_parent_id():
    first = make_doc(
        "first",
        "first",
        document_id="src",
        parent_id="chunk-1",
        section_path=["Policy"],
    )
    second = make_doc(
        "second",
        "second",
        document_id="src",
        parent_id="chunk-2",
        section_path=["Policy"],
    )
    alternate = make_doc(
        "alternate",
        "alternate",
        document_id="src",
        parent_id="chunk-3",
        section_path=["FAQ"],
    )

    _, _, result = retrieve(
        [first, second, alternate], top_k=2, max_per_parent_or_section=1
    )

    assert [doc.doc_id for doc in result] == ["first", "alternate"]


def test_missing_group_metadata_and_reranker_order_are_preserved():
    documents = [
        make_doc("first", "first", file_id="src-a", parent_id="p"),
        make_doc("legacy", "legacy"),
        make_doc("last", "last", file_id="src-b", parent_id="q"),
    ]

    _, _, result = retrieve(
        documents,
        top_k=3,
        rerankers=[FixedReranker(["last", "legacy", "first"])],
        max_per_parent_or_section=1,
    )

    assert [doc.doc_id for doc in result] == ["last", "legacy", "first"]


def test_linked_thumbnails_follow_selected_rank_and_remain_within_top_k():
    first = make_doc(
        "first", "first text", file_id="src", thumbnail_doc_id="thumb-first"
    )
    second = make_doc(
        "second", "second text", file_id="src", thumbnail_doc_id="thumb-second"
    )
    thumb_first = make_doc(
        "thumb-first", "", type="thumbnail", file_id="src", image_origin="img-1"
    )
    thumb_second = make_doc(
        "thumb-second", "", type="thumbnail", file_id="src", image_origin="img-2"
    )
    store = FakeDocumentStore(
        [first, second, thumb_first, thumb_second], reverse_get=True
    )
    pipeline = VectorRetrieval(
        vector_store=FakeVectorStore(["first", "second"]),
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        max_per_parent_or_section=None,
    )

    result = pipeline(
        text="question",
        top_k=2,
        scope=["first", "second", "thumb-first", "thumb-second"],
        thumbnail_count=2,
    )

    assert [doc.doc_id for doc in result] == ["first", "second"]
    assert [doc.metadata["image_origin"] for doc in result] == ["img-1", "img-2"]
    assert len(result) <= 2


def test_thumbnail_outside_scope_is_never_fetched():
    text = make_doc(
        "text", "visible text", file_id="source-a", thumbnail_doc_id="private-thumb"
    )
    private = make_doc(
        "private-thumb",
        "",
        type="thumbnail",
        file_id="source-a",
        image_origin="private-image",
    )
    store = FakeDocumentStore([text, private])
    pipeline = VectorRetrieval(
        vector_store=FakeVectorStore(["text"]),
        doc_store=store,
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        max_per_parent_or_section=None,
    )

    result = pipeline(text="question", top_k=1, scope=["text"])

    assert [doc.doc_id for doc in result] == ["text"]
    assert all("private-thumb" not in ids for ids in store.get_calls)


def test_thumbnail_metadata_filter_failure_keeps_safe_text_result():
    text = make_doc(
        "text",
        "visible evidence",
        file_id="source-a",
        visibility="public",
        thumbnail_doc_id="thumb",
    )
    thumbnail = make_doc(
        "thumb",
        "",
        type="thumbnail",
        file_id="source-a",
        visibility="private",
        image_origin="private-image",
    )
    pipeline = VectorRetrieval(
        vector_store=FakeVectorStore(["text"]),
        doc_store=FakeDocumentStore([text, thumbnail]),
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        max_per_parent_or_section=None,
    )

    result = pipeline(
        text="question",
        top_k=1,
        scope=["text", "thumb"],
        filters=MetadataFilters(
            filters=[
                MetadataFilter(
                    key="visibility", value="public", operator=FilterOperator.EQ
                )
            ]
        ),
    )

    assert [doc.doc_id for doc in result] == ["text"]
    assert result[0].text == "visible evidence"
    assert result[0].metadata.get("image_origin") is None


@pytest.mark.parametrize(
    ("text_source_id", "thumbnail_source_id"),
    [(None, "other-source"), ("source-a", None), (None, None)],
)
def test_linked_thumbnail_requires_confirmed_source_identity(
    text_source_id, thumbnail_source_id
):
    text_metadata = {"thumbnail_doc_id": "thumb"}
    thumbnail_metadata = {"type": "thumbnail", "image_origin": "unverified-image"}
    if text_source_id is not None:
        text_metadata["document_id"] = text_source_id
    if thumbnail_source_id is not None:
        thumbnail_metadata["file_id"] = thumbnail_source_id
    text = make_doc("text", "citation-ready source evidence", **text_metadata)
    thumbnail = make_doc("thumb", "", **thumbnail_metadata)
    pipeline = VectorRetrieval(
        vector_store=FakeVectorStore(["text"]),
        doc_store=FakeDocumentStore([text, thumbnail]),
        embedding=FakeEmbedding(),
        retrieval_mode="vector",
        max_per_parent_or_section=None,
    )

    result = pipeline(text="question", top_k=1, scope=["text", "thumb"])

    assert [doc.doc_id for doc in result] == ["text"]
    assert result[0].text == "citation-ready source evidence"
    assert result[0].metadata.get("type") is None
    assert result[0].metadata.get("image_origin") is None


def test_selected_ids_are_exposed_to_optional_trace():
    documents = [
        make_doc("first", "same evidence"),
        make_doc("duplicate", " same evidence "),
    ]
    pipeline, _, _ = retrieve(documents, top_k=2)
    trace = {}

    result = pipeline(text="question", top_k=2, do_extend=True, trace=trace)

    assert [doc.doc_id for doc in result] == ["first"]
    assert trace["diversity_selected_ids"] == ["first"]
