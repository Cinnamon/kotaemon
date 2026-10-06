"""SQL adapter tests for the knowledge source catalog."""

from ktem.index.file.knowledge_catalog import KnowledgeCatalog
from sqlalchemy import JSON, Column, Integer, String, create_engine
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Session, declarative_base, sessionmaker


def test_catalog_filters_private_visibility_and_allowed_source_ids(tmp_path):
    base = declarative_base()

    class Source(base):
        __tablename__ = "source"
        id = Column(String, primary_key=True)
        name = Column(String)
        path = Column(String)
        user = Column(String)
        note = Column(MutableDict.as_mutable(JSON))

    class Index(base):
        __tablename__ = "index_relation"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'knowledge.db'}")
    base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def knowledge(path, person):
        return {
            "knowledge": {
                "source_type": "markdown",
                "virtual_path": path,
                "document_name": f"{person}.md",
                "entity": {"person": person},
            }
        }

    with Session(engine) as session:
        session.add_all(
            [
                Source(
                    id="owner",
                    name="Alice.md",
                    path="/tmp/upload-1",
                    user="user-a",
                    note=knowledge("/team/Alice.md", "Alice"),
                ),
                Source(
                    id="other",
                    name="Bob.md",
                    path="/tmp/upload-2",
                    user="user-b",
                    note=knowledge("/team/Bob.md", "Bob"),
                ),
                Source(
                    id="legacy",
                    name="legacy.md",
                    path="/tmp/upload-3",
                    user="user-a",
                    note={"knowledge": "not-a-dict"},
                ),
                Source(
                    id="literal-none",
                    name="literal-none.md",
                    path="/tmp/upload-4",
                    user="user-a",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/literal-none.md",
                            "document_name": "literal-none.md",
                            "entity": {"person": "None"},
                        }
                    },
                ),
                Source(
                    id="missing-person",
                    name="missing-person.md",
                    path="/tmp/upload-5",
                    user="user-a",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/missing-person.md",
                            "document_name": "missing-person.md",
                            "entity": {},
                        }
                    },
                ),
            ]
        )
        session.add_all(
            [
                Index(
                    source_id="owner", target_id="owner-chunk", relation_type="document"
                ),
                Index(
                    source_id="owner", target_id="owner-vector", relation_type="vector"
                ),
                Index(
                    source_id="other", target_id="other-chunk", relation_type="document"
                ),
            ]
        )
        session.commit()

    catalog = KnowledgeCatalog(
        Source,
        Index,
        private=True,
        user_id="user-a",
        session_factory=session_factory,
    )

    sources = catalog.list_sources(allowed_source_ids=["owner", "other", "legacy"])
    assert {item.source_id for item in sources} == {"owner", "legacy"}
    assert catalog.resolve_source_ids(
        path="/team/Alice.md", allowed_source_ids=["owner", "other"]
    ) == ("owner",)
    assert catalog.resolve_source_ids(
        source_type=" MARKDOWN ",
        entity_filters={"person": "alice"},
        allowed_source_ids=["owner", "other"],
    ) == ("owner",)
    assert (
        catalog.resolve_source_ids(
            entity_filters={"person": "Bob"},
            allowed_source_ids=["owner", "other"],
        )
        == ()
    )
    assert catalog.resolve_source_ids(
        entity_filters={"person": "None"},
        allowed_source_ids=["literal-none", "missing-person"],
    ) == ("literal-none",)
    assert (
        catalog.resolve_source_ids(
            allowed_source_ids=[],
        )
        == ()
    )
    assert catalog.chunk_ids(["owner", "other", "missing"]) == {
        "owner": ("owner-chunk",),
    }
    assert catalog.source_ids_for_chunk_ids(
        ["owner-chunk", "owner-vector", "other-chunk"],
        allowed_source_ids=["owner", "other"],
    ) == {"owner-chunk": ("owner",)}

    # The logical path comes from note metadata and never from Source.path.
    owner = next(item for item in sources if item.source_id == "owner")
    assert owner.virtual_path == "/team/Alice.md"
    legacy = next(item for item in sources if item.source_id == "legacy")
    assert legacy.virtual_path is None

    anonymous_catalog = KnowledgeCatalog(
        Source,
        Index,
        private=True,
        user_id=None,
        session_factory=session_factory,
    )
    assert anonymous_catalog.list_sources() == []
    assert anonymous_catalog.chunk_ids(["owner"]) == {}
    assert anonymous_catalog.source_ids_for_chunk_ids(["owner-chunk"]) == {}


def test_public_catalog_still_intersects_explicit_allowlist(tmp_path):
    base = declarative_base()

    class Source(base):
        __tablename__ = "public_source"
        id = Column(String, primary_key=True)
        name = Column(String)
        user = Column(String)
        note = Column(MutableDict.as_mutable(JSON))

    class Index(base):
        __tablename__ = "public_index"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'public.db'}")
    base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with Session(engine) as session:
        session.add_all(
            [
                Source(
                    id="a",
                    name="a.md",
                    user="user-a",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/a.md",
                            "document_name": "a.md",
                            "entity": {},
                        }
                    },
                ),
                Source(
                    id="b",
                    name="b.md",
                    user="user-b",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/b.md",
                            "document_name": "b.md",
                            "entity": {},
                        }
                    },
                ),
            ]
        )
        session.commit()

    catalog = KnowledgeCatalog(
        Source, Index, private=False, user_id="user-a", session_factory=factory
    )

    assert {item.source_id for item in catalog.list_sources()} == {"a", "b"}
    assert [item.source_id for item in catalog.list_sources(["b"])] == ["b"]
