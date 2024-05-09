from typing import AnyStr, Optional, Type

from pydantic import BaseModel, Field

from kotaemon.agents.tools.base import ToolException
from kotaemon.llms import BaseLLM

from .base import BaseTool


class LLMArgs(BaseModel):
    query: str = Field(..., description="a search question or prompt")


class LLMTool(BaseTool):
    name: str = "llm"
    description: str = (
        "A pretrained LLM like yourself. Useful when you need to act with "
        "general world knowledge and common sense. Prioritize it when you "
        "are confident in solving the problem "
        "yourself. Input can be any instruction."
    )
    llm: BaseLLM
    args_schema: Optional[Type[BaseModel]] = LLMArgs

    def _run_tool(self, query: AnyStr) -> str:
        output = None
        try:
            response = self.llm(query)
        except ValueError:
            raise ToolException("LLM Tool call failed")
        output = response.text
        return output
