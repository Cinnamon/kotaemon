from typing import Iterator, List, Union

from langchain.schema.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from kotaemon.base import BaseComponent

from ..llms.chats.base import ChatLLM
from ..llms.completions.base import LLM

BaseLLM = Union[ChatLLM, LLM]


class FactWithEvidence(BaseModel):
    """Class representing a single statement.

    Each fact has a body and a list of sources.
    If there are multiple facts make sure to break them apart
    such that each one only uses a set of sources that are relevant to it.
    """

    fact: str = Field(..., description="Body of the sentence, as part of a response")
    substring_quote: List[str] = Field(
        ...,
        description=(
            "Each source should be a direct quote from the context, "
            "as a substring of the original content"
        ),
    )

    def _get_span(self, quote: str, context: str, errs: int = 100) -> Iterator[str]:
        import regex

        minor = quote
        major = context

        errs_ = 0
        s = regex.search(f"({minor}){{e<={errs_}}}", major)
        while s is None and errs_ <= errs:
            errs_ += 1
            s = regex.search(f"({minor}){{e<={errs_}}}", major)

        if s is not None:
            yield from s.spans()

    def get_spans(self, context: str) -> Iterator[str]:
        for quote in self.substring_quote:
            yield from self._get_span(quote, context)


class QuestionAnswer(BaseModel):
    """A question and its answer as a list of facts each one should have a source.
    each sentence contains a body and a list of sources."""

    question: str = Field(..., description="Question that was asked")
    answer: List[FactWithEvidence] = Field(
        ...,
        description=(
            "Body of the answer, each fact should be "
            "its separate object with a body and a list of sources"
        ),
    )


class CitationPipeline(BaseComponent):
    """Citation pipeline to extract cited evidences from source
    (based on input question)"""

    llm: BaseLLM

    def run(
        self,
        context: str,
        question: str,
    ) -> QuestionAnswer:
        schema = QuestionAnswer.schema()
        function = {
            "name": schema["title"],
            "description": schema["description"],
            "parameters": schema,
        }
        llm_kwargs = {
            "functions": [function],
            "function_call": {"name": function["name"]},
        }
        messages = [
            SystemMessage(
                content=(
                    "You are a world class algorithm to answer "
                    "questions with correct and exact citations."
                )
            ),
            HumanMessage(content="Answer question using the following context"),
            HumanMessage(content=context),
            HumanMessage(content=f"Question: {question}"),
            HumanMessage(
                content=(
                    "Tips: Make sure to cite your sources, "
                    "and use the exact words from the context."
                )
            ),
        ]

        llm_output = self.llm(messages, **llm_kwargs)
        function_output = llm_output.messages[0].additional_kwargs["function_call"][
            "arguments"
        ]
        output = QuestionAnswer.parse_raw(function_output)

        return output
