"""The file-index UI keeps its explicit selected-files boundary."""

from ktem.index.file.pipelines import DocumentRetrievalPipeline
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.storages import InMemoryDocumentStore, InMemoryVectorStore


class FixedEmbeddings(BaseEmbeddings):
    def run(self, text, *args, **kwargs):
        return [DocumentWithEmbedding(embedding=[1.0, 0.0])]


def test_no_selected_files_returns_empty_without_calling_retrieval():
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Index=None,
        VS=None,
        DS=None,
    )

    assert pipeline.run(text="question", doc_ids=[]) == []


def test_selected_source_ids_are_resolved_to_chunk_scope(monkeypatch, tmp_path):
    base = declarative_base()

    class Index(base):
        __tablename__ = "index_relation"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    class Source(base):
        __tablename__ = "source"
        id = Column(String, primary_key=True)
        name = Column(String)
        user = Column(String)
        note = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'index.db'}")
    base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                Source(id="source-a", name="a.md", user="", note=None),
                Source(id="source-b", name="b.md", user="", note=None),
            ]
        )
        session.add_all(
            [
                Index(
                    source_id="source-a", target_id="chunk-a", relation_type="document"
                ),
                Index(
                    source_id="source-b", target_id="chunk-b", relation_type="document"
                ),
            ]
        )
        session.commit()

    from ktem.index.file.knowledge_service import create_file_knowledge_service

    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: create_file_knowledge_service(
            **kwargs, session_factory=session_factory
        ),
    )
    vector = InMemoryVectorStore()
    vector.add(
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[{"file_id": "source-a"}, {"file_id": "source-b"}],
        ids=["chunk-a", "chunk-b"],
    )
    docs = InMemoryDocumentStore()
    docs.add(
        [
            Document(
                id_="chunk-a", text="selected chunk", metadata={"file_id": "source-a"}
            ),
            Document(
                id_="chunk-b", text="other chunk", metadata={"file_id": "source-b"}
            ),
        ]
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=FixedEmbeddings(),
        Source=Source,
        Index=Index,
        VS=vector,
        DS=docs,
        retrieval_mode="vector",
    )

    result = pipeline.run(text="question", doc_ids=["source-a"])

    assert [doc.doc_id for doc in result] == ["chunk-a"]
