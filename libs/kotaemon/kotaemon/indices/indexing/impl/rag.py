from __future__ import annotations

from dataclasses import dataclass
import logging
import shutil
import threading
import time
from copy import deepcopy
from functools import cached_property, lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Generator, Optional

import tiktoken
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.file.base import default_file_metadata_func
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Session
from theflow.settings import settings
from kotaemon.base import Document
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.indexing.base import BaseIndexing
from kotaemon.indices.vectorindex import VectorIndexing
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
from kotaemon.indices.splitters import BaseSplitter, TokenSplitter
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

logger = logging.getLogger(__name__)

# Wire app-level config into reader singletons at import time.
_vlm_endpoint = getattr(settings, "KH_VLM_ENDPOINT", "")
_markdown_output_dir = getattr(settings, "KH_MARKDOWN_OUTPUT_DIR", None)
adobe_reader.vlm_endpoint = _vlm_endpoint
azure_reader.vlm_endpoint = _vlm_endpoint
docling_reader.vlm_endpoint = _vlm_endpoint
azure_reader.cache_dir = _markdown_output_dir
_mhtml_reader = KH_DEFAULT_FILE_EXTRACTORS.get(".mhtml")
if _mhtml_reader is not None and hasattr(_mhtml_reader, "cache_dir"):
    _mhtml_reader.cache_dir = _markdown_output_dir


def _load_reader(dotted: str) -> type:
    from kotaemon.loaders import (
        AdobeReader,
        AzureAIDocumentIntelligenceLoader,
        DoclingReader,
        HtmlReader,
        OCRReader,
        TxtReader,
        UnstructuredReader,
        WebReader,
    )

    registry = {
        "kotaemon.loaders.AdobeReader": AdobeReader,
        "kotaemon.loaders.AzureAIDocumentIntelligenceLoader": (
            AzureAIDocumentIntelligenceLoader
        ),
        "kotaemon.loaders.DoclingReader": DoclingReader,
        "kotaemon.loaders.HtmlReader": HtmlReader,
        "kotaemon.loaders.OCRReader": OCRReader,
        "kotaemon.loaders.TxtReader": TxtReader,
        "kotaemon.loaders.UnstructuredReader": UnstructuredReader,
        "kotaemon.loaders.WebReader": WebReader,
    }
    if dotted not in registry:
        raise ValueError(f"Unknown reader: {dotted!r}")
    return registry[dotted]


