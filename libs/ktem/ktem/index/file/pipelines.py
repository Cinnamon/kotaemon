from __future__ import annotations

import json
import logging
import shutil
import threading
import time
import warnings
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Generator, Optional, Sequence

import tiktoken
from decouple import config
from ktem.db.models import engine
from ktem.embeddings.manager import embedding_models_manager
from ktem.llms.manager import llms
from ktem.rerankings.manager import reranking_models_manager
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from theflow.settings import settings
from theflow.utils.modules import import_dotted_string

from kotaemon.base import BaseComponent, Document, Node, Param, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorIndexing, VectorRetrieval
from kotaemon.indices.ingests.files import (
    KH_DEFAULT_FILE_EXTRACTORS,
    adobe_reader,
    azure_reader,
    docling_reader,
    paddle_struct_reader,
    paddle_vl_reader,
    unstructured,
    web_reader,
)
from kotaemon.indices.knowledge.chunking.identity import (
    source_version_for_path,
    stamp_chunk_identity,
)
from kotaemon.indices.knowledge.chunking.registry import get_chunk_strategy
from kotaemon.indices.knowledge.metadata import normalize_knowledge_metadata
from kotaemon.indices.knowledge.planning.query_enrichment import QueryEnricher
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.indices.knowledge.retrieval.expansion import (
    ChunkResolver,
    ExpansionPolicy,
    expand_evidence,
)
from kotaemon.indices.knowledge.retrieval.trace import trace_event, trace_scoped
from kotaemon.indices.rankings import BaseReranking, LLMReranking, LLMTrulensScoring
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter

from .base import BaseFileIndexIndexing, BaseFileIndexRetriever
from .knowledge_service import create_file_knowledge_service

logger = logging.getLogger(__name__)
_INDEXING_IDENTITY_METADATA_KEYS = frozenset(
    {"file_id", "document_id", "collection_name", "source_version"}
)


