from __future__ import annotations

import shutil
from hashlib import sha256
from pathlib import Path

from ktem.components import embeddings, filestorage_path, get_docstore, get_vectorstore
from ktem.db.models import Index, Source, SourceTargetRelation, engine
from ktem.indexing.base import BaseIndex
from ktem.indexing.exceptions import FileExistsError
from kotaemon.indices import VectorIndexing
from kotaemon.indices.ingests import DocumentIngestor
from sqlmodel import Session, select

USER_SETTINGS = {
    "index_parser": {
        "name": "Index parser",
        "value": "normal",
        "choices": [
            ("PDF text parser", "normal"),
            ("Mathpix", "mathpix"),
            ("Advanced ocr", "ocr"),
        ],
        "component": "dropdown",
    },
    "separate_embedding": {
        "name": "Use separate embedding",
        "value": False,
        "choices": [("Yes", True), ("No", False)],
        "component": "dropdown",
    },
    "num_retrieval": {
        "name": "Number of documents to retrieve",
        "value": 3,
        "component": "number",
    },
    "retrieval_mode": {
        "name": "Retrieval mode",
        "value": "vector",
        "choices": ["vector", "text", "hybrid"],
        "component": "dropdown",
    },
    "prioritize_table": {
        "name": "Prioritize table",
        "value": True,
        "choices": [True, False],
        "component": "checkbox",
    },
    "mmr": {
        "name": "Use MMR",
        "value": True,
        "choices": [True, False],
        "component": "checkbox",
    },
    "use_reranking": {
        "name": "Use reranking",
        "value": True,
        "choices": [True, False],
        "component": "checkbox",
    },
}


class IndexDocumentPipeline(BaseIndex):
    """Store the documents and index the content into vector store and doc store

    Args:
        indexing_vector_pipeline: pipeline to index the documents
        file_ingestor: ingestor to ingest the documents
    """

    indexing_vector_pipeline: VectorIndexing = VectorIndexing.withx(
        doc_store=get_docstore(),
        vector_store=get_vectorstore(),
        embedding=embeddings.get_default(),
    )
    file_ingestor: DocumentIngestor = DocumentIngestor.withx()

    def run(
        self,
        file_paths: str | Path | list[str | Path],
        reindex: bool = False,
        **kwargs,  # type: ignore
    ):
        """Index the list of documents

        This function will extract the files, persist the files to storage,
        index the files.

        Args:
            file_paths: list of file paths to index
            reindex: whether to force reindexing the files if they exist

        Returns:
            list of split nodes
        """
        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        to_index: list[str] = []
        file_to_hash: dict[str, str] = {}
        errors = []

        for file_path in file_paths:
            abs_path = str(Path(file_path).resolve())
            with open(abs_path, "rb") as fi:
                file_hash = sha256(fi.read()).hexdigest()

            file_to_hash[abs_path] = file_hash

            with Session(engine) as session:
                statement = select(Source).where(Source.name == Path(abs_path).name)
                item = session.exec(statement).first()

            if item and not reindex:
                errors.append(Path(abs_path).name)
                continue

            to_index.append(abs_path)

        if errors:
            raise FileExistsError(
                "Files already exist. Please rename/remove them or enable reindex.\n"
                f"{errors}"
            )

        # persist the files to storage
        for path in to_index:
            shutil.copy(path, filestorage_path / file_to_hash[path])

        # prepare record info
        file_to_source: dict[str, Source] = {}
        for file_path, file_hash in file_to_hash.items():
            source = Source(path=file_hash, name=Path(file_path).name)
            file_to_source[file_path] = source

        # extract the files
        nodes = self.file_ingestor(to_index)
        for node in nodes:
            file_path = str(node.metadata["file_path"])
            node.source = file_to_source[file_path].id

        # index the files
        self.indexing_vector_pipeline(nodes)

        # persist to the index
        file_ids = []
        with Session(engine) as session:
            for source in file_to_source.values():
                session.add(source)
            session.commit()
            for source in file_to_source.values():
                file_ids.append(source.id)

        with Session(engine) as session:
            for node in nodes:
                index = Index(
                    source_id=node.source,
                    target_id=node.doc_id,
                    relation_type=SourceTargetRelation.DOCUMENT,
                )
                session.add(index)
            for node in nodes:
                index = Index(
                    source_id=node.source,
                    target_id=node.doc_id,
                    relation_type=SourceTargetRelation.VECTOR,
                )
                session.add(index)
            session.commit()

        return nodes, file_ids

    def get_user_settings(self) -> dict:
        return USER_SETTINGS

    @classmethod
    def get_pipeline(cls, setting) -> "IndexDocumentPipeline":
        """Get the pipeline based on the setting"""
        obj = cls()
        obj.file_ingestor.pdf_mode = setting["index.index_parser"]
        return obj
