from __future__ import annotations

import logging
import shutil
import warnings
from collections import defaultdict
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Optional

from ktem.components import embeddings, filestorage_path
from ktem.db.models import engine
from llama_index.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.vector_stores.types import VectorStoreQueryMode
from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings
from theflow.utils.modules import import_dotted_string

from kotaemon.base import RetrievedDocument
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.indices.ingests import DocumentIngestor
from kotaemon.indices.rankings import BaseReranking

from .base import BaseFileIndexIndexing, BaseFileIndexRetriever

logger = logging.getLogger(__name__)


@lru_cache
def dev_settings():
    """Retrieve the developer settings from flowsettings.py"""
    file_extractors = {}

    if hasattr(settings, "FILE_INDEX_PIPELINE_FILE_EXTRACTORS"):
        file_extractors = {
            key: import_dotted_string(value, safe=False)
            for key, value in settings.FILE_INDEX_PIPELINE_FILE_EXTRACTORS.items()
        }

    chunk_size = None
    if hasattr(settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE"):
        chunk_size = settings.FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE

    chunk_overlap = None
    if hasattr(settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP"):
        chunk_overlap = settings.FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP

    return file_extractors, chunk_size, chunk_overlap


class DocumentRetrievalPipeline(BaseFileIndexRetriever):
    """Retrieve relevant document

    Args:
        vector_retrieval: the retrieval pipeline that return the relevant documents
            given a text query
        reranker: the reranking pipeline that re-rank and filter the retrieved
            documents
        get_extra_table: if True, for each retrieved document, the pipeline will look
            for surrounding tables (e.g. within the page)
    """

    vector_retrieval: VectorRetrieval = VectorRetrieval.withx(
        embedding=embeddings.get_default(),
    )
    reranker: BaseReranking
    get_extra_table: bool = False

    def run(
        self,
        text: str,
        top_k: int = 5,
        mmr: bool = False,
        doc_ids: Optional[list[str]] = None,
    ) -> list[RetrievedDocument]:
        """Retrieve document excerpts similar to the text

        Args:
            text: the text to retrieve similar documents
            top_k: number of documents to retrieve
            mmr: whether to use mmr to re-rank the documents
            doc_ids: list of document ids to constraint the retrieval
        """
        Index = self._Index

        kwargs = {}
        if doc_ids:
            with Session(engine) as session:
                stmt = select(Index).where(
                    Index.relation_type == "vector",
                    Index.source_id.in_(doc_ids),  # type: ignore
                )
                results = session.execute(stmt)
                vs_ids = [r[0].target_id for r in results.all()]

            kwargs["filters"] = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="doc_id",
                        value=vs_id,
                        operator=FilterOperator.EQ,
                    )
                    for vs_id in vs_ids
                ],
                condition=FilterCondition.OR,
            )

        if mmr:
            # TODO: double check that llama-index MMR works correctly
            kwargs["mode"] = VectorStoreQueryMode.MMR
            kwargs["mmr_threshold"] = 0.5

        # rerank
        docs = self.vector_retrieval(text=text, top_k=top_k, **kwargs)
        if docs and self.get_from_path("reranker"):
            docs = self.reranker(docs, query=text)

        if not self.get_extra_table:
            return docs

        # retrieve extra nodes relate to table
        table_pages = defaultdict(list)
        retrieved_id = set([doc.doc_id for doc in docs])
        for doc in docs:
            if "page_label" not in doc.metadata:
                continue
            if "file_name" not in doc.metadata:
                warnings.warn(
                    "file_name not in metadata while page_label is in metadata: "
                    f"{doc.metadata}"
                )
            table_pages[doc.metadata["file_name"]].append(doc.metadata["page_label"])

        queries: list[dict] = [
            {"$and": [{"file_name": {"$eq": fn}}, {"page_label": {"$in": pls}}]}
            for fn, pls in table_pages.items()
        ]
        if queries:
            extra_docs = self.vector_retrieval(
                text="",
                top_k=50,
                where=queries[0] if len(queries) == 1 else {"$or": queries},
            )
            for doc in extra_docs:
                if doc.doc_id not in retrieved_id:
                    docs.append(doc)

        return docs

    @classmethod
    def get_user_settings(cls) -> dict:
        from ktem.llms.manager import llms

        try:
            reranking_llm = llms.get_default_name()
            reranking_llm_choices = list(llms.options().keys())
        except Exception as e:
            logger.error(e)
            reranking_llm = None
            reranking_llm_choices = []

        return {
            "reranking_llm": {
                "name": "LLM for reranking",
                "value": reranking_llm,
                "component": "dropdown",
                "choices": reranking_llm_choices,
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
                "value": False,
                "choices": [True, False],
                "component": "checkbox",
            },
        }

    @classmethod
    def get_pipeline(cls, user_settings, index_settings, selected):
        """Get retriever objects associated with the index

        Args:
            settings: the settings of the app
            kwargs: other arguments
        """
        retriever = cls(
            get_extra_table=user_settings["prioritize_table"],
            reranker=user_settings["reranking_llm"],
        )
        if not user_settings["use_reranking"]:
            retriever.reranker = None  # type: ignore

        kwargs = {
            ".top_k": int(user_settings["num_retrieval"]),
            ".mmr": user_settings["mmr"],
            ".doc_ids": selected,
        }
        retriever.set_run(kwargs, temp=True)
        return retriever

    def set_resources(self, resources: dict):
        super().set_resources(resources)
        self.vector_retrieval.vector_store = self._VS
        self.vector_retrieval.doc_store = self._DS


