from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from langchain.output_parsers.boolean import BooleanOutputParser

from kotaemon.base import Document

from .llm import LLMReranking


class LLMScoring(LLMReranking):
    def run(
        self,
        documents: list[Document],
        query: str,
    ) -> list[Document]:
        """Filter down documents based on their relevance to the query."""
        filtered_docs: list[Document] = []
        output_parser = BooleanOutputParser()

        if self.concurrent:
            with ThreadPoolExecutor() as executor:
                futures = []
                for doc in documents:
                    _prompt = self.prompt_template.populate(
                        question=query, context=doc.get_content()
                    )
                    futures.append(executor.submit(lambda: self.llm(_prompt)))

                results = [future.result() for future in futures]
        else:
            results = []
            for doc in documents:
                _prompt = self.prompt_template.populate(
                    question=query, context=doc.get_content()
                )
                results.append(self.llm(_prompt))

        for result, doc in zip(results, documents):
            score = np.exp(np.average(result.logprobs))
            include_doc = output_parser.parse(result.text)
            if include_doc:
                doc.metadata["llm_reranking_score"] = score
            else:
                doc.metadata["llm_reranking_score"] = 1 - score
            filtered_docs.append(doc)

        # prevent returning empty result
        if len(filtered_docs) == 0:
            filtered_docs = documents[: self.top_k]

        return filtered_docs
