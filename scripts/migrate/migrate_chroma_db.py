import uuid

import chromadb
from ktem.index.models import Index
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


def _init_resource(private: bool = True, id: int = 1):
    """Init schemas. Hard-code"""
    Base = declarative_base()

    if private:
        Source = type(
            "Source",
            (Base,),
            {
                "__tablename__": f"index__{id}__source",
                "__table_args__": (
                    UniqueConstraint("name", "user", name="_name_user_uc"),
                ),
                "id": Column(
                    String,
                    primary_key=True,
                    default=lambda: str(uuid.uuid4()),
                    unique=True,
                ),
                "name": Column(String),
                "path": Column(String),
                "size": Column(Integer, default=0),
                "date_created": Column(
                    DateTime(timezone=True), server_default=func.now()
                ),
                "user": Column(Integer, default=1),
                "note": Column(
                    MutableDict.as_mutable(JSON),  # type: ignore
                    default={},
                ),
            },
        )
    else:
        Source = type(
            "Source",
            (Base,),
            {
                "__tablename__": f"index__{id}__source",
                "id": Column(
                    String,
                    primary_key=True,
                    default=lambda: str(uuid.uuid4()),
                    unique=True,
                ),
                "name": Column(String, unique=True),
                "path": Column(String),
                "size": Column(Integer, default=0),
                "date_created": Column(
                    DateTime(timezone=True), server_default=func.now()
                ),
                "user": Column(Integer, default=1),
                "note": Column(
                    MutableDict.as_mutable(JSON),  # type: ignore
                    default={},
                ),
            },
        )
    Index = type(
        "IndexTable",
        (Base,),
        {
            "__tablename__": f"index__{id}__index",
            "id": Column(Integer, primary_key=True, autoincrement=True),
            "source_id": Column(String),
            "target_id": Column(String),
            "relation_type": Column(String),
            "user": Column(Integer, default=1),
        },
    )

    return {"Source": Source, "Index": Index}


def get_chromadb_collection(
    db_dir: str = "../ktem_app_data/user_data/vectorstore",
    collection_name: str = "index_1",
):
    """Extract collection from chromadb"""
    client = chromadb.PersistentClient(path=db_dir)
    collection = client.get_or_create_collection(collection_name)

    return collection


def update_metadata(metadata, file_id):
    """Update file_id"""
    metadata["file_id"] = file_id
    return metadata


def migrate_chroma_db(
    chroma_db_dir: str, sqlite_path: str, is_private: bool = True, int_index: int = 1
):
    chroma_collection_name = f"index_{int_index}"

    """Update chromadb with metadata.file_id"""
    engine = create_engine(sqlite_path)
    resource = _init_resource(private=is_private, id=int_index)
    print("Load sqlalchemy engine successfully!")

    chroma_db_collection = get_chromadb_collection(
        db_dir=chroma_db_dir, collection_name=chroma_collection_name
    )
    print(
        f"Load chromadb collection: {chroma_collection_name}, "
        f"path: {chroma_db_dir} successfully!"
    )

    # Load docs id of user
    with Session(engine) as session:
        stmt = select(resource["Source"])
        results = session.execute(stmt)
        doc_ids = [r[0].id for r in results.all()]
    print(f"Retrieve n-docs: {len(doc_ids)}")
    print(doc_ids)

    for doc_id in doc_ids:
        print("-")
        # Find corresponding vector ids
        with Session(engine) as session:
            stmt = select(resource["Index"]).where(
                resource["Index"].relation_type == "vector",
                resource["Index"].source_id.in_([doc_id]),
            )
            results = session.execute(stmt)
            vs_ids = [r[0].target_id for r in results.all()]

        print(f"Got {len(vs_ids)} vs_ids for doc {doc_id}")

        # Update file_id
        if len(vs_ids) > 0:
            batch = chroma_db_collection.get(ids=vs_ids, include=["metadatas"])
            batch.update(
                ids=batch["ids"],
                metadatas=[
                    update_metadata(metadata, doc_id) for metadata in batch["metadatas"]
                ],
            )

        # Assert file_id. Skip
        print(f"doc-{doc_id} got updated")


def main(chroma_db_dir: str, sqlite_path: str):
    engine = create_engine(sqlite_path)

    with Session(engine) as session:
        stmt = select(Index)

        results = session.execute(stmt)
        file_indices = [r[0] for r in results.all()]

        for file_index in file_indices:
            _id = file_index.id
            _is_private = file_index.config["private"]

            print(f"Migrating for Index id: {_id}, is_private: {_is_private}")

            migrate_chroma_db(
                chroma_db_dir=chroma_db_dir,
                sqlite_path=sqlite_path,
                is_private=_is_private,
                int_index=_id,
            )


if __name__ == "__main__":
    chrome_db_dir: str = "./vectorstore/kan_db"
    sqlite_path: str = "sqlite:///../ktem_app_data/user_data/sql.db"

    main(chrome_db_dir, sqlite_path)
