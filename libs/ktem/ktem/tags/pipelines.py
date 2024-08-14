from pathlib import Path
from typing import Generator

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

    @property
    def chunk_tag_index_crud(self) -> ChunkTagIndexCRUD:
        return ChunkTagIndexCRUD(engine)

    @property
    def tag_crud(self) -> TagCRUD:
        return TagCRUD(engine)

    @classmethod
    def resolve_tag_names(cls, tag_str: str) -> list[str]:
        tags = []
        if tag_str:
            if "," in tag_str:
                tags = [tag.strip() for tag in tag_str.split(",")]
            else:
                tags = [tag_str]

        return tags

    @classmethod
    def get_pipeline(cls, user_settings, index_settings) -> BaseFileIndexIndexing:
        """Get custom settings (tag_ids) from index settings"""
        llm = llms.get(index_settings.get("llm", llms.get_default_name()))
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

    def process_tag(self, tag_prompt: str, doc_content: str) -> str:
        # TODO: add LLM logic to automatically tag document content
        return f"{type(self.llm)} {tag_prompt} - {doc_content}"

    def process_docs(
        self, docs: list[DocumentWithEmbedding], clean_previous=False, chunk_size=20
    ) -> Generator[Document, None, list[str]]:
        doc_ids = [doc.doc_id for doc in docs]
        n_docs = len(docs)
        n_tags = len(self.tags)

        indexed_ids = []

        # clean previous tagging results if specified
        if clean_previous:
            deleted_items = self.chunk_tag_index_crud.delete_by_chunk_ids(doc_ids)
            print(f"Deleted {len(deleted_items)} previous tagging results.")

        # tagging process
        for _tag_idx, tag in enumerate(self.tags):
            yield Document(
                content=f"Tagging [{_tag_idx+1}/{n_tags} tag(s) `{tag}`]:",
                channel="debug",
            )
            tag_dict = self.tag_crud.query_by_name(tag)
            if tag_dict is None:
                continue

            tag_prompt = tag_dict.get("prompt", "")
            tag_id = tag_dict.get("id", "")

            for _idx, doc in enumerate(docs):
                doc_content = doc.text
                doc_id = doc.doc_id

                # pending
                index_id = self.chunk_tag_index_crud.create(
                    tag_id=tag_id, chunk_id=doc_id, content=""
                )
                indexed_ids += [index_id]

                try:
                    # in - progress
                    self.chunk_tag_index_crud.update_status_by_id(
                        index_id, new_status=TagProcessStatus.in_progress
                    )
                    # main LLM call to populate tag content
                    tag_content: str = self.process_tag(tag_prompt, doc_content)

                    # TODO: create additional vectorstore and
                    # perform vector indexing for tag content
                    self.chunk_tag_index_crud.update_content_by_id(
                        index_id,
                        new_content=tag_content,
                    )
                    self.chunk_tag_index_crud.update_status_by_id(
                        index_id, new_status=TagProcessStatus.done
                    )

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
            doc_ids = list(set([r[0].target_id for r in results.all()]))

        docs = self.DS.get(doc_ids)
        print(f"Got {len(docs)} docs in index.")
        yield from self.process_docs(docs, clean_previous=True)