@lru_cache
def dev_settings():
    """Retrieve the developer settings from flowsettings.py"""
    file_extractors = {}

    if hasattr(settings, "FILE_INDEX_PIPELINE_FILE_EXTRACTORS"):
        file_extractors = {
            key: import_dotted_string(value, safe=False)()
            for key, value in settings.FILE_INDEX_PIPELINE_FILE_EXTRACTORS.items()
        }

    chunk_size = None
    if hasattr(settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE"):
        chunk_size = settings.FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE

    chunk_overlap = None
    if hasattr(settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP"):
        chunk_overlap = settings.FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP

    return file_extractors, chunk_size, chunk_overlap


_default_token_func = tiktoken.encoding_for_model("gpt-3.5-turbo").encode


class DocumentRetrievalPipeline(BaseFileIndexRetriever):
    """Retrieve relevant document

    Args:
        vector_retrieval: the retrieval pipeline that return the relevant documents
            given a text query
        reranker: the reranking pipeline that re-rank and filter the retrieved
            documents
        get_extra_table: if True, for each retrieved document, the pipeline will look
            for surrounding tables (e.g. within the page)
        top_k: number of documents to retrieve
        mmr: whether to use mmr to re-rank the documents
    """

    embedding: BaseEmbeddings
    rerankers: Sequence[BaseReranking] = []
    # use LLM to create relevant scores for displaying on UI
    llm_scorer: LLMReranking | None = LLMReranking.withx()
    get_extra_table: bool = False
    mmr: bool = False
    top_k: int = 5
    retrieval_mode: str = "hybrid"
    v3_enabled: bool = False
    candidate_k: int = 20
    max_fused_candidates: int = 40
    query_enrichment: bool = False
    evidence_expansion: bool = False
    query_enricher: Optional[QueryEnricher] = None

    @Node.auto(depends_on=["embedding", "VS", "DS"])
    def vector_retrieval(self) -> VectorRetrieval:
        return VectorRetrieval(
            embedding=self.embedding,
            vector_store=self.VS,
            doc_store=self.DS,
            retrieval_mode=self.retrieval_mode,  # type: ignore
            rerankers=self.rerankers,
        )

    def run(
        self,
        text: str,
        doc_ids: Optional[list[str]] = None,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        """Retrieve document excerpts similar to the text

        Args:
            text: the text to retrieve similar documents
            doc_ids: list of document ids to constraint the retrieval
        """
        # Flatten file-group IDs before passing the explicit UI selection to the
        # knowledge service.
        if doc_ids is not None:
            flatten_doc_ids = []
            for doc_id in doc_ids:
                if doc_id is None:
                    raise ValueError("No document is selected")

                if doc_id.startswith("["):
                    group_ids = json.loads(doc_id)
                    if not isinstance(group_ids, list):
                        raise ValueError("File group selection must contain a list")
                    flatten_doc_ids.extend(group_ids)
                else:
                    flatten_doc_ids.append(doc_id)
            doc_ids = flatten_doc_ids

        print("searching in doc_ids", doc_ids)
        trace = kwargs.get("trace")
        if not doc_ids:
            logger.info(f"Skip retrieval because of no selected files: {self}")
            trace_event(trace, "no_search", reason="empty_ui_selection")
            trace_event(trace, "final_ui", ids=[])
            return []

        vector_retrieval = self.vector_retrieval

        def run_vector_retrieval(**retrieval_kwargs):
            # Keep the file UI's expanded first pass and optional MMR setting
            # while routing Agent/service search through the existing retriever.
            retrieval_kwargs["do_extend"] = True
            if self.mmr:
                retrieval_kwargs["mode"] = VectorStoreQueryMode.MMR
                retrieval_kwargs["mmr_threshold"] = 0.5
            return vector_retrieval(**retrieval_kwargs)

        service = create_file_knowledge_service(
            Source=self.Source,
            Index=self.Index,
            vector_retrieval=run_vector_retrieval,
            docstore=self.DS,
            private=self.private,
            user_id=self.user_id,
        )
        chunk_ids = service.chunk_ids_for_sources(doc_ids)

        # Preserve the caller's exact source allowlist at the service boundary.
        s_time = time.time()
        search_kwargs = {
            "top_k": self.top_k,
            "allowed_source_ids": doc_ids,
            "trace": trace,
        }
        if self.v3_enabled:
            retrieval_policy = RetrievalPolicy(
                enabled=True,
                candidate_k=self.candidate_k,
                max_fused_candidates=self.max_fused_candidates,
            )
            trace_event(
                trace,
                "product_retrieval_config",
                v3_enabled=True,
                candidate_k=self.candidate_k,
                max_fused_candidates=self.max_fused_candidates,
                chunk_seed_k=self.top_k,
                query_enrichment=self.query_enrichment,
                evidence_expansion=self.evidence_expansion,
            )
            search_kwargs["retrieval_policy"] = retrieval_policy
            for key in ("path", "source_types", "filters"):
                if kwargs.get(key) is not None:
                    search_kwargs[key] = kwargs[key]
            if self.query_enrichment:
                enricher = self.query_enricher or QueryEnricher(
                    max_variants=retrieval_policy.max_variants
                )
                search_kwargs["enriched_query"] = enricher.enrich(
                    text, kwargs.get("user_history", ())
                )
        docs = service.search(text, **search_kwargs)

        if self.v3_enabled and self.evidence_expansion and docs:
            allowed_chunk_ids = service.authorized_chunk_ids(
                path=kwargs.get("path"),
                source_types=kwargs.get("source_types"),
                filters=kwargs.get("filters"),
                allowed_source_ids=doc_ids,
            )
            scorer = next(
                (
                    reranker
                    for reranker in self.rerankers
                    if callable(getattr(reranker, "score_pairs", None))
                ),
                None,
            )
            bundle = expand_evidence(
                docs,
                query=text,
                resolver=ChunkResolver(
                    docstore=service.docstore, catalog=service.catalog
                ),
                allowed_chunk_ids=allowed_chunk_ids,
                scorer=scorer,
                policy=ExpansionPolicy(),
            )
            seeds = list(bundle.seeds)
            expansions = list(bundle.expansions)
            for document in seeds:
                document.metadata = {
                    **dict(document.metadata or {}),
                    "knowledge_evidence_role": "seed",
                }
            for document in expansions:
                document.metadata = {
                    **dict(document.metadata or {}),
                    "knowledge_evidence_role": "expansion",
                }
            docs = seeds + expansions
            trace_event(
                trace,
                "evidence_expansion",
                decisions=list(bundle.decisions),
                seed_ids=[document.doc_id for document in seeds],
                expanded_ids=[document.doc_id for document in expansions],
                authorized_chunk_count=len(allowed_chunk_ids),
            )
        print("retrieval step took", time.time() - s_time)

        if not self.get_extra_table:
            trace_event(
                trace,
                "final_ui",
                ids=[doc.doc_id for doc in docs],
            )
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
            try:
                extra_trace = trace_scoped(trace, query_kind="extra_table")
                extra_kwargs = dict(
                    text="",
                    top_k=50,
                    scope=chunk_ids,
                    fallback_scope=chunk_ids,
                    where=queries[0] if len(queries) == 1 else {"$or": queries},
                )
                if trace is not None:
                    extra_kwargs["trace"] = extra_trace
                extra_docs = self.vector_retrieval(**extra_kwargs)
                for doc in extra_docs:
                    if doc.doc_id in chunk_ids and doc.doc_id not in retrieved_id:
                        docs.append(doc)
            except Exception:
                print("Error retrieving additional tables")

        trace_event(trace, "final_ui", ids=[doc.doc_id for doc in docs])
        return docs

    def generate_relevant_scores(
        self, query: str, documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        docs = (
            documents
            if not self.llm_scorer
            else self.llm_scorer(documents=documents, query=query)
        )
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
            "v3_enabled": {
                "name": "Enable v3 retrieval",
                "value": False,
                "component": "checkbox",
            },
            "candidate_k": {
                "name": "V3 candidates per route",
                "value": 20,
                "component": "number",
            },
            "max_fused_candidates": {
                "name": "V3 maximum fused candidates",
                "value": 40,
                "component": "number",
            },
            "query_enrichment": {
                "name": "Enable query enrichment",
                "value": False,
                "component": "checkbox",
            },
            "evidence_expansion": {
                "name": "Enable authorized evidence expansion",
                "value": False,
                "component": "checkbox",
            },
            "reranking_llm": {
                "name": "LLM for relevant scoring",
                "value": reranking_llm,
                "component": "dropdown",
                "choices": reranking_llm_choices,
                "special_type": "llm",
            },
            "num_retrieval": {
                "name": "Number of document chunks to retrieve",
                "value": 10,
                "component": "number",
            },
            "retrieval_mode": {
                "name": "Retrieval mode",
                "value": "hybrid",
                "choices": ["vector", "text", "hybrid"],
                "component": "dropdown",
            },
            "prioritize_table": {
                "name": "Prioritize table",
                "value": False,
                "choices": [True, False],
                "component": "checkbox",
            },
            "mmr": {
                "name": "Use MMR",
                "value": False,
                "choices": [True, False],
                "component": "checkbox",
            },
            "use_reranking": {
                "name": "Use reranking",
                "value": True,
                "choices": [True, False],
                "component": "checkbox",
            },
            "use_llm_reranking": {
                "name": "Use LLM relevant scoring",
                "value": not config("USE_LOW_LLM_REQUESTS", default=False, cast=bool),
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
        use_llm_reranking = user_settings.get("use_llm_reranking", False)

        retriever = cls(
            get_extra_table=user_settings["prioritize_table"],
            top_k=user_settings["num_retrieval"],
            mmr=user_settings["mmr"],
            embedding=embedding_models_manager[
                index_settings.get(
                    "embedding", embedding_models_manager.get_default_name()
                )
            ],
            retrieval_mode=user_settings["retrieval_mode"],
            v3_enabled=user_settings.get("v3_enabled", False),
            candidate_k=user_settings.get("candidate_k", 20),
            max_fused_candidates=user_settings.get("max_fused_candidates", 40),
            query_enrichment=user_settings.get("query_enrichment", False),
            evidence_expansion=user_settings.get("evidence_expansion", False),
            llm_scorer=(LLMTrulensScoring() if use_llm_reranking else None),
            rerankers=[
                reranking_models_manager[
                    index_settings.get(
                        "reranking", reranking_models_manager.get_default_name()
                    )
                ]
            ],
        )
        if not user_settings["use_reranking"]:
            retriever.rerankers = []  # type: ignore

        for reranker in retriever.rerankers:
            if isinstance(reranker, LLMReranking):
                reranker.llm = llms.get(
                    user_settings["reranking_llm"], llms.get_default()
                )

        if retriever.llm_scorer:
            retriever.llm_scorer.llm = llms.get(
                user_settings["reranking_llm"], llms.get_default()
            )

        kwargs = {".doc_ids": selected}
        retriever.set_run(kwargs, temp=False)
        return retriever


class IndexPipeline(BaseComponent):
    """Index a single file"""

    loader: BaseReader
    splitter: BaseSplitter | None
    chunk_batch_size: int = 200

    Source = Param(help="The SQLAlchemy Source table")
    Index = Param(help="The SQLAlchemy Index table")
    VS = Param(help="The VectorStore")
    DS = Param(help="The DocStore")
    FSPath = Param(help="The file storage path")
    user_id = Param(help="The user id")
    collection_name: str = "default"
    private: bool = False
    run_embedding_in_thread: bool = False
    embedding: BaseEmbeddings

    @Node.auto(depends_on=["Source", "Index", "embedding"])
    def vector_indexing(self) -> VectorIndexing:
        return VectorIndexing(
            vector_store=self.VS, doc_store=self.DS, embedding=self.embedding
        )

    def _split_and_normalize_text_docs(self, documents):
        output = []
        for parser_unit_ordinal, document in enumerate(documents):
            document.metadata = normalize_knowledge_metadata(document)
            document.metadata["_parser_unit_ordinal"] = parser_unit_ordinal
            if self.splitter:
                strategy = get_chunk_strategy(
                    document.metadata["source_type"], self.splitter
                )
                chunks = strategy.split(document)
            else:
                chunks = [document]
            source_version = document.metadata.get("source_version")
            if source_version:
                chunks = stamp_chunk_identity(
                    document, chunks, source_version=source_version
                )
            else:
                for chunk in chunks:
                    chunk.metadata = normalize_knowledge_metadata(chunk)
                    for key in (
                        "_parser_unit_ordinal",
                        "_semantic_unit_group_id",
                        "source_unit_text",
                    ):
                        chunk.metadata.pop(key, None)
            document.metadata.pop("_parser_unit_ordinal", None)
            output.extend(chunks)
        return output

    def handle_docs(self, docs, file_id, file_name) -> Generator[Document, None, int]:
        s_time = time.time()
        text_docs = []
        non_text_docs = []
        thumbnail_docs = []

        for doc in docs:
            doc_type = doc.metadata.get("type", "text")
            if doc_type == "text":
                text_docs.append(doc)
            elif doc_type == "thumbnail":
                thumbnail_docs.append(doc)
            else:
                non_text_docs.append(doc)

        print(f"Got {len(thumbnail_docs)} page thumbnails")
        page_label_to_thumbnail = {
            doc.metadata["page_label"]: doc.doc_id for doc in thumbnail_docs
        }

        all_chunks = self._split_and_normalize_text_docs(text_docs)
        for document in non_text_docs + thumbnail_docs:
            document.metadata = normalize_knowledge_metadata(document)

        # add the thumbnails doc_id to the chunks
        for chunk in all_chunks:
            page_label = chunk.metadata.get("page_label", None)
            if page_label and page_label in page_label_to_thumbnail:
                chunk.metadata["thumbnail_doc_id"] = page_label_to_thumbnail[page_label]

        to_index_chunks = all_chunks + non_text_docs + thumbnail_docs

        # add to doc store
        chunks = []
        n_chunks = 0
        chunk_size = self.chunk_batch_size * 4
        for start_idx in range(0, len(to_index_chunks), chunk_size):
            chunks = to_index_chunks[start_idx : start_idx + chunk_size]
            self.handle_chunks_docstore(chunks, file_id)
            n_chunks += len(chunks)
            yield Document(
                f" => [{file_name}] Processed {n_chunks} chunks",
                channel="debug",
            )

        def insert_chunks_to_vectorstore():
            chunks = []
            n_chunks = 0
            chunk_size = self.chunk_batch_size
            for start_idx in range(0, len(to_index_chunks), chunk_size):
                chunks = to_index_chunks[start_idx : start_idx + chunk_size]
                self.handle_chunks_vectorstore(chunks, file_id)
                n_chunks += len(chunks)
                if self.VS:
                    yield Document(
                        f" => [{file_name}] Created embedding for {n_chunks} chunks",
                        channel="debug",
                    )

        # run vector indexing in thread if specified
        if self.run_embedding_in_thread:
            print("Running embedding in thread")
            threading.Thread(
                target=lambda: list(insert_chunks_to_vectorstore())
            ).start()
        else:
            yield from insert_chunks_to_vectorstore()

        print("indexing step took", time.time() - s_time)
        return n_chunks

    def handle_chunks_docstore(self, chunks, file_id):
        """Run chunks"""
        # run embedding, add to both vector store and doc store
        self.vector_indexing.add_to_docstore(chunks)

        # record in the index
        with Session(engine) as session:
            nodes = []
            for chunk in chunks:
                nodes.append(
                    self.Index(
                        source_id=file_id,
                        target_id=chunk.doc_id,
                        relation_type="document",
                    )
                )
            session.add_all(nodes)
            session.commit()

    def handle_chunks_vectorstore(self, chunks, file_id):
        """Run chunks"""
        # run embedding, add to both vector store and doc store
        self.vector_indexing.add_to_vectorstore(chunks)
        self.vector_indexing.write_chunk_to_file(chunks)

        if self.VS:
            # record in the index
            with Session(engine) as session:
                nodes = []
                for chunk in chunks:
                    nodes.append(
                        self.Index(
                            source_id=file_id,
                            target_id=chunk.doc_id,
                            relation_type="vector",
                        )
                    )
                session.add_all(nodes)
                session.commit()

    def get_id_if_exists(self, file_path: str | Path) -> Optional[str]:
        """Check if the file is already indexed

        Args:
            file_path: the path to the file

        Returns:
            the file id if the file is indexed, otherwise None
        """
        file_name = file_path.name if isinstance(file_path, Path) else file_path
        if self.private:
            cond: tuple = (
                self.Source.name == file_name,
                self.Source.user == self.user_id,
            )
        else:
            cond = (self.Source.name == file_name,)

        with Session(engine) as session:
            stmt = select(self.Source).where(*cond)
            item = session.execute(stmt).first()
            if item:
                return item[0].id

        return None

    def store_url(self, url: str) -> str:
        """Store URL into the database and storage, return the file id

        Args:
            url: the URL

        Returns:
            the file id
        """
        file_hash = sha256(url.encode()).hexdigest()
        source = self.Source(
            name=url,
            path=file_hash,
            size=0,
            user=self.user_id,  # type: ignore
        )
        with Session(engine) as session:
            session.add(source)
            session.commit()
            file_id = source.id

        return file_id

    def store_file(self, file_path: Path) -> str:
        """Store file into the database and storage, return the file id

        Args:
            file_path: the path to the file

        Returns:
            the file id
        """
        file_hash = source_version_for_path(file_path)

        shutil.copy(file_path, self.FSPath / file_hash)
        source = self.Source(
            name=file_path.name,
            path=file_hash,
            size=file_path.stat().st_size,
            user=self.user_id,  # type: ignore
        )
        with Session(engine) as session:
            session.add(source)
            session.commit()
            file_id = source.id

        return file_id

    def _source_version(self, file_id: str, file_path: str | Path) -> str | None:
        """Return an upload-byte hash; URL locators do not identify content bytes."""
        if not isinstance(file_path, Path):
            return None
        path_column = getattr(self.Source, "path", None)
        stored_path = None
        if path_column is not None:
            with Session(engine) as session:
                stmt = select(path_column).where(self.Source.id == file_id)
                stored_path = session.execute(stmt).scalar_one_or_none()
        if isinstance(stored_path, str) and len(stored_path) == 64:
            try:
                int(stored_path, 16)
                return stored_path.lower()
            except ValueError:
                pass
        return source_version_for_path(file_path)

    def finish(
        self,
        file_id: str,
        file_path: str | Path,
        knowledge_metadata: dict | None = None,
        source_version: str | None = None,
    ) -> str:
        """Finish the indexing"""
        with Session(engine) as session:
            stmt = select(self.Source).where(self.Source.id == file_id)
            result = session.execute(stmt).first()
            if not result:
                return file_id

            item = result[0]
            note = dict(item.note or {})

            # populate the number of tokens
            doc_ids_stmt = select(self.Index.target_id).where(
                self.Index.source_id == file_id,
                self.Index.relation_type == "document",
            )
            doc_ids = [_[0] for _ in session.execute(doc_ids_stmt)]
            token_func = self.get_token_func()
            if doc_ids and token_func:
                docs = self.DS.get(doc_ids)
                note["tokens"] = sum([len(token_func(doc.text)) for doc in docs])

            # populate the note
            note["loader"] = self.get_from_path("loader").__class__.__name__
            file_name = file_path.name if isinstance(file_path, Path) else file_path
            resolved_source_version = (
                source_version
                if source_version is not None
                else self._source_version(file_id, file_path)
            )
            normalized_metadata = {
                "file_id": file_id,
                "file_name": file_name,
                **(knowledge_metadata or {}),
            }
            normalized_metadata.pop("source_version", None)
            if resolved_source_version is not None:
                normalized_metadata["source_version"] = resolved_source_version
            normalized = normalize_knowledge_metadata(
                Document(text="", metadata=normalized_metadata)
            )
            knowledge = dict(note.get("knowledge") or {})
            knowledge.pop("source_version", None)
            knowledge_keys = [
                "source_type",
                "virtual_path",
                "document_name",
                "entity",
            ]
            if resolved_source_version is not None:
                knowledge_keys.append("source_version")
            knowledge.update({key: normalized[key] for key in knowledge_keys})
            note["knowledge"] = knowledge
            item.note = note

            session.add(item)
            session.commit()

        return file_id

    def get_token_func(self):
        """Get the token function for calculating the number of tokens"""
        return _default_token_func

    def delete_file(self, file_id: str):
        """Delete a file from the db, including its chunks in docstore and vectorstore

        Args:
            file_id: the file id
        """
        with Session(engine) as session:
            session.execute(delete(self.Source).where(self.Source.id == file_id))
            vs_ids, ds_ids = [], []
            index = session.execute(
                select(self.Index).where(self.Index.source_id == file_id)
            ).all()
            for each in index:
                if each[0].relation_type == "vector":
                    vs_ids.append(each[0].target_id)
                elif each[0].relation_type == "document":
                    ds_ids.append(each[0].target_id)
                session.delete(each[0])
            session.commit()

        if vs_ids and self.VS:
            self.VS.delete(vs_ids)
        if ds_ids:
            self.DS.delete(ds_ids)

    def run(
        self, file_path: str | Path, reindex: bool, **kwargs
    ) -> tuple[str, list[Document]]:
        raise NotImplementedError

    def stream(
        self,
        file_path: str | Path,
        reindex: bool = False,
        knowledge_metadata: dict | None = None,
        **kwargs,
    ) -> Generator[Document, None, tuple[str, list[Document]]]:
        reserved_metadata = _INDEXING_IDENTITY_METADATA_KEYS.intersection(
            knowledge_metadata or {}
        )
        if reserved_metadata:
            raise ValueError(
                "knowledge_metadata cannot override indexing-owned identity fields: "
                + ", ".join(sorted(reserved_metadata))
            )

        # check if the file is already indexed
        if isinstance(file_path, Path):
            file_path = file_path.resolve()

        file_id = self.get_id_if_exists(file_path)

        if isinstance(file_path, Path):
            if file_id is not None:
                if not reindex:
                    raise ValueError(
                        f"File {file_path.name} already indexed. Please rerun with "
                        "reindex=True to force reindexing."
                    )
                else:
                    # remove the existing records
                    yield Document(
                        f" => Removing old {file_path.name}", channel="debug"
                    )
                    self.delete_file(file_id)
                    file_id = self.store_file(file_path)
            else:
                # add record to db
                file_id = self.store_file(file_path)
        else:
            if file_id is not None:
                raise ValueError(f"URL {file_path} already indexed.")
            else:
                # add record to db
                file_id = self.store_url(file_path)

        # extract the file
        if isinstance(file_path, Path):
            extra_info = default_file_metadata_func(str(file_path))
            file_name = file_path.name
        else:
            extra_info = {"file_name": file_path}
            file_name = file_path

        extra_info["file_id"] = file_id
        extra_info["collection_name"] = self.collection_name
        extra_info.update(knowledge_metadata or {})
        source_version = self._source_version(file_id, file_path)
        if source_version is not None:
            extra_info["source_version"] = source_version

        yield Document(f" => Converting {file_name} to text", channel="debug")
        docs = self.loader.load_data(file_path, extra_info=extra_info)
        for document in docs:
            document.metadata = dict(document.metadata or {})
            if source_version is None:
                document.metadata.pop("source_version", None)
            else:
                document.metadata["source_version"] = source_version
        yield Document(f" => Converted {file_name} to text", channel="debug")
        yield from self.handle_docs(docs, file_id, file_name)

        self.finish(
            file_id,
            file_path,
            knowledge_metadata=knowledge_metadata,
            source_version=source_version,
        )

        yield Document(f" => Finished indexing {file_name}", channel="debug")
        return file_id, docs


class IndexDocumentPipeline(BaseFileIndexIndexing):
    """Index the file. Decide which pipeline based on the file type.

    This method is essentially a factory to decide which indexing pipeline to use.

    We can decide the pipeline programmatically, and/or automatically based on an LLM.
    If we based on the LLM, essentially we will log the LLM thought process in a file,
    and then during the indexing, we will read that file to decide which pipeline
    to use, and then log the operation in that file. Overtime, the LLM can learn to
    decide which pipeline should be used.
    """

    reader_mode: str = Param("default", help="The reader mode")
    embedding: BaseEmbeddings
    run_embedding_in_thread: bool = False

    @Param.auto(depends_on="reader_mode")
    def readers(self):
        readers = deepcopy(KH_DEFAULT_FILE_EXTRACTORS)
        print("reader_mode", self.reader_mode)
        if self.reader_mode == "adobe":
            readers[".pdf"] = adobe_reader
        elif self.reader_mode == "azure-di":
            readers[".pdf"] = azure_reader
        elif self.reader_mode == "docling":
            readers[".pdf"] = docling_reader
        elif self.reader_mode == "paddle-struct":
            readers.update(
                {
                    ".pdf": paddle_struct_reader,
                    ".png": paddle_struct_reader,
                    ".jpeg": paddle_struct_reader,
                    ".jpg": paddle_struct_reader,
                    ".tiff": paddle_struct_reader,
                    ".tif": paddle_struct_reader,
                }
            )
        elif self.reader_mode == "paddle-vl":
            readers.update(
                {
                    ".pdf": paddle_vl_reader,
                    ".png": paddle_vl_reader,
                    ".jpeg": paddle_vl_reader,
                    ".jpg": paddle_vl_reader,
                    ".tiff": paddle_vl_reader,
                    ".tif": paddle_vl_reader,
                }
            )

        dev_readers, _, _ = dev_settings()
        readers.update(dev_readers)

        return readers

    @classmethod
    def get_user_settings(cls):
        return {
            "reader_mode": {
                "name": "File loader",
                "value": "default",
                "choices": [
                    ("Default (open-source)", "default"),
                    ("Adobe API (figure+table extraction)", "adobe"),
                    (
                        "Azure AI Document Intelligence (figure+table extraction)",
                        "azure-di",
                    ),
                    ("Docling (figure+table extraction)", "docling"),
                    (
                        "PaddleOCR PPStructureV3 (table+figure extraction)",
                        "paddle-struct",
                    ),
                    ("PaddleOCR-VL (VLM document parsing)", "paddle-vl"),
                ],
                "component": "dropdown",
            },
        }

    @classmethod
    def get_pipeline(cls, user_settings, index_settings) -> BaseFileIndexIndexing:
        use_quick_index_mode = user_settings.get("quick_index_mode", False)
        print("use_quick_index_mode", use_quick_index_mode)
        obj = cls(
            embedding=embedding_models_manager[
                index_settings.get(
                    "embedding", embedding_models_manager.get_default_name()
                )
            ],
            run_embedding_in_thread=use_quick_index_mode,
            reader_mode=user_settings.get("reader_mode", "default"),
        )
        return obj

    def is_url(self, file_path: str | Path) -> bool:
        return isinstance(file_path, str) and (
            file_path.startswith("http://") or file_path.startswith("https://")
        )

    def route(self, file_path: str | Path) -> IndexPipeline:
        """Decide the pipeline based on the file type

        Can subclass this method for a more elaborate pipeline routing strategy.
        """

        _, dev_chunk_size, dev_chunk_overlap = dev_settings()

        chunk_size = self.chunk_size or dev_chunk_size
        chunk_overlap = self.chunk_overlap or dev_chunk_overlap

        # check if file_path is a URL
        if self.is_url(file_path):
            reader = web_reader
        else:
            assert isinstance(file_path, Path)
            ext = file_path.suffix.lower()
            reader = self.readers.get(ext, unstructured)
            if reader is None:
                raise NotImplementedError(
                    f"No supported pipeline to index {file_path.name}. Please specify "
                    "the suitable pipeline for this file type in the settings."
                )

        print(f"Chunk size: {chunk_size}, chunk overlap: {chunk_overlap}")

        print("Using reader", reader)
        pipeline: IndexPipeline = IndexPipeline(
            loader=reader,
            splitter=TokenSplitter(
                chunk_size=chunk_size or 1024,
                chunk_overlap=chunk_overlap or 256,
                separator="\n\n",
                backup_separators=["\n", ".", "\u200b"],
            ),
            run_embedding_in_thread=self.run_embedding_in_thread,
            Source=self.Source,
            Index=self.Index,
            VS=self.VS,
            DS=self.DS,
            FSPath=self.FSPath,
            user_id=self.user_id,
            private=self.private,
            embedding=self.embedding,
        )

        return pipeline

    def run(
        self, file_paths: str | Path | list[str | Path], *args, **kwargs
    ) -> tuple[list[str | None], list[str | None]]:
        raise NotImplementedError

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        """Return a list of indexed file ids, and a list of errors"""
        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        metadata_by_path = kwargs.pop("knowledge_metadata_by_path", {}) or {}

        file_ids: list[str | None] = []
        errors: list[str | None] = []
        all_docs = []

        n_files = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            original_path = file_path
            knowledge_metadata = metadata_by_path.get(original_path)
            if knowledge_metadata is None:
                knowledge_metadata = metadata_by_path.get(str(original_path))
            if self.is_url(file_path):
                file_name = file_path
            else:
                file_path = Path(file_path)
                file_name = file_path.name

            yield Document(
                content=f"Indexing [{idx + 1}/{n_files}]: {file_name}",
                channel="debug",
            )

            try:
                pipeline = self.route(file_path)
                file_id, docs = yield from pipeline.stream(
                    file_path,
                    reindex=reindex,
                    knowledge_metadata=knowledge_metadata,
                    **kwargs,
                )
                all_docs.extend(docs)
                file_ids.append(file_id)
                errors.append(None)
                yield Document(
                    content={
                        "file_path": file_path,
                        "file_name": file_name,
                        "status": "success",
                    },
                    channel="index",
                )
            except Exception as e:
                logger.exception(e)
                file_ids.append(None)
                errors.append(str(e))
                yield Document(
                    content={
                        "file_path": file_path,
                        "file_name": file_name,
                        "status": "failed",
                        "message": str(e),
                    },
                    channel="index",
                )

        return file_ids, errors, all_docs
