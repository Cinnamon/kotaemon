import os
from abc import abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Union

from langchain.output_parsers.boolean import BooleanOutputParser

from ..base import BaseComponent
from ..base.schema import Document
from ..llms import PromptTemplate
from ..llms.chats.base import ChatLLM
from ..llms.completions.base import LLM

BaseLLM = Union[ChatLLM, LLM]


class BaseRerankingPipeline(BaseComponent):
    @abstractmethod
    def run(self, documents: List[Document], query: str) -> List[Document]:
        """Main method to transform list of documents
        (re-ranking, filtering, etc)"""
        ...


class CohereReranking(BaseRerankingPipeline):
    model_name: str = "rerank-multilingual-v2.0"
    cohere_api_key: Optional[str] = None
    top_k: int = 1

    def run(self, documents: List[Document], query: str) -> List[Document]:
        """Use Cohere Reranker model to re-order documents
        with their relevance score"""
        try:
            import cohere
        except ImportError:
            raise ImportError(
                "Please install Cohere " "`pip install cohere` to use Cohere Reranking"
            )

        cohere_api_key = (
            self.cohere_api_key if self.cohere_api_key else os.environ["COHERE_API_KEY"]
        )
        cohere_client = cohere.Client(cohere_api_key)

        # output documents
        compressed_docs = []
        if len(documents) > 0:  # to avoid empty api call
            _docs = [d.content for d in documents]
            results = cohere_client.rerank(
                model=self.model_name, query=query, documents=_docs, top_n=self.top_k
            )
            for r in results:
                doc = documents[r.index]
                doc.metadata["relevance_score"] = r.relevance_score
                compressed_docs.append(doc)

        return compressed_docs


RERANK_PROMPT_TEMPLATE = """Given the following question and context,
return YES if the context is relevant to the question and NO if it isn't.

> Question: {question}
> Context:
>>>
{context}
>>>
> Relevant (YES / NO):"""


class LLMReranking(BaseRerankingPipeline):
    llm: BaseLLM
    prompt_template: PromptTemplate = PromptTemplate(template=RERANK_PROMPT_TEMPLATE)
    top_k: int = 3
    concurrent: bool = True

    def run(
        self,
        documents: List[Document],
        query: str,
    ) -> List[Document]:
        """Filter down documents based on their relevance to the query."""
        filtered_docs = []
        output_parser = BooleanOutputParser()

        if self.concurrent:
            with ThreadPoolExecutor() as executor:
                futures = []
                for doc in documents:
                    _prompt = self.prompt_template.populate(
                        question=query, context=doc.get_content()
                    )
                    futures.append(executor.submit(lambda: self.llm(_prompt).text))

                results = [future.result() for future in futures]
        else:
            results = []
            for doc in documents:
                _prompt = self.prompt_template.populate(
                    question=query, context=doc.get_content()
                )
                results.append(self.llm(_prompt).text)

        # use Boolean parser to extract relevancy output from LLM
        results = [output_parser.parse(result) for result in results]
        for include_doc, doc in zip(results, documents):
            if include_doc:
                filtered_docs.append(doc)

        # prevent returning empty result
        if len(filtered_docs) == 0:
            filtered_docs = documents[: self.top_k]

        return filtered_docs
