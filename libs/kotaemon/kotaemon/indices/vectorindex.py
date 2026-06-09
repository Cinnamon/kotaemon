from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence, cast

from kotaemon.base import Document, RetrievedDocument, Runnable
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

from .base import BaseRetrieval
from .rankings import BaseReranking, LLMReranking

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"


@dataclass(kw_only=True)
class VectorIndexing:
    vector_store: BaseVectorStore
    embedding: BaseEmbeddings
    cache_dir: Optional[str] = None
    doc_store: Optional[BaseDocumentStore] = None
    count_: int = 0

    def to_retrieval_pipeline(self, *args, **kwargs):
        return VectorRetrieval(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            **kwargs,
        )

    def write_chunk_to_file(self, docs: list[Document]):
        if not self.cache_dir:
            return
        file_name = docs[0].metadata.get("file_name")
        if not file_name:
            return
        file_name = Path(file_name)
        for i, doc in enumerate(docs):
            parts = []
            if "page_label" in doc.metadata:
                parts.append(f"Page label: {doc.metadata['page_label']}")
            if "file_name" in doc.metadata:
                parts.append(f"File name: {doc.metadata['file_name']}")
            if doc.text:
                parts.append(f"text:\n{doc.text}")
            with open(
                Path(self.cache_dir) / f"{file_name.stem}_{self.count_ + i}.md",
                "w",
                encoding="utf-8",
            ) as f:
                f.write("\n".join(parts))

    def add_to_docstore(self, docs: list[Document]):
        if self.doc_store:
            self.doc_store.add(docs)

    def add_to_vectorstore(self, docs: list[Document]):
        if self.vector_store:
            embeddings = self.embedding(docs)
            self.vector_store.add(
                embeddings=embeddings,
                ids=[t.doc_id for t in docs],
            )

    def run(self, text: str | list[str] | Document | list[Document]):
        input_: list[Document] = []
        if not isinstance(text, list):
            text = [text]
        for item in cast(list, text):
            if isinstance(item, str):
                input_.append(Document(text=item, id_=str(uuid.uuid4())))
            elif isinstance(item, Document):
                input_.append(item)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )
        self.add_to_vectorstore(input_)
        self.add_to_docstore(input_)
        self.write_chunk_to_file(input_)
        self.count_ += len(input_)


@dataclass(kw_only=True)
class VectorRetrieval(BaseRetrieval):
    vector_store: BaseVectorStore
    embedding: BaseEmbeddings
    doc_store: Optional[BaseDocumentStore] = None
    rerankers: Sequence[BaseReranking] = field(default_factory=list)
    top_k: int = 5
    first_round_top_k_mult: int = 10
    retrieval_mode: str = "hybrid"

    def _filter_docs(
        self, documents: list[RetrievedDocument], top_k: int | None = None
    ):
        return documents[:top_k] if top_k else documents

    def run(
        self, text: str | Document, top_k: Optional[int] = None, **kwargs
    ) -> list[RetrievedDocument]:
        if top_k is None:
            top_k = self.top_k
        do_extend = kwargs.pop("do_extend", False)
        kwargs.pop("thumbnail_count", 3)
        top_k_first_round = top_k * self.first_round_top_k_mult if do_extend else top_k
        if self.doc_store is None:
            raise ValueError("doc_store is not provided.")

        result: list[RetrievedDocument] = []
        scope = kwargs.pop("scope", None)

        if self.retrieval_mode == "vector":
            emb = self.embedding(text)[0].embedding
            _, scores, ids = self.vector_store.query(
                embedding=emb, top_k=top_k_first_round, doc_ids=scope, **kwargs
            )
            docs = self.doc_store.get(ids)
            result = [
                RetrievedDocument(**doc.to_dict(), score=score)
                for doc, score in zip(docs, scores)
            ]
        elif self.retrieval_mode == "text":
            query = text.text if isinstance(text, Document) else text
            docs = (
                self.doc_store.query(query, top_k=top_k_first_round, doc_ids=scope)
                if scope
                else []
            )
            result = [RetrievedDocument(**doc.to_dict(), score=-1.0) for doc in docs]
        elif self.retrieval_mode == "hybrid":
            emb = self.embedding(text)[0].embedding
            vs_docs, vs_ids, vs_scores = [], [], []

            def query_vectorstore():
                nonlocal vs_docs, vs_scores, vs_ids
                assert self.doc_store is not None
                _, vs_scores, vs_ids = self.vector_store.query(
                    embedding=emb, top_k=top_k_first_round, doc_ids=scope, **kwargs
                )
                if vs_ids:
                    vs_docs = self.doc_store.get(vs_ids)

            ds_docs: list[RetrievedDocument] = []

            def query_docstore():
                nonlocal ds_docs
                assert self.doc_store is not None
                query = text.text if isinstance(text, Document) else text
                if scope:
                    ds_docs = self.doc_store.query(
                        query, top_k=top_k_first_round, doc_ids=scope
                    )

            t1 = threading.Thread(target=query_vectorstore)
            t2 = threading.Thread(target=query_docstore)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            result = [
                RetrievedDocument(**doc.to_dict(), score=-1.0)
                for doc in ds_docs
                if doc not in vs_ids
            ]
            result += [
                RetrievedDocument(**doc.to_dict(), score=score)
                for doc, score in zip(vs_docs, vs_scores)
            ]

        if self.rerankers and text:
            for reranker in self.rerankers:
                if isinstance(reranker, LLMReranking):
                    result = self._filter_docs(result, top_k=top_k)
                result = reranker.run(documents=result, query=text)

        result = self._filter_docs(result, top_k=top_k)
        return result


@dataclass(kw_only=True)
class TextVectorQA:
    retrieving_pipeline: BaseRetrieval
    qa_pipeline: Runnable

    def run(self, question, **kwargs):
        retrieved_documents = self.retrieving_pipeline(question, **kwargs)
        return self.qa_pipeline(question, retrieved_documents, **kwargs)
