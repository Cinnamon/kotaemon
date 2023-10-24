from typing import AnyStr, Optional, Type, Union

from pydantic import BaseModel, Field

from kotaemon.llms.chats.base import ChatLLM
from kotaemon.llms.chats.openai import AzureChatOpenAI
from kotaemon.llms.completions.base import LLM

from .base import BaseTool, ToolException

BaseLLM = Union[ChatLLM, LLM]


class LLMArgs(BaseModel):
    query: str = Field(..., description="a search question or prompt")


class LLMTool(BaseTool):
    name = "llm"
    description = (
        "A pretrained LLM like yourself. Useful when you need to act with "
        "general world knowledge and common sense. Prioritize it when you "
        "are confident in solving the problem "
        "yourself. Input can be any instruction."
    )
    llm: BaseLLM = AzureChatOpenAI()
    args_schema: Optional[Type[BaseModel]] = LLMArgs

    def _run_tool(self, query: AnyStr) -> str:
        output = None
        try:
            response = self.llm(query)
        except ValueError:
            raise ToolException("LLM Tool call failed")
        output = response.text
        return output
