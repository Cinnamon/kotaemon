from collections import defaultdict
from pathlib import Path
from typing import Generator

from ktem.db.base_models import BaseTag, TagScope
from ktem.db.models import engine
from ktem.index.file.base import BaseFileIndexIndexing
from ktem.index.file.pipelines import IndexDocumentPipeline, IndexPipeline
from ktem.llms.manager import llms
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.llms import BaseLLM

from ..db.base_models import TagProcessStatus
from .crud import ChunkTagIndexCRUD, TagCRUD


class MetaIndexPipeline(IndexDocumentPipeline):
    """Meta index pipeline for tagging documents.
    We reuse the logic from IndexDocumentPipeline and add custom
    tagging procedure with .stream() method.
    """

    llm: BaseLLM
    tags: list[str]
    DEFAULT_CHUNK_SIZE = 20

    @property
    def chunk_tag_index_crud(self) -> ChunkTagIndexCRUD:
        return ChunkTagIndexCRUD(engine)

    @property
    def tag_crud(self) -> TagCRUD:
        return TagCRUD(engine)

    @classmethod
    def resolve_tag_names(cls, tag_str: str | list) -> list[str]:
        if isinstance(tag_str, list):
            return tag_str

        tag_str = tag_str.strip()
        tags = []
        if tag_str.strip() == "":
            return []

        if "," in tag_str:
            tags = [tag.strip() for tag in tag_str.split(",")]
        else:
            tags = [tag_str]

        return tags

    @classmethod
    def get_pipeline(
        cls, user_settings: dict, index_settings: dict[str, str]
    ) -> BaseFileIndexIndexing:
        """Get custom settings (tag_ids) from index settings"""
        llm = llms.get(index_settings.get("llm", llms.get_default_name()), None)
        tags = index_settings.get("tags", "")
        obj = super().get_pipeline(user_settings, index_settings)

        # assign custom settings for the pipeline
        obj.llm = llm
        obj.tags = cls.resolve_tag_names(tags)
        return obj

    def route(self, file_path: Path) -> IndexPipeline:
        """Decide the pipeline based on the file type
        Can subclass this method for a more elaborate pipeline routing strategy.
        """
        pipeline = super().route(file_path)

        # disable vectorstore for this kind of Index
        pipeline.VS = None
        # disable chunking for this kind of Index
        pipeline.splitter = None

        return pipeline

    def generate_with_llm(self, tag_prompt: str, doc_content: str) -> str:
        # TODO: add LLM logic to automatically tag document content
        return f"{type(self.llm)} {tag_prompt} - {doc_content}"

    def create_tag_content(
        self, tag_id: str, chunk_id: str, tag_prompt: str, doc_content: str
    ) -> str:
        # pending
        index_id = self.chunk_tag_index_crud.create(
            tag_id=tag_id, chunk_id=chunk_id, content=""
        )
        # in - progress
        self.chunk_tag_index_crud.update_status_by_id(
            index_id, new_status=TagProcessStatus.in_progress
        )
        # main LLM call to populate tag content
        tag_content: str = self.generate_with_llm(tag_prompt, doc_content)

        # TODO: create additional vectorstore and
        # perform vector indexing for tag content
        self.chunk_tag_index_crud.update_content_by_id(
            index_id,
            new_content=tag_content,
        )
        self.chunk_tag_index_crud.update_status_by_id(
            index_id, new_status=TagProcessStatus.done
        )
        return index_id

    def process_docs(
        self,
        docs: list[DocumentWithEmbedding],
        clean_previous=False,
        chunk_size=DEFAULT_CHUNK_SIZE,
    ) -> Generator[Document, None, list[str]]:
        doc_ids = [doc.doc_id for doc in docs]
        n_docs = len(docs)
        n_tags = len(self.tags)

        # group doc by file_id
        file_id_to_docs = defaultdict(list)
        for doc in docs:
            file_id = doc.metadata.get("file_id", "")
            if file_id:
                file_id_to_docs[file_id].append(doc)

        n_files = len(file_id_to_docs)
        file_ids = list(file_id_to_docs.keys())

        indexed_ids = []

        # clean previous tagging results if specified
        if clean_previous:
            deleted_items = self.chunk_tag_index_crud.delete_by_chunk_ids(
                doc_ids + file_ids
            )
            yield Document(
                content=(f"Cleaned {len(deleted_items)} previous tagging results."),
                channel="debug",
            )

        # tagging process
        for _tag_idx, tag in enumerate(self.tags):
            yield Document(
                content=f"Tagging [{_tag_idx+1}/{n_tags} tag(s) `{tag}`]:",
                channel="debug",
            )
            tag_obj: BaseTag | None = self.tag_crud.query_by_name(tag)
            if tag_obj is None:
                continue

            tag_prompt = tag_obj.prompt
            tag_id = tag_obj.id
            tag_scope = tag_obj.scope

            if tag_scope == TagScope.chunk.value:
                for _idx, doc in enumerate(docs):
                    try:
                        doc_content = doc.text
                        doc_id = doc.doc_id
                        index_id = self.create_tag_content(
                            tag_id, doc_id, tag_prompt, doc_content
                        )
                        indexed_ids.append(index_id)
                        if (_idx + 1) % chunk_size == 0 or _idx == n_docs - 1:
                            yield Document(
                                content=(
                                    f"Tagging [{_tag_idx+1}/{n_tags}] - "
                                    f"Processed [{_idx+1}/{n_docs} documents]"
                                ),
                                channel="debug",
                            )
                    except Exception as e:
                        # failed
                        self.chunk_tag_index_crud.update_status_by_id(
                            index_id, new_status=TagProcessStatus.failed
                        )
                        print(e)
                        yield Document(
                            content=(
                                f"Tagging [{_tag_idx+1}/{n_tags}]: - "
                                f"Failed to tag document {_idx + 1}: {e}"
                            ),
                            channel="debug",
                        )
            elif tag_scope == TagScope.file.value:
                for _idx, (file_id, file_docs) in enumerate(file_id_to_docs.items()):
                    try:
                        doc_content = "\n".join([doc.text for doc in file_docs])
                        index_id = self.create_tag_content(
                            tag_id, file_id, tag_prompt, doc_content
                        )
                        indexed_ids.append(index_id)
                        yield Document(
                            content=(
                                f"Tagging [{_tag_idx+1}/{n_tags}] - "
                                f"Processed [{_idx+1}/{n_files} files]"
                            ),
                            channel="debug",
                        )
                    except Exception as e:
                        # failed
                        self.chunk_tag_index_crud.update_status_by_id(
                            index_id, new_status=TagProcessStatus.failed
                        )
                        print(e)
                        yield Document(
                            content=(
                                f"Tagging [{_tag_idx+1}/{n_tags}]: - "
                                f"Failed to tag document {_idx + 1}: {e}"
                            ),
                            channel="debug",
                        )

        yield Document(
            content="Completed.",
            channel="debug",
        )

        return indexed_ids

    def stream(
        self, file_paths: str | Path | list[str | Path], reindex: bool = False, **kwargs
    ) -> Generator[
        Document, None, tuple[list[str | None], list[str | None], list[Document]]
    ]:
        """Return a list of indexed file ids, and a list of errors"""
        file_ids, errors, all_docs = yield from super().stream(
            file_paths, reindex=reindex, **kwargs
        )
        yield from self.process_docs(all_docs)

        return file_ids, errors, all_docs

    def rebuild_index(self) -> Generator[Document, None, list[str]]:
        """Update tag content for all documents in the index"""

        doc_ids = []

        with Session(engine) as session:
            stmt = select(self.Index).where(
                self.Index.relation_type == "document",
            )
            results = session.execute(stmt)
            doc_ids = list(set(result.target_id for result in results.scalars()))

        docs = self.DS.get(doc_ids)
        print(f"Got {len(docs)} docs in index.")
        indexed_ids = yield from self.process_docs(docs, clean_previous=True)

        return indexed_ids
