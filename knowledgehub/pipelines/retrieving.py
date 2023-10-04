from abc import abstractmethod
from pathlib import Path
from typing import List, Union

from theflow import Node, Param

from ..base import BaseComponent
from ..docstores import BaseDocumentStore
from ..documents.base import Document, RetrievedDocument
from ..embeddings import BaseEmbeddings
from ..vectorstores import BaseVectorStore

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"


class BaseRetrieval(BaseComponent):
    """Define the base interface of a retrieval pipeline"""

    @abstractmethod
    def run_raw(self, text: str, top_k: int = 1) -> List[RetrievedDocument]:
        ...

    @abstractmethod
    def run_batch_raw(
        self, text: List[str], top_k: int = 1
    ) -> List[List[RetrievedDocument]]:
        ...

    @abstractmethod
    def run_document(self, text: Document, top_k: int = 1) -> List[RetrievedDocument]:
        ...

    @abstractmethod
    def run_batch_document(
        self, text: List[Document], top_k: int = 1
    ) -> List[List[RetrievedDocument]]:
        ...


class RetrieveDocumentFromVectorStorePipeline(BaseRetrieval):
    """Retrieve list of documents from vector store"""

    vector_store: Param[BaseVectorStore] = Param()
    doc_store: Param[BaseDocumentStore] = Param()
    embedding: Node[BaseEmbeddings] = Node()
    # TODO: refer to llama_index's storage as well

    def run_raw(self, text: str, top_k: int = 1) -> List[RetrievedDocument]:
        return self.run_batch_raw([text], top_k=top_k)[0]

    def run_batch_raw(
        self, text: List[str], top_k: int = 1
    ) -> List[List[RetrievedDocument]]:
        if self.doc_store is None:
            raise ValueError(
                "doc_store is not provided. Please provide a doc_store to "
                "retrieve the documents"
            )

        result = []
        for each_text in text:
            emb = self.embedding(each_text)
            _, scores, ids = self.vector_store.query(embedding=emb, top_k=top_k)
            docs = self.doc_store.get(ids)
            each_result = [
                RetrievedDocument(**doc.to_dict(), score=score)
                for doc, score in zip(docs, scores)
            ]
            result.append(each_result)
        return result

    def run_document(self, text: Document, top_k: int = 1) -> List[RetrievedDocument]:
        return self.run_raw(text.text, top_k)

    def run_batch_document(
        self, text: List[Document], top_k: int = 1
    ) -> List[List[RetrievedDocument]]:
        return self.run_batch_raw(text=[t.text for t in text], top_k=top_k)

    def is_document(self, text, *args, **kwargs) -> bool:
        if isinstance(text, Document):
            return True
        elif isinstance(text, List) and isinstance(text[0], Document):
            return True
        return False

    def is_batch(self, text, *args, **kwargs) -> bool:
        if isinstance(text, list):
            return True
        return False

    def save(
        self,
        path: Union[str, Path],
        vectorstore_fname: str = VECTOR_STORE_FNAME,
        docstore_fname: str = DOC_STORE_FNAME,
    ):
        """Save the whole state of the indexing pipeline vector store and all
        necessary information to disk

        Args:
            path (str): path to save the state
        """
        if isinstance(path, str):
            path = Path(path)
        self.vector_store.save(path / vectorstore_fname)
        self.doc_store.save(path / docstore_fname)

    def load(
        self,
        path: Union[str, Path],
        vectorstore_fname: str = VECTOR_STORE_FNAME,
        docstore_fname: str = DOC_STORE_FNAME,
    ):
        """Load all information from disk to an object"""
        if isinstance(path, str):
            path = Path(path)
        self.vector_store.load(path / vectorstore_fname)
        self.doc_store.load(path / docstore_fname)
