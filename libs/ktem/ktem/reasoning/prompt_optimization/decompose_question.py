import logging

from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import RewriteQuestionPipeline
from pydantic import BaseModel, Field

from kotaemon.base import Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM

logger = logging.getLogger(__name__)


class SubQuery(BaseModel):
    """Search over a database of insurance rulebooks or financial reports"""

    sub_query: str = Field(
        ...,
        description="A very specific query against the database.",
    )


class DecomposeQuestionPipeline(RewriteQuestionPipeline):
    """Decompose user complex question into multiple sub-questions

    Args:
        llm: the language model to rewrite question
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(
        default_callback=lambda _: llms.get("openai-gpt4-turbo", llms.get_default())
    )
    DECOMPOSE_SYSTEM_PROMPT_TEMPLATE = (
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
                sub_queries.append(
                    Document(
                        content=SubQuery.parse_raw(
                            tool_call["function"]["arguments"]
                        ).sub_query
                    )
                )

        return sub_queries