class IndexDocumentPipeline(BaseFileIndexIndexing):
    """Store the documents and index the content into vector store and doc store

    Args:
        indexing_vector_pipeline: pipeline to index the documents
        file_ingestor: ingestor to ingest the documents
    """

    indexing_vector_pipeline: VectorIndexing = VectorIndexing.withx(
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
        Source = self._Source
        Index = self._Index

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
                item = session.execute(statement).first()

                if item and not reindex:
                    errors.append(Path(abs_path).name)
                    continue

            to_index.append(abs_path)

        if errors:
            print(
                "Files already exist. Please rename/remove them or enable reindex.\n"
                f"{errors}"
            )

        if not to_index:
            return [], []

        # persist the files to storage
        for path in to_index:
            shutil.copy(path, filestorage_path / file_to_hash[path])

        # prepare record info
        file_to_source: dict = {}
        for file_path, file_hash in file_to_hash.items():
            source = Source(
                name=Path(file_path).name,
                path=file_hash,
                size=Path(file_path).stat().st_size,
            )
            file_to_source[file_path] = source

        # extract the files
        nodes = self.file_ingestor(to_index)
        print("Extracted", len(to_index), "files into", len(nodes), "nodes")

        # index the files
        print("Indexing the files into vector store")
        self.indexing_vector_pipeline(nodes)
        print("Finishing indexing the files into vector store")

        # persist to the index
        print("Persisting the vector and the document into index")
        file_ids = []
        with Session(engine) as session:
            for source in file_to_source.values():
                session.add(source)
            session.commit()
            for source in file_to_source.values():
                file_ids.append(source.id)

            for node in nodes:
                file_path = str(node.metadata["file_path"])
                node.source = str(file_to_source[file_path].id)
                file_to_source[file_path].text_length += len(node.text)

            session.flush()
            session.commit()

        with Session(engine) as session:
            for node in nodes:
                index = Index(
                    source_id=node.source,
                    target_id=node.doc_id,
                    relation_type="document",
                )
                session.add(index)
            for node in nodes:
                index = Index(
                    source_id=node.source,
                    target_id=node.doc_id,
                    relation_type="vector",
                )
                session.add(index)
            session.commit()

        print("Finishing persisting the vector and the document into index")
        print(f"{len(nodes)} nodes are indexed")
        return nodes, file_ids

    @classmethod
    def get_user_settings(cls) -> dict:
        return {
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
        }

    @classmethod
    def get_pipeline(cls, user_settings, index_settings) -> "IndexDocumentPipeline":
        """Get the pipeline based on the setting"""
        obj = cls()
        obj.file_ingestor.pdf_mode = user_settings["index_parser"]

        file_extractors, chunk_size, chunk_overlap = dev_settings()
        if file_extractors:
            obj.file_ingestor.override_file_extractors = file_extractors
        if chunk_size:
            obj.file_ingestor.text_splitter.chunk_size = chunk_size
        if chunk_overlap:
            obj.file_ingestor.text_splitter.chunk_overlap = chunk_overlap

        return obj

    def set_resources(self, resources: dict):
        super().set_resources(resources)
        self.indexing_vector_pipeline.vector_store = self._VS
        self.indexing_vector_pipeline.doc_store = self._DS
