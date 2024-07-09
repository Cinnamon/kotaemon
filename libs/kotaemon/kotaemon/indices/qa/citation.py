from typing import Iterator, List

from pydantic import BaseModel, Field

from kotaemon.base import BaseComponent
from kotaemon.base.schema import HumanMessage, SystemMessage
from kotaemon.llms import BaseLLM


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

    def run(self, context: str, question: str):
        return self.invoke(context, question)

    def prepare_llm(self, context: str, question: str):
        schema = QuestionAnswer.schema()
        function = {
            "name": schema["title"],
            "description": schema["description"],
            "parameters": schema,
        }
        llm_kwargs = {
            "tools": [{"type": "function", "function": function}],
            "tool_choice": "auto",
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
        return messages, llm_kwargs

    def invoke(self, context: str, question: str):
        messages, llm_kwargs = self.prepare_llm(context, question)
        try:
            print("CitationPipeline: invoking LLM")
            llm_output = self.get_from_path("llm").invoke(messages, **llm_kwargs)
            print("CitationPipeline: finish invoking LLM")
            if not llm_output.messages or not llm_output.additional_kwargs.get(
                "tool_calls"
            ):
                return None
            function_output = llm_output.additional_kwargs["tool_calls"][0]["function"][
                "arguments"
            ]
            output = QuestionAnswer.parse_raw(function_output)
        except Exception as e:
            print(e)
            return None

        return output

    async def ainvoke(self, context: str, question: str):
        messages, llm_kwargs = self.prepare_llm(context, question)

        try:
            print("CitationPipeline: async invoking LLM")
            llm_output = await self.get_from_path("llm").ainvoke(messages, **llm_kwargs)
            print("CitationPipeline: finish async invoking LLM")
            function_output = llm_output.additional_kwargs["tool_calls"][0]["function"][
                "arguments"
            ]
            output = QuestionAnswer.parse_raw(function_output)
        except Exception as e:
            print(e)
            return None

        return output
