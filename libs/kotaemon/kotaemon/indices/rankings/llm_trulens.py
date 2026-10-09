from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import tiktoken

from kotaemon.base import Document, HumanMessage, SystemMessage
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.llms import BaseLLM, PromptTemplate

from .llm import LLMReranking

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = PromptTemplate(
    """You are a RELEVANCE grader; providing the relevance of the given CONTEXT to the given QUESTION.
        Respond only as a number from 0 to 10 where 0 is the least relevant and 10 is the most relevant.

        A few additional scoring guidelines:

        - Long CONTEXTS should score equally well as short CONTEXTS.

        - RELEVANCE score should increase as the CONTEXTS provides more RELEVANT context to the QUESTION.

        - RELEVANCE score should increase as the CONTEXTS provides RELEVANT context to more parts of the QUESTION.

        - CONTEXT that is RELEVANT to some of the QUESTION should score of 2, 3 or 4. Higher score indicates more RELEVANCE.

        - CONTEXT that is RELEVANT to most of the QUESTION should get a score of 5, 6, 7 or 8. Higher score indicates more RELEVANCE.

        - CONTEXT that is RELEVANT to the entire QUESTION should get a score of 9 or 10. Higher score indicates more RELEVANCE.

        - CONTEXT must be relevant and helpful for answering the entire QUESTION to get a score of 10.

        - Never elaborate."""  # noqa: E501
)

USER_PROMPT_TEMPLATE = PromptTemplate(
    """QUESTION: {question}

        CONTEXT: {context}

        RELEVANCE: """
)  # noqa

PATTERN_NUMBER: re.Pattern = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)")
"""Regex that matches integers and decimals."""

MAX_CONTEXT_LEN = 7500


def validate_rating(rating) -> float:
    """Validate a rating is between 0 and 10."""

    if not 0 <= rating <= 10:
        raise ValueError("Rating must be between 0 and 10")

    return rating


def re_0_10_rating(s: str) -> float:
    """Extract a 0-10 rating from a string.

    Decimals such as "7.5" are parsed as a single number. If multiple numbers
    are found within the 0-10 range, the smallest is returned, which handles
    replies like "Out of 10, I'd say 8".

    Args:
        s: String to extract rating from.

    Returns:
        float: Extracted rating.

    Raises:
        ValueError: If no number between 0 and 10 is found in the string.
    """

    vals = []
    for match in PATTERN_NUMBER.findall(s):
        try:
            vals.append(float(validate_rating(float(match))))
        except ValueError:
            pass

    if not vals:
        raise ValueError(f"Could not parse a 0-10 rating from: {s[:100]!r}")

    return min(vals)


class LLMTrulensScoring(LLMReranking):
    llm: BaseLLM
    system_prompt_template: PromptTemplate = SYSTEM_PROMPT_TEMPLATE
    user_prompt_template: PromptTemplate = USER_PROMPT_TEMPLATE
    concurrent: bool = True
    normalize: float = 10
    trim_func: TokenSplitter = TokenSplitter.withx(
        chunk_size=MAX_CONTEXT_LEN,
        chunk_overlap=0,
        separator=" ",
        tokenizer=partial(
            tiktoken.encoding_for_model("gpt-3.5-turbo").encode,
            allowed_special=set(),
            disallowed_special="all",
        ),
    )

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
                    chunked_doc_content = self.trim_func(
                        [
                            Document(content=doc.get_content())
                            # skip metadata which cause troubles
                        ]
                    )[0].text

                    messages = []
                    messages.append(
                        SystemMessage(self.system_prompt_template.populate())
                    )
                    messages.append(
                        HumanMessage(
                            self.user_prompt_template.populate(
                                question=query, context=chunked_doc_content
                            )
                        )
                    )

                    def llm_call():
                        return self.llm(messages).text

                    futures.append(executor.submit(llm_call))

                results = [future.result() for future in futures]
        else:
            results = []
            for doc in documents:
                messages = []
                messages.append(SystemMessage(self.system_prompt_template.populate()))
                messages.append(
                    SystemMessage(
                        self.user_prompt_template.populate(
                            question=query, context=doc.get_content()
                        )
                    )
                )
                results.append(self.llm(messages).text)

        # use Boolean parser to extract relevancy output from LLM
        scores = []
        for r_idx, result in enumerate(results):
            try:
                score = re_0_10_rating(result) / self.normalize
            except ValueError:
                # an unparsable reply gets the lowest score, not a failed rerank
                logger.warning("Unparsable relevance rating, scoring 0: %.100r", result)
                score = 0.0
            scores.append((r_idx, score))
        results = scores
        results.sort(key=lambda x: x[1], reverse=True)

        for r_idx, score in results:
            doc = documents[r_idx]
            doc.metadata["llm_trulens_score"] = score
            filtered_docs.append(doc)

        print(
            "LLM rerank scores",
            [doc.metadata["llm_trulens_score"] for doc in filtered_docs],
        )

        return filtered_docs
