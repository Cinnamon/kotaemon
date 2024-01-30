from typing import List, Optional

from langchain.agents import AgentType as LCAgentType
from langchain.agents import initialize_agent
from langchain.agents.agent import AgentExecutor as LCAgentExecutor

from kotaemon.llms import LLM, ChatLLM

from .base import BaseAgent
from .io import AgentOutput, AgentType
from .tools import BaseTool


class LangchainAgent(BaseAgent):
    """Wrapper for Langchain Agent"""

    name: str = "LangchainAgent"
    agent_type: AgentType
    description: str = "LangchainAgent for answering multi-step reasoning questions"
    AGENT_TYPE_MAP = {
        AgentType.openai: LCAgentType.OPENAI_FUNCTIONS,
        AgentType.openai_multi: LCAgentType.OPENAI_MULTI_FUNCTIONS,
        AgentType.react: LCAgentType.ZERO_SHOT_REACT_DESCRIPTION,
        AgentType.self_ask: LCAgentType.SELF_ASK_WITH_SEARCH,
    }
    agent: Optional[LCAgentExecutor] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.agent_type not in self.AGENT_TYPE_MAP:
            raise NotImplementedError(
                f"AgentType {self.agent_type } not supported by Langchain wrapper"
            )
        self.update_agent_tools()

    def update_agent_tools(self):
        assert isinstance(self.llm, (ChatLLM, LLM))
        langchain_plugins = [tool.to_langchain_format() for tool in self.plugins]

        # a fix for search_doc tool name:
        # use "Intermediate Answer" for self-ask agent
        found_search_tool = False
        if self.agent_type == AgentType.self_ask:
            for plugin in langchain_plugins:
                if plugin.name == "search_doc":
                    plugin.name = "Intermediate Answer"
                    langchain_plugins = [plugin]
                    found_search_tool = True
                    break

        if self.agent_type != AgentType.self_ask or found_search_tool:
            # reinit Langchain AgentExecutor
            self.agent = initialize_agent(
                langchain_plugins,
                self.llm.to_langchain_format(),
                agent=self.AGENT_TYPE_MAP[self.agent_type],
                handle_parsing_errors=True,
                verbose=True,
            )

    def add_tools(self, tools: List[BaseTool]) -> None:
        super().add_tools(tools)
        self.update_agent_tools()
        return

    def run(self, instruction: str) -> AgentOutput:
        assert (
            self.agent is not None
        ), "Lanchain AgentExecutor is not correctly initialized"

        # Langchain AgentExecutor call
        output = self.agent(instruction)["output"]

        return AgentOutput(
            text=output,
            agent_type=self.agent_type,
            status="finished",
        )