@lru_cache
def dev_settings() -> tuple:
    """Retrieve developer-level overrides from flowsettings.py."""
    file_extractors = {}
    if hasattr(settings, "FILE_INDEX_PIPELINE_FILE_EXTRACTORS"):
        file_extractors = {
            key: _load_reader(value)()
            for key, value in settings.FILE_INDEX_PIPELINE_FILE_EXTRACTORS.items()
        }

    chunk_size = getattr(settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_SIZE", None)
    chunk_overlap = getattr(
        settings, "FILE_INDEX_PIPELINE_SPLITTER_CHUNK_OVERLAP", None
    )
    return file_extractors, chunk_size, chunk_overlap


_default_token_func = tiktoken.encoding_for_model("gpt-3.5-turbo").encode


@dataclass(kw_only=True)
class IndexPipeline:
    """Index a single file into the vector and document stores."""

    loader: BaseReader
    splitter: BaseSplitter | None
    chunk_batch_size: int = 200

    Source: type[DeclarativeBase]
    Index: type[DeclarativeBase]
    VS: BaseVectorStore
    DS: BaseDocumentStore
    FSPath: Path
    user_id: int
    engine: Engine
    collection_name: str = "default"
    private: bool = False
    run_embedding_in_thread: bool = False
    embedding: BaseEmbeddings

    @cached_property
    def vector_indexing(self) -> VectorIndexing:
        return VectorIndexing(
            vector_store=self.VS,
            doc_store=self.DS,
            embedding=self.embedding,
            cache_dir=getattr(settings, "KH_CHUNKS_OUTPUT_DIR", None),
        )

    def handle_docs(
        self, docs, file_id, file_name
    ) -> Generator[Document, None, int]:
        s_time = time.time()
        text_docs, non_text_docs, thumbnail_docs = [], [], []

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

        all_chunks = self.splitter(text_docs) if self.splitter else text_docs

        for chunk in all_chunks:
            page_label = chunk.metadata.get("page_label")
            if page_label and page_label in page_label_to_thumbnail:
                chunk.metadata["thumbnail_doc_id"] = (
                    page_label_to_thumbnail[page_label]
                )

        to_index_chunks = all_chunks + non_text_docs + thumbnail_docs

        n_chunks = 0
        batch = self.chunk_batch_size * 4
        for start in range(0, len(to_index_chunks), batch):
            chunk_slice = to_index_chunks[start : start + batch]
            self.handle_chunks_docstore(chunk_slice, file_id)
            n_chunks += len(chunk_slice)
            yield Document(
                f" => [{file_name}] Processed {n_chunks} chunks",
                channel="debug",
            )

        def insert_chunks_to_vectorstore():
            n = 0
            for start in range(0, len(to_index_chunks), self.chunk_batch_size):
                sl = to_index_chunks[start : start + self.chunk_batch_size]
                self.handle_chunks_vectorstore(sl, file_id)
                n += len(sl)
                if self.VS:
                    yield Document(
                        f" => [{file_name}] Created embedding for {n} chunks",
                        channel="debug",
                    )

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
        """Persist chunks to doc store and record in index table."""
        self.vector_indexing.add_to_docstore(chunks)
        with Session(self.engine) as session:
            session.add_all(
                [
                    self.Index(
                        source_id=file_id,
                        target_id=chunk.doc_id,
                        relation_type="document",
                    )
                    for chunk in chunks
                ]
            )
            session.commit()

    def handle_chunks_vectorstore(self, chunks, file_id):
        """Embed chunks and record vector ids in index table."""
        self.vector_indexing.add_to_vectorstore(chunks)
        self.vector_indexing.write_chunk_to_file(chunks)
        if self.VS:
            with Session(self.engine) as session:
                session.add_all(
                    [
                        self.Index(
                            source_id=file_id,
                            target_id=chunk.doc_id,
                            relation_type="vector",
                        )
                        for chunk in chunks
                    ]
                )
                session.commit()

    def get_id_if_exists(self, file_path: str | Path) -> Optional[str]:
        """Return the existing file id if this file is already indexed."""
        file_name = file_path.name if isinstance(file_path, Path) else file_path
        cond: tuple = (
            (self.Source.name == file_name, self.Source.user == self.user_id)
            if self.private
            else (self.Source.name == file_name,)
        )
        with Session(self.engine) as session:
            item = session.execute(select(self.Source).where(*cond)).first()
            if item:
                return item[0].id
        return None

    def store_url(self, url: str) -> str:
        """Persist a URL record and return the generated file id."""
        file_hash = sha256(url.encode()).hexdigest()
        source = self.Source(
            name=url, path=file_hash, size=0, user=self.user_id
        )
        with Session(self.engine) as session:
            session.add(source)
            session.commit()
            return source.id

    def store_file(self, file_path: Path) -> str:
        """Copy the file to storage, persist a record, return file id."""
        with file_path.open("rb") as fi:
            file_hash = sha256(fi.read()).hexdigest()
        shutil.copy(file_path, self.FSPath / file_hash)
        source = self.Source(
            name=file_path.name,
            path=file_hash,
            size=file_path.stat().st_size,
            user=self.user_id,
        )
        with Session(self.engine) as session:
            session.add(source)
            session.commit()
            return source.id

    def finish(self, file_id: str, file_path: str | Path) -> str:
        """Populate token count and loader metadata after indexing."""
        with Session(self.engine) as session:
            result = session.execute(
                select(self.Source).where(self.Source.id == file_id)
            ).first()
            if not result:
                return file_id
            item = result[0]
            doc_ids = [
                _[0]
                for _ in session.execute(
                    select(self.Index.target_id).where(
                        self.Index.source_id == file_id,
                        self.Index.relation_type == "document",
                    )
                )
            ]
            token_func = self.get_token_func()
            if doc_ids and token_func:
                docs = self.DS.get(doc_ids)
                item.note["tokens"] = sum(
                    len(token_func(doc.text)) for doc in docs
                )
            item.note["loader"] = self.loader.__class__.__name__
            session.add(item)
            session.commit()
        return file_id

    def get_token_func(self):
        """Return the tokenizer used to count tokens."""
        return _default_token_func

    def delete_file(self, file_id: str) -> None:
        """Remove a file and all its indexed chunks."""
        with Session(self.engine) as session:
            session.execute(
                delete(self.Source).where(self.Source.id == file_id)
            )
            vs_ids, ds_ids = [], []
            for (each,) in session.execute(
                select(self.Index).where(self.Index.source_id == file_id)
            ).all():
                if each.relation_type == "vector":
                    vs_ids.append(each.target_id)
                elif each.relation_type == "document":
                    ds_ids.append(each.target_id)
                session.delete(each)
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
        self, file_path: str | Path, reindex: bool, **kwargs
    ) -> Generator[Document, None, tuple[str, list[Document]]]:
        if isinstance(file_path, Path):
            file_path = file_path.resolve()

        file_id = self.get_id_if_exists(file_path)

        if isinstance(file_path, Path):
            if file_id is not None:
                if not reindex:
                    raise ValueError(
                        f"File {file_path.name} already indexed. Rerun with "
                        "reindex=True to force reindexing."
                    )
                yield Document(
                    f" => Removing old {file_path.name}", channel="debug"
                )
                self.delete_file(file_id)
                file_id = self.store_file(file_path)
            else:
                file_id = self.store_file(file_path)
        else:
            if file_id is not None:
                raise ValueError(f"URL {file_path} already indexed.")
            file_id = self.store_url(file_path)

        if isinstance(file_path, Path):
            extra_info = default_file_metadata_func(str(file_path))
            file_name = file_path.name
        else:
            extra_info = {"file_name": file_path}
            file_name = file_path

        extra_info["file_id"] = file_id
        extra_info["collection_name"] = self.collection_name

        yield Document(f" => Converting {file_name} to text", channel="debug")
        docs = self.loader.load_data(file_path, extra_info=extra_info)
        yield Document(f" => Converted {file_name} to text", channel="debug")
        yield from self.handle_docs(docs, file_id, file_name)

        self.finish(file_id, file_path)
        yield Document(f" => Finished indexing {file_name}", channel="debug")
        return file_id, docs


