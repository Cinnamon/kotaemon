from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from kotaemon.base import Document
from kotaemon.evaluate.context_relevance import ContextRelevanceEvaluator

from .llm import LLMReranking


class LLMTrulensScoring(LLMReranking):
    context_relevance_evaluator: ContextRelevanceEvaluator
    top_k: int = 3
    concurrent: bool = True

    def run(
        self,
        documents: list[Document],
        query: str,
    ) -> list[Document]:
        """Filter down documents based on their relevance to the query."""
        filtered_docs = []

        documents = sorted(documents, key=lambda doc: doc.get_content())
        if self.concurrent:
            with ThreadPoolExecutor() as executor:
                futures = []
                for doc in documents:
                    futures.append(
                        executor.submit(
                            lambda: self.context_relevance_evaluator(doc, query)
                        )
                    )

                results = [future.result() for future in futures]
        else:
            results = []
            for doc in documents:
                results.append(self.context_relevance_evaluator(doc, query))

        for score, doc in zip(results, documents):
            doc.metadata["context_relevance"] = score
            filtered_docs.append(doc)

        # prevent returning empty result
        if len(filtered_docs) == 0:
            filtered_docs = documents[: self.top_k]

        return filtered_docs
