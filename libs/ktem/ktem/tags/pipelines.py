from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Generator

from ktem.db.base_models import BaseTag, TagScope, TagType
from ktem.db.models import engine
from ktem.index.file.base import BaseFileIndexIndexing
from ktem.index.file.pipelines import IndexDocumentPipeline, IndexPipeline
from ktem.llms.manager import llms
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotaemon.base import BaseComponent, Document, DocumentWithEmbedding, Param
from kotaemon.base.schema import HumanMessage, SystemMessage
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.llms import BaseLLM
from kotaemon.storages import BaseVectorStore

from ..db.base_models import TagProcessStatus
from .crud import ChunkTagIndexCRUD, TagCRUD

N_CHUNKS_PER_FILE_FOR_TAGGING = 5


class ChunkTagIndexVectorStore:
    def __init__(self, vectorstore: BaseVectorStore, embeddings: BaseEmbeddings):
        self._vectorstore = vectorstore
        self._embedding = embeddings

    def add(self, doc_ids: list[str], doc_contents: list[str]):
        embeddings = self._embedding(doc_contents)
        self._vectorstore.add(
            embeddings=embeddings,
            ids=doc_ids,
        )

    def query(self, query: str, top_k: int = 10, tag_names: list[str] = []):
        retrieval_kwargs = {}

        if tag_names:
            retrieval_kwargs["filters"] = MetadataFilters(
                filters=[
                    MetadataFilter(
                        key="tag_name",
                        value=tag_names,
                        operator=FilterOperator.IN,
                    )
                ],
                condition=FilterCondition.OR,
            )

        emb = self._embedding(query)[0].embedding
        _, scores, ids = self._vectorstore.query(
            embedding=emb, top_k=top_k, **retrieval_kwargs
        )

        return ids


class MetaIndexPipeline(IndexDocumentPipeline):
    """Meta index pipeline for tagging documents.
    We reuse the logic from IndexDocumentPipeline and add custom
    tagging procedure with .stream() method.
    """

    llm: BaseLLM
    tags: list[str]
    meta_vectorstore = Param(help="The VectorStore")
    DEFAULT_CHUNK_SIZE = 10

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
        print(f"Tags: {tags}")
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

    def generate_with_llm(self, tag: BaseTag, doc_content: str) -> str:
        llm_tag_pipeline = LLMMetaTagPipeline(llm=self.llm, tag=tag)
        return llm_tag_pipeline.run(doc_content)

    def create_tag_content(self, chunk_id: str, tag: BaseTag, doc_content: str) -> str:
        # pending
        tag_id = tag.id
        index_id = self.chunk_tag_index_crud.create(
            tag_id=tag_id, chunk_id=chunk_id, content=""
        )
        # in - progress
        self.chunk_tag_index_crud.update_status_by_id(
            index_id, new_status=TagProcessStatus.in_progress
        )
        # main LLM call to populate tag content
        tag_content: str = self.generate_with_llm(tag, doc_content)

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

            tag_scope = tag_obj.scope

            if tag_scope == TagScope.chunk.value:
                pool = ThreadPoolExecutor(max_workers=N_CHUNKS_PER_FILE_FOR_TAGGING)
                futures = []
                for _idx, doc in enumerate(docs):
                    try:
                        doc_content = doc.text
                        doc_id = doc.doc_id
                        futures.append(
                            pool.submit(
                                self.create_tag_content, doc_id, tag_obj, doc_content
                            )
                        )
                        if (_idx + 1) % chunk_size == 0 or _idx == n_docs - 1:
                            # get output from current thread pool
                            for future in futures:
                                index_id = future.result()
                                indexed_ids.append(index_id)

                            futures = []

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
                # finish the rest of the threads
                pool.shutdown(wait=True)

            elif tag_scope == TagScope.file.value:
                for _idx, (file_id, file_docs) in enumerate(file_id_to_docs.items()):
                    try:
                        doc_content = "\n".join(
                            [
                                doc.text
                                for doc in file_docs[:N_CHUNKS_PER_FILE_FOR_TAGGING]
                            ]
                        )
                        index_id = self.create_tag_content(
                            file_id, tag_obj, doc_content
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


class LLMMetaTagPipeline(BaseComponent):
    llm: BaseLLM
    tag: BaseTag

    def run(self, context: str):
        return self.invoke(context)

    def get_prompt(self, context: str):
        context = context.replace("\n", " ")
        if self.tag.type == TagType.text.value:
            messages = [
                SystemMessage(
                    content=(
                        "You are a world class algorithm to convert "
                        "the input text to a tag value based on "
                        "the instruction below."
                    )
                ),
                HumanMessage(
                    content=(f"Tag name:{self.tag.name}\nInstruction:{self.tag.prompt}")
                ),
                HumanMessage(content=f"Context:\n{context}"),
                HumanMessage(content="Create a tag value based on the above context."),
                HumanMessage(
                    content=("Only output the tag value " "without any explanation.")
                ),
            ]
            classes = None
        else:
            if self.tag.type == TagType.classification.value:
                classes = self.tag.meta["valid_classes"]
            else:
                classes = "true, false"
            messages = [
                SystemMessage(
                    content=(
                        "You are a world class algorithm to classify "
                        "the input text to predefined classed based on "
                        "the instruction below."
                    )
                ),
                HumanMessage(
                    content=(f"Tag name:{self.tag.name}\nInstruction:{self.tag.prompt}")
                ),
                HumanMessage(content=f"Context:\n{context}"),
                HumanMessage(
                    content=(
                        "Classify the above context "
                        f"to one of the classes: {classes}"
                    )
                ),
                HumanMessage(
                    content=(
                        "Only output the exact class name " "without any explanation."
                    )
                ),
            ]

        if classes is not None:
            classes = [it.strip() for it in classes.split(",")]

        return messages, classes

    def invoke(self, context: str):
        messages, classes = self.get_prompt(context)
        kwargs = {
            "max_tokens": 100,
        }
        try:
            llm_output = self.llm(messages, **kwargs).text
            if classes is not None:
                assert llm_output in classes, f"Output {llm_output} not in {classes}"
            print(self.tag.name, context[:100].replace("\n", " "), llm_output)
        except Exception as e:
            print(e)
            return None

        return llm_output
