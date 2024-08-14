from concurrent.futures import ThreadPoolExecutor

from theflow import Param
from kotaemon.base import BaseComponent, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from ktem.db.models import engine
from ktem.db.base_models import TagProcessStatus

from .crud import ChunkTagIndexCRUD


THREAD_POOL_EXECUTOR = ThreadPoolExecutor(
    max_workers=8
)


class MetaIndexPipeline(BaseComponent):
    VS = Param(help="The VectorStore")
    VS_tag_index: Param(help="The VectorStore for Tag-Chunk Index")
    user_id = Param(help="The user id")
    private: bool = False
    run_embedding_in_thread: bool = False
    embedding: BaseEmbeddings

    @property
    def chunk_tag_index_crud(self) -> ChunkTagIndexCRUD:
        return ChunkTagIndexCRUD(engine)

    def run_single(
        self,
        chunk_id: str,
        chunk_content: str,
        tag_id: str,
        tag_prompt: str,
        run_failures: bool = False
    ):
        """
        Create embedding & content for pair ( chunk-id vs tag-id )

        Notes:
        - IF the pair (chunk_id, tag_id) exists, depend on run_failures and its previous status
        to decide whether we will add its to this current batch-processing or not.

        """
        exist_record = self.chunk_tag_index_crud.query_by_chunk_tag_id(
            chunk_id=chunk_id,
            tag_id=tag_id
        )

        if (
            run_failures and
            (
                exist_record is not None and
                exist_record['status'] == TagProcessStatus.done.value
            )
        ):
            # Enable Run for failures and the previous is success
            return
        elif not run_failures and exist_record is not None:
            # Disable run for failure but the record has been existed no matter status
            return

        llm_prompt: str = f"{tag_prompt}\n```{chunk_content}```"

        content = llm_prompt

        # Pending
        index_id = self.chunk_tag_index_crud.create(
            tag_id=tag_id,
            chunk_id=chunk_id,
            content=content
        )

        # In - progress
        self.chunk_tag_index_crud.update_status_by_id(
            index_id, new_status=TagProcessStatus.in_progress
        )

        try:
            embed_doc: DocumentWithEmbedding = self.embedding(content)[0]
            self.VS_tag_index._collection.add(
                ids=[index_id],
                metadatas=[{
                    "chunk_id": chunk_id,
                    "tag_id": tag_id,
                    "content": embed_doc.text,
                }],
                embeddings=[embed_doc.embedding]
            )

            # Done
            self.chunk_tag_index_crud.update_status_by_id(
                index_id,
                new_status=TagProcessStatus.done
            )
            print(f"Done - index: {index_id}")
        except Exception as e:
            # Failed
            print(f"Got exception for index-id: {index_id}, {e}")
            self.chunk_tag_index_crud.update_status_by_id(
                index_id, new_status=TagProcessStatus.failed
            )

    def run(
        self,
        tag_prompts: list[str],
        tag_ids: list[str],
        chunk_ids: list[str] | None = None,
        run_failures: bool = False,
        run_threadpool: bool = True
    ):
        """
        With n tag, and m chunk
        Run indexing for n x m pairs
        For each pair, the content = llm(tag_content + chunk_content)
        The content later will be saved on VS for later similarity search

        """
        assert len(tag_ids) == len(tag_prompts)

        # IF chunk_ids is set nul. Retrieve all
        if chunk_ids is None:
            records = self.VS._collection.get(
                include=["metadatas", "documents"]
            )
        else:
            records = self.VS._collection.get(
                ids=chunk_ids,
                include=["metadatas", "documents"],
            )

        for i, (meta_data, chunk_content, chunk_id) in enumerate(zip(
            records['metadatas'],
            records['documents'],
            records['ids']
        )):
            for tag_prompt, tag_id in zip(tag_prompts, tag_ids):
                if run_threadpool:
                    THREAD_POOL_EXECUTOR.submit(
                        self.run_single,
                        *(chunk_id, chunk_content, tag_id, tag_prompt)
                    )
                else:
                    self.run_single(
                        chunk_id,
                        chunk_content,
                        tag_id,
                        tag_prompt,
                    )

        return True
