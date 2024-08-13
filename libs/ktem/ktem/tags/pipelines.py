import uuid

from theflow import Param
from kotaemon.base import BaseComponent, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from ktem.db.models import engine

from .crud import ChunkTagIndexCRUD
from ..db.base_models import TagProcessStatus


class MetaIndexPipeline(BaseComponent):
    VS = Param(help="The VectorStore")
    VS_tag_index: Param(help="The VectorStore for Tag-Chunk Index")
    user_id = Param(help="The user id")
    tag_id = Param(help="The tag id")
    private: bool = False
    run_embedding_in_thread: bool = False
    embedding: BaseEmbeddings

    @property
    def chunk_tag_index_crud(self) -> ChunkTagIndexCRUD:
        return ChunkTagIndexCRUD(engine)

    def run(
        self,
        tag_prompt: str
    ):
        records = self.VS._collection.get(
            include=["metadatas", "documents"]
        )
        n_chunk = len(records['ids'])
        index_ids: list[str] = []

        # In - pending
        for i, (meta_data, chunk_content, chunk_id) in enumerate(zip(
            records['metadatas'],
            records['documents'],
            records['ids']
        )):
            concat_content: str = f"{tag_prompt} - {chunk_content}"

            # Pending
            index_id = self.chunk_tag_index_crud.create(
                tag_id=self.tag_id,
                chunk_id=chunk_id,
                content=concat_content
            )
            index_ids += [index_id]

            # In - progress
            self.chunk_tag_index_crud.update_status_by_id(
                index_id, new_status=TagProcessStatus.in_progress
            )

            try:
                embed_doc: DocumentWithEmbedding = self.embedding(concat_content)[0]
                self.VS_tag_index._collection.add(
                    ids=[index_id],
                    metadatas=[{
                        "chunk_id": chunk_id,
                        "tag_id": self.tag_id,
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
