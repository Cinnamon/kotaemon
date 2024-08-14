from theflow import Param
from kotaemon.base import BaseComponent, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from ktem.db.models import engine
from ktem.db.base_models import TagProcessStatus

from .crud import ChunkTagIndexCRUD


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

    def run(
        self,
        tag_prompts: list[str],
        tag_ids: list[str],
        chunk_ids: list[str] | None = None,
        run_failures: bool = False,
    ):
        if chunk_ids is None:
            records = self.VS._collection.get(
                include=["metadatas", "documents"]
            )
            chunk_ids = records["ids"]
        else:
            records = self.VS._collection.get(
                ids=chunk_ids,
                include=["metadatas", "documents"],
            )

        n_chunk = len(chunk_ids)
        index_ids: list[str] = []

        # In - pending
        for i, (meta_data, chunk_content, chunk_id) in enumerate(zip(
            records['metadatas'],
            records['documents'],
            records['ids']
        )):
            for tag_prompt, tag_id in zip(tag_prompts, tag_ids):
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
                    # Enable Run for failures too and the previous is success
                    continue
                elif not run_failures and exist_record is not None:
                    # Disable run for failure but the record has been existed no matter status
                    continue

                llm_prompt: str = f"{tag_prompt}\n```{chunk_content}```"

                content = llm_prompt

                # Pending
                index_id = self.chunk_tag_index_crud.create(
                    tag_id=tag_id,
                    chunk_id=chunk_id,
                    content=content
                )
                index_ids += [index_id]

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
                    print(f"[{i+1}/{n_chunk}] Done - index: {index_id}")
                except Exception as e:
                    # Failed
                    print(f"[{i+1}/{n_chunk}] Got exception for index-id: {index_id}, {e}")
                    self.chunk_tag_index_crud.update_status_by_id(
                        index_id, new_status=TagProcessStatus.failed
                    )

        return True
