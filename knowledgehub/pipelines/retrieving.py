from typing import List

from theflow import Node, Param

from ..components import BaseComponent
from ..documents.base import Document
from ..embeddings import BaseEmbeddings
from ..vectorstores import BaseVectorStore


class RetrieveDocumentFromVectorStorePipeline(BaseComponent):
    """Retrieve list of documents from vector store"""

    vector_store: Param[BaseVectorStore] = Param()
    embedding: Node[BaseEmbeddings] = Node()
    # TODO: populate to document store as well when it's finished
    # TODO: refer to llama_index's storage as well

    def run_raw(self, text: str) -> List[str]:
        emb = self.embedding(text)
        return self.vector_store.query(embedding=emb)[2]

    def run_batch_raw(self, text: List[str]) -> List[List[str]]:
        result = []
        for each_text in text:
            emb = self.embedding(each_text)
            result.append(self.vector_store.query(embedding=emb)[2])
        return result

    def run_document(self, text: Document) -> List[str]:
        return self.run_raw(text.text)

    def run_batch_document(self, text: List[Document]) -> List[List[str]]:
        input_text = [each.text for each in text]
        return self.run_batch_raw(input_text)

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
