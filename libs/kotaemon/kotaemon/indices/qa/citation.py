from typing import List

from pydantic import BaseModel, Field

from kotaemon.base import BaseComponent
from kotaemon.base.schema import HumanMessage, SystemMessage
from kotaemon.llms import BaseLLM


class CiteEvidence(BaseModel):
    """List of evidences (maximum 5) to support the answer."""

    evidences: List[str] = Field(
        ...,
        description=(
            "Each source should be a direct quote from the context, "
            "as a substring of the original content (max 15 words)."
        ),
    )


class CitationPipeline(BaseComponent):
    """Citation pipeline to extract cited evidences from source
    (based on input question)"""

    llm: BaseLLM

    def run(self, context: str, question: str):
        return self.invoke(context, question)

    def prepare_llm(self, context: str, question: str):
        schema = CiteEvidence.schema()
        function = {
            "name": schema["title"],
            "description": schema["description"],
            "parameters": schema,
        }
        llm_kwargs = {
            "tools": [{"type": "function", "function": function}],
            "tool_choice": "required",
            "tools_pydantic": [CiteEvidence],
        }
        messages = [
            SystemMessage(
                content=(
                    "You are a world class algorithm to answer "
                    "questions with correct and exact citations."
                )
            ),
            HumanMessage(
                content=(
                    "Answer question using the following context. "
                    "Use the provided function CiteEvidence() to cite your sources."
                )
            ),
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
            if not llm_output.additional_kwargs.get("tool_calls"):
                return None

            first_func = llm_output.additional_kwargs["tool_calls"][0]

            if "function" in first_func:
                # openai and cohere format
                function_output = first_func["function"]["arguments"]
            else:
                # anthropic format
                function_output = first_func["args"]

            print("CitationPipeline:", function_output)

            if isinstance(function_output, str):
                output = CiteEvidence.parse_raw(function_output)
            else:
                output = CiteEvidence.parse_obj(function_output)
        except Exception as e:
            print(e)
            return None

        return output

    async def ainvoke(self, context: str, question: str):
        raise NotImplementedError()
