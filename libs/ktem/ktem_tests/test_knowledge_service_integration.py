"""The file QA retriever delegates selected-source search to KnowledgeService."""

from ktem.index.file.pipelines import DocumentRetrievalPipeline

from kotaemon.base import RetrievedDocument


class CapturingKnowledgeService:
    def __init__(self, result, chunk_ids=None):
        self.result = list(result)
        self.chunk_ids = list(chunk_ids or [])
        self.search_calls = []
        self.chunk_calls = []

    def search(self, query, **kwargs):
        self.search_calls.append((query, kwargs))
        return list(self.result)

    def chunk_ids_for_sources(self, source_ids):
        self.chunk_calls.append(list(source_ids))
        return list(self.chunk_ids)


def test_file_qa_flattens_group_selection_and_preserves_citation_documents(monkeypatch):
    cited = RetrievedDocument(
        id_="chunk-a",
        text="the quoted source passage",
        metadata={"file_id": "source-a", "file_name": "guide.md", "page_label": "4"},
        score=0.91,
    )
    service = CapturingKnowledgeService([cited], ["chunk-a", "chunk-b"])
    factory_calls = []

    def build_service(**kwargs):
        factory_calls.append(kwargs)
        return service

    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        build_service,
        raising=False,
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        private=True,
        user_id="user-a",
        top_k=3,
    )

    result = pipeline.run(
        text="where is the procedure?", doc_ids=['["source-a", "source-b"]']
    )

    assert result == [cited]
    assert result[0].metadata == {
        "file_id": "source-a",
        "file_name": "guide.md",
        "page_label": "4",
    }
    assert service.search_calls == [
        (
            "where is the procedure?",
            {
                "allowed_source_ids": ["source-a", "source-b"],
                "top_k": 3,
                "trace": None,
            },
        )
    ]
    assert service.chunk_calls == [["source-a", "source-b"]]
    assert factory_calls[0]["private"] is True
    assert factory_calls[0]["user_id"] == "user-a"


def test_file_qa_keeps_empty_selection_without_constructing_global_service(monkeypatch):
    factory_calls = []
    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: factory_calls.append(kwargs),
        raising=False,
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
    )

    assert pipeline.run(text="question", doc_ids=None) == []
    assert pipeline.run(text="question", doc_ids=[]) == []
    assert factory_calls == []


def test_extra_table_lookup_stays_inside_selected_chunk_ids(monkeypatch):
    cited = RetrievedDocument(
        id_="selected-chunk",
        text="table summary",
        metadata={"file_id": "source-a", "file_name": "guide.md", "page_label": "4"},
        score=0.8,
    )
    service = CapturingKnowledgeService([cited], ["selected-chunk", "selected-table"])

    class ExtraRetriever:
        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return [
                RetrievedDocument(
                    id_="unselected-table",
                    text="unselected source table",
                    metadata={"file_name": "other.md", "page_label": "4"},
                    score=0.7,
                )
            ]

    extra_retriever = ExtraRetriever()
    monkeypatch.setattr(
        "ktem.index.file.pipelines.create_file_knowledge_service",
        lambda **kwargs: service,
        raising=False,
    )
    monkeypatch.setattr(
        "ktem.index.file.pipelines.VectorRetrieval",
        lambda **kwargs: extra_retriever,
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        get_extra_table=True,
    )

    assert pipeline.run(text="question", doc_ids=["source-a"]) == [cited]
    assert len(extra_retriever.calls) == 1
    assert extra_retriever.calls[0]["scope"] == ["selected-chunk", "selected-table"]


def test_agent_factory_global_search_stays_inside_private_user_catalog(tmp_path):
    from ktem.index.file.knowledge_service import create_agent_knowledge_service
    from sqlalchemy import JSON, Column, Integer, String, create_engine
    from sqlalchemy.ext.mutable import MutableDict
    from sqlalchemy.orm import declarative_base, sessionmaker

    base = declarative_base()

    class Source(base):
        __tablename__ = "agent_source"
        id = Column(String, primary_key=True)
        name = Column(String)
        user = Column(String)
        note = Column(MutableDict.as_mutable(JSON))

    class Index(base):
        __tablename__ = "agent_index"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'agent.db'}")
    base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                Source(
                    id="alice",
                    name="Alice.md",
                    user="user-a",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/Alice.md",
                            "document_name": "Alice.md",
                            "entity": {"person": "Alice"},
                        }
                    },
                ),
                Source(
                    id="bob",
                    name="Bob.md",
                    user="user-b",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/Bob.md",
                            "document_name": "Bob.md",
                            "entity": {"person": "Bob"},
                        }
                    },
                ),
            ]
        )
        session.add_all(
            [
                Index(
                    source_id="alice",
                    target_id="alice-chunk",
                    relation_type="document",
                ),
                Index(source_id="bob", target_id="bob-chunk", relation_type="document"),
            ]
        )
        session.commit()

    retriever = CapturingKnowledgeService([], [])

    def run_retriever(*, text, **kwargs):
        return retriever.search(text, **kwargs)

    service = create_agent_knowledge_service(
        Source=Source,
        Index=Index,
        vector_retrieval=run_retriever,
        docstore=object(),
        private=True,
        user_id="user-a",
        session_factory=session_factory,
    )

    assert service.search("unmatched global question") == []
    assert retriever.search_calls[0][1]["scope"] is None
    assert retriever.search_calls[0][1]["fallback_scope"] == ["alice-chunk"]
    assert [
        item["source_id"] for item in service.list("/team") if item["kind"] == "source"
    ] == ["alice"]
