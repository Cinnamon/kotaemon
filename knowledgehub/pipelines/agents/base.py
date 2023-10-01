from enum import Enum
from typing import Dict, List, Union

from pydantic import BaseModel

from kotaemon.llms.chats.base import ChatLLM
from kotaemon.llms.completions.base import LLM
from kotaemon.pipelines.tools import BaseTool
from kotaemon.prompt.template import PromptTemplate

BaseLLM = Union[ChatLLM, LLM]


class AgentType(Enum):
    """
    Enumerated type for agent types.
    """

    openai = "openai"
    react = "react"
    rewoo = "rewoo"
    vanilla = "vanilla"
    openai_memory = "openai_memory"

    @staticmethod
    def get_agent_class(_type: "AgentType"):
        """
        Get agent class from agent type.
        :param _type: agent type
        :return: agent class
        """
        if _type == AgentType.rewoo:
            from .rewoo.agent import RewooAgent

            return RewooAgent
        else:
            raise ValueError(f"Unknown agent type: {_type}")


class AgentOutput(BaseModel):
    """
    Pydantic model for agent output.
    """

    output: str
    cost: float
    token_usage: int


class BaseAgent(BaseTool):
    name: str
    """Name of the agent."""
    type: AgentType
    """Agent type, must be one of AgentType"""
    description: str
    """Description used to tell the model how/when/why to use the agent.
    You can provide few-shot examples as a part of the description. This will be
    input to the prompt of LLM."""
    llm: Union[BaseLLM, Dict[str, BaseLLM]]
    """Specify LLM to be used in the model, cam be a dict to supply different
    LLMs to multiple purposes in the agent"""
    prompt_template: Union[PromptTemplate, Dict[str, PromptTemplate]]
    """A prompt template or a dict to supply different prompt to the agent
    """
    plugins: List[BaseTool]
    """List of plugins / tools to be used in the agent
    """
