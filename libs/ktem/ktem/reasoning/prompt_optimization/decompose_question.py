from ktem.llms.manager import llms
from ktem.reasoning.prompt_optimization.rewrite_question import RewriteQuestionPipeline
from langchain.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from kotaemon.base import Document, HumanMessage, Node, SystemMessage
from kotaemon.llms import ChatLLM

DEFAULT_DECOMPOSE_PROMPT = (
    "Given the following question, perform query decomposition. "
    "Given a user question, break it down into the most specific sub questions you can "
    "which will later help you answer the original question"
    "Each sub question should be about a single concept/fact/idea."
    "Keep the sub question as concise as possible. "
    "Give answer in {lang}\n"
    "Original question: {question}\n"
    "Sub questions: "
)
system_prompt_template = (
    "You are an expert at converting user complex questions into sub questions."
    "You have access to a database of insurance rulebooks and financial reports"
    "for building LLM-powered applications."
    "Perform query decomposition. "
    "Given a user question, break it down into the most specific sub questions you can"
    "which will help you answer the original question. "
    "Each sub question should be about a single concept/fact/idea."
    "If there are acronyms or words you are not familiar with, "
    "do not try to rephrase them."
)


class SubQuery(BaseModel):
    """Search over a database of insurance rulebooks or financial reports"""

    sub_query: str = Field(
        ...,
        description="A very specific query against the database.",
    )


class DecomposeQuestionPipeline(RewriteQuestionPipeline):
    """Rewrite user question

    Args:
        llm: the language model to rewrite question
        rewrite_template: the prompt template for llm to paraphrase a text input
        lang: the language of the answer. Currently support English and Japanese
    """

    llm: ChatLLM = Node(
        default_callback=lambda _: llms.get("openai-gpt4-turbo", llms.get_default())
    )
    rewrite_template: str = DEFAULT_DECOMPOSE_PROMPT
    lang: str = "English"
    final_prompt: ChatPromptTemplate

    def create_prompt(self, question):
        schema = SubQuery.schema()
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
            SystemMessage(content=system_prompt_template),
            HumanMessage(content=question),
        ]

        return messages, llm_kwargs

    def run(self, question: str) -> list:  # type: ignore
        messages, llm_kwargs = self.create_prompt(question)
        result = self.llm(messages, **llm_kwargs)
        tool_calls = result.additional_kwargs["tool_calls"]
        sub_queries = []
        for tool_call in tool_calls:
            sub_queries.append(
                Document(
                    content=SubQuery.parse_raw(
                        tool_call["function"]["arguments"]
                    ).sub_query
                )
            )

        return sub_queries

    @classmethod
    def get_pipeline(cls):
        pipeline = cls()
        return pipeline
