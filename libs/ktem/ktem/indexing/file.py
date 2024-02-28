from __future__ import annotations

import shutil
import warnings
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Optional

from ktem.components import (
    embeddings,
    filestorage_path,
    get_docstore,
    get_vectorstore,
    llms,
)
from ktem.db.models import Index, Source, SourceTargetRelation, engine
from ktem.indexing.base import BaseIndexing, BaseRetriever
from llama_index.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.vector_stores.types import VectorStoreQueryMode
from sqlmodel import Session, select
from theflow.settings import settings

from kotaemon.base import RetrievedDocument
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.indices.ingests import DocumentIngestor
from kotaemon.indices.rankings import BaseReranking, CohereReranking, LLMReranking

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


class DocumentRetrievalPipeline(BaseRetriever):
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
        doc_store=get_docstore(),
        vector_store=get_vectorstore(),
        embedding=embeddings.get_default(),
    )
    reranker: BaseReranking = CohereReranking.withx(
        cohere_api_key=getattr(settings, "COHERE_API_KEY", "")
    ) >> LLMReranking.withx(llm=llms.get_lowest_cost())
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
        kwargs = {}
        if doc_ids:
            with Session(engine) as session:
                stmt = select(Index).where(
                    Index.relation_type == SourceTargetRelation.VECTOR,
                    Index.source_id.in_(doc_ids),  # type: ignore
                )
                results = session.exec(stmt)
                vs_ids = [r.target_id for r in results.all()]

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
        if self.get_from_path("reranker"):
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


class IndexDocumentPipeline(BaseIndexing):
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
            print(
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
        print("Extracted", len(to_index), "files into", len(nodes), "nodes")
        for node in nodes:
            file_path = str(node.metadata["file_path"])
            node.source = file_to_source[file_path].id

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

        print("Finishing persisting the vector and the document into index")
        print(f"{len(nodes)} nodes are indexed")
        return nodes, file_ids

    def get_user_settings(self) -> dict:
        return USER_SETTINGS

    @classmethod
    def get_pipeline(cls, settings) -> "IndexDocumentPipeline":
        """Get the pipeline based on the setting"""
        obj = cls()
        obj.file_ingestor.pdf_mode = settings["index.index_parser"]
        return obj

    def get_retrievers(self, settings, **kwargs) -> list[BaseRetriever]:
        """Get retriever objects associated with the index

        Args:
            settings: the settings of the app
            kwargs: other arguments
        """
        retriever = DocumentRetrievalPipeline(
            get_extra_table=settings["index.prioritize_table"]
        )
        if not settings["index.use_reranking"]:
            retriever.reranker = None  # type: ignore

        kwargs = {
            ".top_k": int(settings["index.num_retrieval"]),
            ".mmr": settings["index.mmr"],
            ".doc_ids": kwargs.get("files", None),
        }
        retriever.set_run(kwargs, temp=True)
        return [retriever]
