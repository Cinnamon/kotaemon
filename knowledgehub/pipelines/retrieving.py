from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from kotaemon.indices.rankings import BaseReranking

from ..base import BaseComponent
from ..base.schema import Document, RetrievedDocument
from ..embeddings import BaseEmbeddings
from ..storages import BaseDocumentStore, BaseVectorStore

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"


class RetrieveDocumentFromVectorStorePipeline(BaseComponent):
    """Retrieve list of documents from vector store"""

    vector_store: BaseVectorStore
    doc_store: BaseDocumentStore
    embedding: BaseEmbeddings
    rerankers: Sequence[BaseReranking] = []
    top_k: int = 1
    # TODO: refer to llama_index's storage as well

    def run(
        self, text: str | Document, top_k: Optional[int] = None
    ) -> list[RetrievedDocument]:
        """Retrieve a list of documents from vector store

        Args:
            text: the text to retrieve similar documents
            top_k: number of top similar documents to return

        Returns:
            list[RetrievedDocument]: list of retrieved documents
        """
        if top_k is None:
            top_k = self.top_k

        if self.doc_store is None:
            raise ValueError(
                "doc_store is not provided. Please provide a doc_store to "
                "retrieve the documents"
            )

        emb: list[float] = self.embedding(text)[0]
        _, scores, ids = self.vector_store.query(embedding=emb, top_k=top_k)
        docs = self.doc_store.get(ids)
        result = [
            RetrievedDocument(**doc.to_dict(), score=score)
            for doc, score in zip(docs, scores)
        ]
        # use additional reranker to re-order the document list
        if self.rerankers:
            for reranker in self.rerankers:
                result = reranker(documents=result, query=text)

        return result

    def save(
        self,
        path: str | Path,
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
        path: str | Path,
        vectorstore_fname: str = VECTOR_STORE_FNAME,
        docstore_fname: str = DOC_STORE_FNAME,
    ):
        """Load all information from disk to an object"""
        if isinstance(path, str):
            path = Path(path)
        self.vector_store.load(path / vectorstore_fname)
        self.doc_store.load(path / docstore_fname)
