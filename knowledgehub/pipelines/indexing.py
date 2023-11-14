from __future__ import annotations

import uuid
from pathlib import Path

from theflow import Node, Param

from ..base import BaseComponent, Document
from ..embeddings import BaseEmbeddings
from ..storages import BaseDocumentStore, BaseVectorStore

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"


class IndexVectorStoreFromDocumentPipeline(BaseComponent):
    """Ingest the document, run through the embedding, and store the embedding in a
    vector store.

    This pipeline supports the following set of inputs:
        - List of documents
        - List of texts
    """

    vector_store: Param[BaseVectorStore] = Param()
    doc_store: Param[BaseDocumentStore] = Param()
    embedding: Node[BaseEmbeddings] = Node()
    # TODO: refer to llama_index's storage as well

    def run(self, text: str | list[str] | Document | list[Document]) -> None:
        input_: list[Document] = []
        if not isinstance(text, list):
            text = [text]

        for item in text:
            if isinstance(item, str):
                input_.append(Document(text=item, id_=str(uuid.uuid4())))
            elif isinstance(item, Document):
                input_.append(item)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )

        embeddings = self.embedding(input_)
        self.vector_store.add(
            embeddings=embeddings,
            ids=[t.id_ for t in input_],
        )
        if self.doc_store:
            self.doc_store.add(input_)

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
