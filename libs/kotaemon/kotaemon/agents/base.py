from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from kotaemon.llms import BaseLLM, PromptTemplate

from .io import AgentOutput, AgentType
from .tools import BaseTool


@dataclass(kw_only=True)
class BaseAgent:
    name: str
    agent_type: AgentType
    description: str
    llm: Optional[BaseLLM] = None
    prompt_template: Optional[Union[PromptTemplate, dict[str, PromptTemplate]]] = None
    plugins: list[BaseTool] = field(default_factory=list)

    @staticmethod
    def safeguard_run(run_func, *args, **kwargs):
        def wrapper(self, *args, **kwargs):
            try:
                return run_func(self, *args, **kwargs)
            except Exception as e:
                return AgentOutput(
                    text="",
                    agent_type=self.agent_type,
                    status="failed",
                    error=str(e),
                )
        return wrapper

    def add_tools(self, tools: list[BaseTool]) -> None:
        self.plugins.extend(tools)

    def run(self, *args, **kwargs) -> AgentOutput | list[AgentOutput]:
        raise NotImplementedError()