@dataclass(kw_only=True)
class IndexDocumentPipeline(BaseIndexing):
    """Route each file to the appropriate IndexPipeline and run it.

    This class is a factory + orchestrator: it decides which reader to
    use per file type, constructs the right ``IndexPipeline``, and
    delegates to it.
    """

    reader_mode: str
    embedding: BaseEmbeddings
    run_embedding_in_thread: bool = False

    @cached_property
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
                {ext: paddle_struct_reader for ext in
                 (".pdf", ".png", ".jpeg", ".jpg", ".tiff", ".tif")}
            )
        elif self.reader_mode == "paddle-vl":
            readers.update(
                {ext: paddle_vl_reader for ext in
                 (".pdf", ".png", ".jpeg", ".jpg", ".tiff", ".tif")}
            )

        # dev_readers, _, _ = dev_settings()
        # readers.update(dev_readers)
        return readers

    def is_url(self, file_path: str | Path) -> bool:
        return isinstance(file_path, str) and (
            file_path.startswith("http://") or file_path.startswith("https://")
        )

    def route(self, file_path: str | Path) -> IndexPipeline:
        """Select the right IndexPipeline for this file."""
        _, dev_chunk_size, dev_chunk_overlap = dev_settings()
        chunk_size = self.chunk_size or dev_chunk_size
        chunk_overlap = self.chunk_overlap or dev_chunk_overlap

        if self.is_url(file_path):
            reader = web_reader
        else:
            assert isinstance(file_path, Path)
            ext = file_path.suffix.lower()
            reader = self.readers.get(ext, unstructured)
            if reader is None:
                raise NotImplementedError(
                    f"No supported pipeline to index {file_path.name}. "
                    "Please specify a pipeline for this file type in settings."
                )

        print(f"Chunk size: {chunk_size}, chunk overlap: {chunk_overlap}")
        print("Using reader", reader)
        return IndexPipeline(
            loader=reader,
            splitter=TokenSplitter(
                chunk_size=chunk_size or 1024,
                chunk_overlap=chunk_overlap or 256,
                separator="\n\n",
                backup_separators=["\n", ".", "\u200B"],
            ),
            run_embedding_in_thread=self.run_embedding_in_thread,
            Source=self.Source,
            Index=self.Index,
            VS=self.VS,
            DS=self.DS,
            FSPath=self.FSPath,
            user_id=self.user_id,
            engine=self.engine,
            private=self.private,
            embedding=self.embedding,
        )

    def run(
        self, file_paths: str | Path | list[str | Path], *args, **kwargs
    ) -> tuple[list[str | None], list[str | None]]:
        raise NotImplementedError

    def stream(
        self,
        file_paths: str | Path | list[str | Path],
        reindex: bool = False,
        **kwargs,
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        """Yield progress messages, return (file_ids, errors, docs)."""
        if not isinstance(file_paths, list):
            file_paths = [file_paths]

        file_ids: list[str | None] = []
        errors: list[str | None] = []
        all_docs: list[Document] = []

        n_files = len(file_paths)
        for idx, file_path in enumerate(file_paths):
            file_name = (
                file_path if self.is_url(file_path) else Path(file_path).name
            )
            if not self.is_url(file_path):
                file_path = Path(file_path)

            yield Document(
                content=f"Indexing [{idx + 1}/{n_files}]: {file_name}",
                channel="debug",
            )
            try:
                pipeline = self.route(file_path)
                file_id, docs = yield from pipeline.stream(
                    file_path, reindex=reindex, **kwargs
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
