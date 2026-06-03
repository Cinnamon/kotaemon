from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import time
import warnings
from collections import defaultdict
from functools import cached_property
from typing import Optional, Sequence

from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)
from llama_index.core.vector_stores.types import VectorStoreQueryMode
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotaemon.base import RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.rankings import BaseReranking, LLMReranking
from kotaemon.indices.retriever.base import BaseRetriever
from kotaemon.indices.vectorindex import VectorRetrieval

logger = logging.getLogger(__name__)

@dataclass(kw_only=True)
class DocumentRetrievalPipeline(BaseRetriever):
    """Retrieve relevant document excerpts from a vector/doc store.

    Args:
        embedding: embedding model used for vector search
        rerankers: optional reranking pipelines applied after retrieval
        llm_scorer: optional LLM-based relevance scorer
        get_extra_table: if True, also retrieve surrounding table nodes
        top_k: number of documents to return
        mmr: whether to apply MMR diversification
        retrieval_mode: one of ``vector``, ``text``, or ``hybrid``
    """

    embedding: BaseEmbeddings
    rerankers: Sequence[BaseReranking] = ()
    llm_scorer: LLMReranking | None
    get_extra_table: bool = False
    mmr: bool = False
    top_k: int = 5
    retrieval_mode: str = "hybrid"
    doc_ids: Optional[list[str]] = None

    @cached_property
    def vector_retrieval(self) -> VectorRetrieval:
        return VectorRetrieval(
            embedding=self.embedding,
            vector_store=self.VS,
            doc_store=self.DS,
            retrieval_mode=self.retrieval_mode,  # type: ignore
            rerankers=self.rerankers,
        )

    def __call__(self, text: str, doc_ids: Optional[list[str]] = None, *args, **kwargs) -> list[RetrievedDocument]:
        return self.run(text, doc_ids, *args, **kwargs)

    def run(
        self,
        text: str,
        doc_ids: Optional[list[str]] = None,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        """Retrieve document excerpts similar to *text*.

        Args:
            text: the query text
            doc_ids: restrict retrieval to these source document ids
        """
        doc_ids = doc_ids or self.doc_ids

        if doc_ids:
            flatten_doc_ids: list[str] = []
            for doc_id in doc_ids:
                if doc_id is None:
                    raise ValueError("No document is selected")
                if doc_id.startswith("["):
                    flatten_doc_ids.extend(json.loads(doc_id))
                else:
                    flatten_doc_ids.append(doc_id)
            doc_ids = flatten_doc_ids

        print("searching in doc_ids", doc_ids)
        if not doc_ids:
            logger.info(f"Skip retrieval because of no selected files: {self}")
            return []

        retrieval_kwargs: dict = {}
        with Session(self.engine) as session:
            stmt = select(self.Index).where(
                self.Index.relation_type == "document",
                self.Index.source_id.in_(doc_ids),
            )
            results = session.execute(stmt)
            chunk_ids = [r[0].target_id for r in results.all()]

        retrieval_kwargs["do_extend"] = True
        retrieval_kwargs["scope"] = chunk_ids
        retrieval_kwargs["filters"] = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="file_id",
                    value=doc_ids,
                    operator=FilterOperator.IN,
                )
            ],
            condition=FilterCondition.OR,
        )

        if self.mmr:
            retrieval_kwargs["mode"] = VectorStoreQueryMode.MMR
            retrieval_kwargs["mmr_threshold"] = 0.5

        s_time = time.time()
        print(f"retrieval_kwargs: {retrieval_kwargs.keys()}")
        docs = self.vector_retrieval(text=text, top_k=self.top_k, **retrieval_kwargs)
        print("retrieval step took", time.time() - s_time)

        if not self.get_extra_table:
            return docs

        table_pages: dict = defaultdict(list)
        retrieved_id = {doc.doc_id for doc in docs}
        for doc in docs:
            if "page_label" not in doc.metadata:
                continue
            if "file_name" not in doc.metadata:
                warnings.warn(
                    "file_name not in metadata while page_label is in metadata:"
                    f" {doc.metadata}"
                )
            table_pages[doc.metadata["file_name"]].append(
                doc.metadata["page_label"]
            )

        queries: list[dict] = [
            {"$and": [{"file_name": {"$eq": fn}}, {"page_label": {"$in": pls}}]}
            for fn, pls in table_pages.items()
        ]
        if queries:
            try:
                extra_docs = self.vector_retrieval(
                    text="",
                    top_k=50,
                    where=queries[0] if len(queries) == 1 else {"$or": queries},
                )
                for doc in extra_docs:
                    if doc.doc_id not in retrieved_id:
                        docs.append(doc)
            except Exception:
                print("Error retrieving additional tables")

        return docs

    def generate_relevant_scores(
        self, query: str, documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        """Re-score documents using the LLM scorer if configured."""
        return (
            documents
            if not self.llm_scorer
            else self.llm_scorer(documents=documents, query=query)
        )
