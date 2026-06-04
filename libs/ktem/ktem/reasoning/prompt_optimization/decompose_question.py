import logging
from dataclasses import dataclass, field

from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import RewriteQuestionPipeline
from pydantic import BaseModel, Field

from kotaemon.base import Document, HumanMessage, SystemMessage
from kotaemon.llms import ChatLLM

logger = logging.getLogger(__name__)


class SubQuery(BaseModel):
    sub_query: str = Field(
        ...,
        description="A very specific query against the database.",
    )


@dataclass(kw_only=True)
class DecomposeQuestionPipeline(RewriteQuestionPipeline):
    llm: ChatLLM = field(
        default_factory=lambda: llms.get("openai-gpt4-turbo", llms.get_default())
    )
    DECOMPOSE_SYSTEM_PROMPT_TEMPLATE: str = (
        "You are an expert at converting user complex questions into sub questions. "
        "Perform query decomposition using provided function_call. "
        "Given a user question, break it down into the most specific sub"
        " questions you can (at most 3) "
        "which will help you answer the original question. "
        "Each sub question should be about a single concept/fact/idea. "
        "If there are acronyms or words you are not familiar with, "
        "do not try to rephrase them."
    )
    prompt_template: str = DECOMPOSE_SYSTEM_PROMPT_TEMPLATE

    def create_prompt(self, question):
        schema = SubQuery.model_json_schema()
        function = {
            "name": schema["title"],
            "description": schema["description"],
            "parameters": schema,
        }
        llm_kwargs = {
            "tools": [{"type": "function", "function": function}],
            "tool_choice": "auto",
            "tools_pydantic": [SubQuery],
        }
        messages = [
            SystemMessage(content=self.prompt_template),
            HumanMessage(content=question),
        ]
        return messages, llm_kwargs

    def run(self, question: str) -> list:  # type: ignore
        messages, llm_kwargs = self.create_prompt(question)
        result = self.llm(messages, **llm_kwargs)
        tool_calls = result.additional_kwargs.get("tool_calls", None)
        sub_queries = []
        if tool_calls:
            for tool_call in tool_calls:
                if "function" in tool_call:
                    function_output = tool_call["function"]["arguments"]
                else:
                    function_output = tool_call["args"]

                if isinstance(function_output, str):
                    sub_query = SubQuery.parse_raw(function_output).sub_query
                else:
                    sub_query = SubQuery.parse_obj(function_output).sub_query

                sub_queries.append(Document(content=sub_query))
        return sub_queries
