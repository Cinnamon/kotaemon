"""Knowledge ingestion through the public single-file and batch entry points."""

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from ktem.index.file import pipelines
from llama_index.core.readers.base import BaseReader
from sqlalchemy import JSON, Column, Integer, String, create_engine, select
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Session, declarative_base

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.ingests.files import KH_DEFAULT_FILE_EXTRACTORS
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.loaders import TxtReader
from kotaemon.loaders.excel_loader import ExcelRowReader
from kotaemon.loaders.pptx_loader import PptxReader
from kotaemon.storages import (
    ChromaVectorStore,
    InMemoryDocumentStore,
    InMemoryVectorStore,
)


class FixtureReader(BaseReader):
    def __init__(self, side_effects=None):
        super().__init__()
        self.last_extra_info = None
        self.side_effects = side_effects if side_effects is not None else []
        self.metadata_overrides = {}
        self.document_text = None
        self.omit_source_version = False

    def load_data(self, file, extra_info=None, **kwargs):
        self.side_effects.append("load_data")
        self.last_extra_info = dict(extra_info or {})
        metadata = {**(extra_info or {}), **self.metadata_overrides}
        if self.omit_source_version:
            metadata.pop("source_version", None)
        return [
            Document(
                text=(
                    self.document_text
                    if self.document_text is not None
                    else "# Intro\n\nBody\n\n## Details\n\nDetails"
                ),
                metadata=metadata,
            )
        ]


class FixtureEmbeddings(BaseEmbeddings):
    def invoke(self, text, **kwargs):
        return [
            DocumentWithEmbedding(content=doc, embedding=[1.0, 0.0]) for doc in text
        ]


class CapturingVectorStore(InMemoryVectorStore):
    def __init__(self):
        super().__init__()
        self._metadata_by_id = {}

    @property
    def metadata_by_id(self):
        return self._metadata_by_id

    def add(self, embeddings, metadatas=None, ids=None):
        self._metadata_by_id.update(zip(ids, deepcopy(metadatas or [{} for _ in ids])))
        return super().add(embeddings, metadatas=metadatas, ids=ids)


def consume_stream(stream):
    while True:
        try:
            next(stream)
        except StopIteration as result:
            return result.value


@pytest.fixture
def index_pipeline_fixture(monkeypatch, tmp_path):
    base = declarative_base()

    class Source(base):
        __tablename__ = "fixture_source"
        id = Column(String, primary_key=True)
        path = Column(String)
        size = Column(Integer)
        note = Column(MutableDict.as_mutable(JSON))

    class Index(base):
        __tablename__ = "fixture_index"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'fixture.db'}")
    base.metadata.create_all(engine)
    monkeypatch.setattr(pipelines, "engine", engine)
    source_id = "fixture-source"
    with Session(engine) as session:
        session.add(Source(id=source_id, note={"tokens": 42, "preserve": "existing"}))
        session.commit()

    pipeline_side_effects = []

    class FixturePipeline(pipelines.IndexPipeline):
        def get_id_if_exists(self, file_path):
            pipeline_side_effects.append("get_id_if_exists")
            return None

        def store_file(self, file_path):
            pipeline_side_effects.append("store_file")
            with Session(engine) as session:
                source = session.get(Source, source_id)
                source.path = sha256(file_path.read_bytes()).hexdigest()
                source.size = file_path.stat().st_size
                session.commit()
            return source_id

    reader = FixtureReader(side_effects=pipeline_side_effects)
    docstore = InMemoryDocumentStore()
    vectorstore = CapturingVectorStore()
    pipeline = FixturePipeline(
        loader=reader,
        splitter=TokenSplitter(chunk_size=128, chunk_overlap=0),
        Source=Source,
        Index=Index,
        DS=docstore,
        VS=vectorstore,
        embedding=FixtureEmbeddings(),
        FSPath=tmp_path,
        user_id="fixture-user",
    )
    pipeline.vector_indexing.cache_dir = None

    def get_source():
        with Session(engine) as session:
            return session.execute(select(Source)).scalar_one()

    yield pipeline, reader, docstore, vectorstore, source_id, get_source
    engine.dispose()


