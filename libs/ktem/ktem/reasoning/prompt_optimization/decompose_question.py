import json
import logging
import re

from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import RewriteQuestionPipeline
from pydantic import BaseModel, Field

from kotaemon.base import Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM

logger = logging.getLogger(__name__)


def _is_tool_not_supported_error(error: Exception) -> bool:
    """Check if the error indicates the model does not support tools."""
    error_msg = str(error).lower()
    return (
        "does not support tools" in error_msg
        or "tool use is not supported" in error_msg
        or "tools are not supported" in error_msg
    )


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
    # Fallback prompt for models that don't support tools
    DECOMPOSE_FALLBACK_PROMPT_TEMPLATE = (
        "You are an expert at converting user complex questions into sub questions. "
        "Given a user question, break it down into the most specific sub"
        " questions you can (at most 3) "
        "which will help you answer the original question. "
        "Each sub question should be about a single concept/fact/idea. "
        "If there are acronyms or words you are not familiar with, "
        "do not try to rephrase them.\n\n"
        "Output your sub-questions as a JSON array of objects, where each object has "
        'a "sub_query" field. Example:\n'
        '[{"sub_query": "What is X?"}, {"sub_query": "How does Y work?"}]\n\n'
        "Only output the JSON array, no other text."
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

    def _run_with_fallback(self, question: str) -> list:
        """Fallback method for models that don't support tools.

        Uses plain text prompting to decompose the question.
        """
        messages = [
            SystemMessage(content=self.DECOMPOSE_FALLBACK_PROMPT_TEMPLATE),
            HumanMessage(content=question),
        ]

        result = self.llm(messages)
        text = result.text.strip()

        # Try to parse the response as JSON
        sub_queries = []
        try:
            # Try to extract JSON array from the response
            # Handle cases where model adds extra text around the JSON
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                for item in parsed:
                    if isinstance(item, dict) and "sub_query" in item:
                        sub_queries.append(Document(content=item["sub_query"]))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse fallback response as JSON: {e}")
            # If JSON parsing fails, try to extract questions from the text
            # by looking for numbered items or question marks
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                # Remove common prefixes like "1.", "- ", "* "
                line = re.sub(r"^[\d]+[.)\]]\s*", "", line)
                line = re.sub(r"^[-*•]\s*", "", line)
                if line and ("?" in line or len(line) > 10):
                    sub_queries.append(Document(content=line))

        return sub_queries[:3]  # Limit to 3 sub-questions

    def run(self, question: str) -> list:  # type: ignore
        messages, llm_kwargs = self.create_prompt(question)

        try:
            result = self.llm(messages, **llm_kwargs)
        except Exception as e:
            if _is_tool_not_supported_error(e):
                logger.warning(
                    f"Model does not support tools, falling back to text-based "
                    f"decomposition: {e}"
                )
                return self._run_with_fallback(question)
            raise

        tool_calls = result.additional_kwargs.get("tool_calls", None)
        sub_queries = []
        if tool_calls:
            for tool_call in tool_calls:
                if "function" in tool_call:
                    # openai and cohere format
                    function_output = tool_call["function"]["arguments"]
                else:
                    # anthropic format
                    function_output = tool_call["args"]

                if isinstance(function_output, str):
                    sub_query = SubQuery.parse_raw(function_output).sub_query
                else:
                    sub_query = SubQuery.parse_obj(function_output).sub_query

                sub_queries.append(
                    Document(
                        content=sub_query,
                    )
                )

        return sub_queries
