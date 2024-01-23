from typing import Optional, Union

from kotaemon.base import BaseComponent, Node, Param
from kotaemon.llms import BaseLLM, PromptTemplate

from .io import AgentOutput, AgentType
from .tools import BaseTool


class BaseAgent(BaseComponent):
    """Define base agent interface"""

    name: str = Param(help="Name of the agent.")
    agent_type: AgentType = Param(help="Agent type, must be one of AgentType")
    description: str = Param(
        help=(
            "Description used to tell the model how/when/why to use the agent. You can"
            " provide few-shot examples as a part of the description. This will be"
            " input to the prompt of LLM."
        )
    )
    llm: Optional[BaseLLM] = Node(
        help=(
            "LLM to be used for the agent (optional). LLM must implement BaseLLM"
            " interface."
        )
    )
    prompt_template: Optional[Union[PromptTemplate, dict[str, PromptTemplate]]] = Param(
        help="A prompt template or a dict to supply different prompt to the agent"
    )
    plugins: list[BaseTool] = Param(
        default_callback=lambda _: [],
        help="List of plugins / tools to be used in the agent",
    )

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
        """Helper method to add tools and update agent state if needed"""
        self.plugins.extend(tools)

    def run(self, *args, **kwargs) -> AgentOutput | list[AgentOutput]:
        """Run the component."""
        raise NotImplementedError()