@pytest.fixture
def index_document_pipeline_fixture():
    class RoutedPipeline:
        received_knowledge_metadata = None
        received_path = None

        def stream(self, file_path, reindex=False, **kwargs):
            self.received_path = file_path
            self.received_knowledge_metadata = kwargs.get("knowledge_metadata")
            assert "knowledge_metadata_by_path" not in kwargs
            yield Document("done", channel="debug")
            return "fixture-source", [Document("fixture")]

    routed = RoutedPipeline()

    class BatchPipeline(pipelines.IndexDocumentPipeline):
        def route(self, file_path):
            return routed

    return BatchPipeline(embedding=FixtureEmbeddings()), routed


def test_stream_persists_caller_knowledge_metadata(index_pipeline_fixture, tmp_path):
    pipeline, reader, docstore, vectorstore, source_id, get_source = (
        index_pipeline_fixture
    )
    input_path = tmp_path / "Zhang San.md"
    input_path.write_text("fixture", encoding="utf-8")
    consume_stream(
        pipeline.stream(
            input_path,
            reindex=False,
            knowledge_metadata={"virtual_path": "/Interns/App/Zhang San"},
        )
    )
    assert reader.last_extra_info["file_id"] == source_id
    assert reader.last_extra_info["virtual_path"] == "/Interns/App/Zhang San"
    stored = docstore.get_all()
    assert len(stored) == 2
    assert {tuple(item.metadata["section_path"]) for item in stored} == {
        ("Intro",),
        ("Intro", "Details"),
    }
    assert all(
        item.metadata["virtual_path"] == "/Interns/App/Zhang San" for item in stored
    )
    assert all(item.metadata["file_id"] == source_id for item in stored)
    assert all(
        vectorstore.metadata_by_id[item.doc_id]["virtual_path"]
        == "/Interns/App/Zhang San"
        for item in stored
    )
    source = get_source()
    assert source.note["tokens"] > 0
    assert source.note["loader"] == "FixtureReader"
    assert source.note["preserve"] == "existing"
    assert source.note["knowledge"] == {
        "source_type": "markdown",
        "virtual_path": "/Interns/App/Zhang San",
        "document_name": "Zhang San.md",
        "entity": {},
        "source_version": sha256(input_path.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize(
    "reserved_key", ["file_id", "document_id", "collection_name", "source_version"]
)
def test_stream_rejects_caller_identity_metadata_before_indexing(
    index_pipeline_fixture, tmp_path, reserved_key
):
    pipeline, reader, docstore, vectorstore, _, get_source = index_pipeline_fixture
    input_path = tmp_path / "reserved.md"
    input_path.write_text("fixture", encoding="utf-8")
    original_note = get_source().note

    with pytest.raises(ValueError, match=reserved_key):
        consume_stream(
            pipeline.stream(
                input_path,
                knowledge_metadata={reserved_key: "caller-controlled"},
            )
        )

    assert reader.side_effects == []
    assert reader.last_extra_info is None
    assert docstore.get_all() == []
    assert vectorstore.metadata_by_id == {}
    assert get_source().note == original_note


def test_stream_preserves_custom_metadata_and_trusted_reader_identity(
    index_pipeline_fixture, tmp_path
):
    pipeline, reader, docstore, _, _, get_source = index_pipeline_fixture
    input_path = tmp_path / "fixture.md"
    input_path.write_text("fixture", encoding="utf-8")
    reader.metadata_overrides = {"document_id": "reader-issued-document"}
    custom_metadata = {
        "source_type": "wiki",
        "virtual_path": "/Interns/App/Fixture",
        "document_name": "logical-fixture.md",
        "entity": {"owner": "Zhang San"},
        "tags": ["app", "intern"],
        "page": 7,
    }

    consume_stream(pipeline.stream(input_path, knowledge_metadata=custom_metadata))

    stored = docstore.get_all()
    assert stored
    assert all(
        item.metadata["document_id"] == "reader-issued-document" for item in stored
    )
    assert all(
        {key: item.metadata[key] for key in custom_metadata} == custom_metadata
        for item in stored
    )
    assert get_source().note["knowledge"] == {
        "source_type": "wiki",
        "virtual_path": "/Interns/App/Fixture",
        "document_name": "logical-fixture.md",
        "entity": {"owner": "Zhang San"},
        "source_version": sha256(input_path.read_bytes()).hexdigest(),
    }


def test_stream_without_knowledge_metadata_keeps_legacy_fallback(
    index_pipeline_fixture, tmp_path
):
    pipeline, _, docstore, _, _, _ = index_pipeline_fixture
    input_path = tmp_path / "legacy.txt"
    input_path.write_text("legacy fixture", encoding="utf-8")
    consume_stream(pipeline.stream(input_path, reindex=False))
    assert docstore.get_all()
    assert all(
        item.metadata["virtual_path"] == "/legacy.txt" for item in docstore.get_all()
    )


@pytest.mark.parametrize("split", [True, False])
def test_handle_docs_normalizes_all_stored_artifact_types(
    index_pipeline_fixture, split
):
    pipeline, _, docstore, vectorstore, source_id, _ = index_pipeline_fixture
    if not split:
        pipeline.splitter = None
    documents = [
        Document(
            text=kind,
            metadata={
                "file_name": "artifacts.md",
                "file_id": source_id,
                "type": kind,
                "page_label": 1,
            },
        )
        for kind in ("text", "table", "image", "thumbnail")
    ]
    consume_stream(pipeline.handle_docs(documents, source_id, "artifacts.md"))
    stored = docstore.get_all()
    assert {item.metadata["type"] for item in stored} == {
        "text",
        "table",
        "image",
        "thumbnail",
    }
    assert all(item.metadata["source_type"] == "markdown" for item in stored)
    assert all(item.metadata["chunk_id"] == item.doc_id for item in stored)
    assert all(
        vectorstore.metadata_by_id[item.doc_id] == item.metadata for item in stored
    )
    text = next(item for item in stored if item.metadata["type"] == "text")
    thumbnail = next(item for item in stored if item.metadata["type"] == "thumbnail")
    assert text.metadata["thumbnail_doc_id"] == thumbnail.doc_id


@pytest.mark.parametrize("path_as_string", [True, False])
def test_batch_stream_uses_metadata_keyed_by_original_input_path(
    index_document_pipeline_fixture,
    tmp_path,
    path_as_string,
):
    input_path = tmp_path / "folder" / ".." / "Zhang San.md"
    original_path = str(input_path) if path_as_string else input_path
    indexer, routed = index_document_pipeline_fixture
    result = consume_stream(
        indexer.stream(
            [original_path],
            knowledge_metadata_by_path={
                original_path: {"virtual_path": "/Interns/App/Zhang San"}
            },
        )
    )
    assert result[0] == ["fixture-source"]
    assert routed.received_path == input_path
    assert routed.received_knowledge_metadata == {
        "virtual_path": "/Interns/App/Zhang San"
    }


def test_default_readers_and_developer_precedence(monkeypatch):
    assert isinstance(KH_DEFAULT_FILE_EXTRACTORS[".faq"], TxtReader)
    for extension in (
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".h",
        ".cpp",
        ".hpp",
    ):
        assert isinstance(KH_DEFAULT_FILE_EXTRACTORS[extension], TxtReader)
    for extension in (".xlsx", ".xls", ".csv"):
        assert isinstance(KH_DEFAULT_FILE_EXTRACTORS[extension], ExcelRowReader)
    for extension in (".ppt", ".pptx"):
        assert isinstance(KH_DEFAULT_FILE_EXTRACTORS[extension], PptxReader)
    override = FixtureReader()
    monkeypatch.setattr(
        pipelines, "dev_settings", lambda: ({".py": override}, None, None)
    )
    indexer = pipelines.IndexDocumentPipeline(embedding=FixtureEmbeddings())
    assert indexer.readers[".py"] is override


def test_finish_normalizes_caller_summary_and_merges_knowledge(
    index_pipeline_fixture, tmp_path
):
    pipeline, _, _, _, _, get_source = index_pipeline_fixture
    with Session(pipelines.engine) as session:
        source = session.get(pipeline.Source, "fixture-source")
        source.note = {**source.note, "knowledge": {"custom": "keep"}}
        session.commit()
    input_path = tmp_path / "original.txt"
    input_path.write_text("fixture", encoding="utf-8")
    consume_stream(
        pipeline.stream(
            input_path,
            reindex=False,
            knowledge_metadata={
                "source_type": "wiki",
                "virtual_path": "Interns/./App/../Zhang San",
                "document_name": "logical.md",
                "entity": {"owner": "Zhang San"},
            },
        )
    )
    summary = get_source().note["knowledge"]
    assert summary == {
        "custom": "keep",
        "source_type": "wiki",
        "virtual_path": "/Interns/Zhang San",
        "document_name": "logical.md",
        "entity": {"owner": "Zhang San"},
        "source_version": sha256(input_path.read_bytes()).hexdigest(),
    }


def test_product_metadata_roundtrip_keeps_locator(index_pipeline_fixture, tmp_path):
    pipeline, reader, docstore, vectorstore, _, _ = index_pipeline_fixture
    input_path = tmp_path / "located.md"
    input_path.write_bytes(b"uploaded bytes v1")
    expected_version = sha256(input_path.read_bytes()).hexdigest()
    reader.document_text = (
        "# A\n\n" + "alpha beta gamma delta " * 24 + "\n\n# B\n\nomega"
    )
    reader.metadata_overrides = {"page_label": "page-7"}
    pipeline.splitter = TokenSplitter(chunk_size=12, chunk_overlap=0)

    consume_stream(
        pipeline.stream(
            input_path,
            knowledge_metadata={"virtual_path": "/Policies/Located"},
        )
    )

    stored = docstore.get_all()
    assert len(stored) > 2
    assert {document.doc_id for document in stored} == set(vectorstore.metadata_by_id)
    assert all(
        vectorstore.metadata_by_id[document.doc_id] == document.metadata
        for document in stored
    )
    assert all(
        document.metadata["source_version"] == expected_version for document in stored
    )
    assert all(document.metadata["page_label"] == "page-7" for document in stored)
    assert all(document.metadata["chunk_id"] == document.doc_id for document in stored)
    assert all(document.metadata["unit_id"] for document in stored)

    units = {}
    for document in stored:
        units.setdefault(document.metadata["unit_id"], []).append(document)
    assert len(units) == 2
    for unit_chunks in units.values():
        ordered = sorted(
            unit_chunks, key=lambda document: document.metadata["chunk_ordinal"]
        )
        assert [document.metadata["chunk_ordinal"] for document in ordered] == list(
            range(len(ordered))
        )
        assert "previous_chunk_id" not in ordered[0].metadata
        assert "next_chunk_id" not in ordered[-1].metadata
        for left, right in zip(ordered, ordered[1:]):
            assert left.metadata["next_chunk_id"] == right.doc_id
            assert right.metadata["previous_chunk_id"] == left.doc_id


@pytest.mark.parametrize("reader_mutation", ["omit", "overwrite"])
def test_stream_enforces_source_version_from_uploaded_bytes(
    index_pipeline_fixture, tmp_path, reader_mutation
):
    pipeline, reader, docstore, vectorstore, _, get_source = index_pipeline_fixture
    input_path = tmp_path / "reader-version.md"
    input_path.write_bytes(b"the uploaded source bytes")
    expected_version = sha256(input_path.read_bytes()).hexdigest()
    reader.document_text = "# Section\n\n" + "same unit chunk " * 30
    pipeline.splitter = TokenSplitter(chunk_size=12, chunk_overlap=0)
    if reader_mutation == "omit":
        reader.omit_source_version = True
    else:
        reader.metadata_overrides = {"source_version": "reader-controlled-value"}

    consume_stream(pipeline.stream(input_path))

    stored = docstore.get_all()
    assert len(stored) > 1
    assert all(
        document.metadata["source_version"] == expected_version for document in stored
    )
    assert all(document.metadata["unit_id"] for document in stored)
    assert all(
        vectorstore.metadata_by_id[document.doc_id] == document.metadata
        for document in stored
    )
    assert get_source().note["knowledge"]["source_version"] == expected_version


def test_url_locator_hash_is_not_claimed_as_content_version(
    index_pipeline_fixture, monkeypatch
):
    pipeline, reader, docstore, _, source_id, _ = index_pipeline_fixture
    url = "https://example.test/policies"
    with Session(pipelines.engine) as session:
        source = session.get(pipeline.Source, source_id)
        source.path = sha256(url.encode("utf-8")).hexdigest()
        session.commit()

    assert pipeline._source_version(source_id, url) is None

    def store_fixture_url(self, _url):
        with Session(pipelines.engine) as session:
            source = session.get(self.Source, source_id)
            source.path = sha256(url.encode("utf-8")).hexdigest()
            session.commit()
        return source_id

    monkeypatch.setattr(type(pipeline), "store_url", store_fixture_url)
    reader.metadata_overrides = {"source_type": "markdown"}
    consume_stream(pipeline.stream(url))

    stored = docstore.get_all()
    assert stored
    assert all("source_version" not in document.metadata for document in stored)
    assert all(
        "_semantic_unit_group_id" not in document.metadata for document in stored
    )
    with Session(pipelines.engine) as session:
        source = session.get(pipeline.Source, source_id)
    assert "source_version" not in source.note["knowledge"]


def test_default_chroma_accepts_knowledge_metadata(index_pipeline_fixture, tmp_path):
    pipeline, _, docstore, _, _, _ = index_pipeline_fixture
    vectorstore = ChromaVectorStore(path=str(tmp_path / "chroma"))
    pipeline.VS = vectorstore
    pipeline.vector_indexing.vector_store = vectorstore
    input_path = tmp_path / "knowledge.md"
    input_path.write_text("fixture", encoding="utf-8")
    consume_stream(
        pipeline.stream(
            input_path,
            knowledge_metadata={
                "virtual_path": "/Interns/App",
                "entity": {"owner": "Zhang San"},
                "tags": ["app", "intern"],
                "page": 7,
            },
        )
    )
    stored = docstore.get_all()
    assert vectorstore.count() == len(stored)
    assert all(item.metadata["entity"] == {"owner": "Zhang San"} for item in stored)
    assert all(isinstance(item.metadata["section_path"], list) for item in stored)
    result = vectorstore._collection.get(where={"virtual_path": "/Interns/App"})
    assert set(result["ids"]) == {item.doc_id for item in stored}
    metadata_by_id = dict(zip(result["ids"], result["metadatas"]))
    for item in stored:
        metadata = metadata_by_id[item.doc_id]
        assert json.loads(metadata["entity"]) == item.metadata["entity"]
        assert json.loads(metadata["section_path"]) == item.metadata["section_path"]
        assert json.loads(metadata["tags"]) == ["app", "intern"]
        for key in ("source_type", "virtual_path", "file_id", "document_id", "page"):
            assert metadata[key] == item.metadata[key]


def test_chroma_node_metadata_projection_preserves_input(tmp_path):
    document = DocumentWithEmbedding(
        text="knowledge",
        embedding=[1.0, 0.0],
        metadata={
            "document_id": "source",
            "entity": {"owner": "Zhang San"},
            "section_path": ["Intro"],
        },
    )
    metadata_before = deepcopy(document.metadata)
    relationships_before = deepcopy(document.relationships)
    vectorstore = ChromaVectorStore(path=str(tmp_path / "chroma"))
    vectorstore.add([document])
    assert document.metadata == metadata_before
    assert document.relationships == relationships_before
    assert vectorstore._collection.get()["metadatas"][0]["document_id"] == "source"
