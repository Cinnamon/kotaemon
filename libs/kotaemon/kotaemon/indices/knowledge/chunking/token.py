"""Fallback to the caller's existing splitter with metadata preserved."""

from kotaemon.base import Document
from kotaemon.indices.splitters import BaseSplitter

from ..metadata import normalize_knowledge_metadata


class TokenChunkStrategy:
    def __init__(self, token_splitter: BaseSplitter):
        self.token_splitter = token_splitter

    def split(self, document: Document) -> list[Document]:
        # Metadata is preserved for retrieval, but should not consume the text
        # budget or cause small configured chunk sizes to reject the document.
        prepared = Document.from_dict(document.to_dict())
        prepared.metadata = normalize_knowledge_metadata(document)
        keys = list(prepared.metadata)
        prepared.excluded_embed_metadata_keys = keys
        prepared.excluded_llm_metadata_keys = keys
        chunks = self.token_splitter([prepared])
        for chunk in chunks:
            chunk.metadata = normalize_knowledge_metadata(chunk)
            chunk.excluded_embed_metadata_keys = list(
                document.excluded_embed_metadata_keys
            )
            chunk.excluded_llm_metadata_keys = list(document.excluded_llm_metadata_keys)
        return chunks
