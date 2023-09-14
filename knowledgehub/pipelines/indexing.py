from typing import List

from theflow import Node, Param

from ..components import BaseComponent
from ..documents.base import Document
from ..embeddings import BaseEmbeddings
from ..vectorstores import BaseVectorStore


class IndexVectorStoreFromDocumentPipeline(BaseComponent):
    """Ingest the document, run through the embedding, and store the embedding in a
    vector store.

    This pipeline supports the following set of inputs:
        - List of documents
        - List of texts
    """

    vector_store: Param[BaseVectorStore] = Param()
    embedding: Node[BaseEmbeddings] = Node()
    # TODO: populate to document store as well when it's finished
    # TODO: refer to llama_index's storage as well

    def run_raw(self, text: str) -> None:
        self.vector_store.add([self.embedding(text)])

    def run_batch_raw(self, text: List[str]) -> None:
        self.vector_store.add(self.embedding(text))

    def run_document(self, text: Document) -> None:
        self.vector_store.add([self.embedding(text)])

    def run_batch_document(self, text: List[Document]) -> None:
        self.vector_store.add(self.embedding(text))

    def is_document(self, text) -> bool:
        if isinstance(text, Document):
            return True
        elif isinstance(text, List) and isinstance(text[0], Document):
            return True
        return False

    def is_batch(self, text) -> bool:
        if isinstance(text, list):
            return True
        return False

    def persist(self, path: str):
        """Save the whole state of the indexing pipeline vector store and all
        necessary information to disk

        Args:
            path (str): path to save the state
        """

    def load(self, path: str):
        """Load all information from disk to an object"""
