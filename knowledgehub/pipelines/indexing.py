import uuid
from typing import List, Optional

from theflow import Node, Param

from ..base import BaseComponent
from ..docstores import BaseDocumentStore
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
    doc_store: Optional[BaseDocumentStore] = None
    embedding: Node[BaseEmbeddings] = Node()

    # TODO: refer to llama_index's storage as well

    def run_raw(self, text: str) -> None:
        document = Document(text=text, id_=str(uuid.uuid4()))
        self.run_batch_document([document])

    def run_batch_raw(self, text: List[str]) -> None:
        documents = [Document(t, id_=str(uuid.uuid4())) for t in text]
        self.run_batch_document(documents)

    def run_document(self, text: Document) -> None:
        self.run_batch_document([text])

    def run_batch_document(self, text: List[Document]) -> None:
        embeddings = self.embedding(text)
        self.vector_store.add(
            embeddings=embeddings,
            ids=[t.id_ for t in text],
        )
        if self.doc_store:
            self.doc_store.add(text)

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
