from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional, Sequence, cast

from theflow.settings import settings as flowsettings

from kotaemon.base import BaseComponent, Document, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.storages import BaseDocumentStore, BaseVectorStore

from .base import BaseIndexing, BaseRetrieval
from .rankings import BaseReranking

VECTOR_STORE_FNAME = "vectorstore"
DOC_STORE_FNAME = "docstore"


class VectorIndexing(BaseIndexing):
    """Ingest the document, run through the embedding, and store the embedding in a
    vector store.

    This pipeline supports the following set of inputs:
        - List of documents
        - List of texts
    """

    cache_dir: Optional[str] = getattr(flowsettings, "KH_CHUNKS_OUTPUT_DIR", None)
    vector_store: BaseVectorStore
    doc_store: Optional[BaseDocumentStore] = None
    embedding: BaseEmbeddings
    count_: int = 0

    def to_retrieval_pipeline(self, *args, **kwargs):
        """Convert the indexing pipeline to a retrieval pipeline"""
        return VectorRetrieval(
            vector_store=self.vector_store,
            doc_store=self.doc_store,
            embedding=self.embedding,
            **kwargs,
        )

    def to_qa_pipeline(self, *args, **kwargs):
        from .qa import CitationQAPipeline

        return TextVectorQA(
            retrieving_pipeline=self.to_retrieval_pipeline(**kwargs),
            qa_pipeline=CitationQAPipeline(**kwargs),
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

        print(f"Getting embeddings for {len(input_)} nodes")
        embeddings = self.embedding(input_)
        print("Adding embeddings to vector store")
        self.vector_store.add(
            embeddings=embeddings,
            ids=[t.doc_id for t in input_],
        )
        if self.doc_store:
            print("Adding documents to doc store")
            self.doc_store.add(input_)
        # save the chunks content into markdown format
        if self.cache_dir:
            file_name = Path(input_[0].metadata["file_name"])
            for i in range(len(input_)):
                markdown_content = ""
                if "page_label" in input_[i].metadata:
                    page_label = str(input_[i].metadata["page_label"])
                    markdown_content += f"Page label: {page_label}"
                if "file_name" in input_[i].metadata:
                    filename = input_[i].metadata["file_name"]
                    markdown_content += f"\nFile name: {filename}"
                if "section" in input_[i].metadata:
                    section = input_[i].metadata["section"]
                    markdown_content += f"\nSection: {section}"
                if "type" in input_[i].metadata:
                    if input_[i].metadata["type"] == "image":
                        image_origin = input_[i].metadata["image_origin"]
                        image_origin = f'<p><img src="{image_origin}"></p>'
                        markdown_content += f"\nImage origin: {image_origin}"
                if input_[i].text:
                    markdown_content += f"\ntext:\n{input_[i].text}"

                with open(
                    Path(self.cache_dir) / f"{file_name.stem}_{self.count_+i}.md", "w"
                ) as f:
                    f.write(markdown_content)
            self.count_ += len(input_)


class VectorRetrieval(BaseRetrieval):
    """Retrieve list of documents from vector store"""

    vector_store: BaseVectorStore
    doc_store: Optional[BaseDocumentStore] = None
    embedding: BaseEmbeddings
    rerankers: Sequence[BaseReranking] = []
    top_k: int = 5
    retrieval_mode: str = "hybrid"  # vector, text, hybrid

    def run(
        self, text: str | Document, top_k: Optional[int] = None, **kwargs
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

        result: list[RetrievedDocument] = []
        # TODO: should declare scope directly in the run params
        scope = kwargs.pop("scope", None)
        emb: list[float]

        if self.retrieval_mode == "vector":
            emb = self.embedding(text)[0].embedding
            _, scores, ids = self.vector_store.query(
                embedding=emb, top_k=top_k, **kwargs
            )
            docs = self.doc_store.get(ids)
            result = [
                RetrievedDocument(**doc.to_dict(), score=score)
                for doc, score in zip(docs, scores)
            ]
        elif self.retrieval_mode == "text":
            query = text.text if isinstance(text, Document) else text
            docs = self.doc_store.query(query, top_k=top_k, doc_ids=scope)
            result = [RetrievedDocument(**doc.to_dict(), score=-1.0) for doc in docs]
        elif self.retrieval_mode == "hybrid":
            # similartiy search section
            emb = self.embedding(text)[0].embedding
            _, vs_scores, vs_ids = self.vector_store.query(
                embedding=emb, top_k=top_k, **kwargs
            )
            vs_docs = self.doc_store.get(vs_ids)

            # full-text search section
            query = text.text if isinstance(text, Document) else text
            docs = self.doc_store.query(query, top_k=top_k, doc_ids=scope)
            result = [
                RetrievedDocument(**doc.to_dict(), score=-1.0)
                for doc in docs
                if doc not in vs_ids
            ]
            result += [
                RetrievedDocument(**doc.to_dict(), score=score)
                for doc, score in zip(vs_docs, vs_scores)
            ]

        # use additional reranker to re-order the document list
        if self.rerankers and text:
            for reranker in self.rerankers:
                result = reranker(documents=result, query=text)

        return result


class TextVectorQA(BaseComponent):
    retrieving_pipeline: BaseRetrieval
    qa_pipeline: BaseComponent

    def run(self, question, **kwargs):
        retrieved_documents = self.retrieving_pipeline(question, **kwargs)
        return self.qa_pipeline(question, retrieved_documents, **kwargs)
