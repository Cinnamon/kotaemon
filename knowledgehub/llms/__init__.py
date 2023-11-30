from typing import Union

from kotaemon.base.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .branching import GatedBranchingPipeline, SimpleBranchingPipeline
from .chats import AzureChatOpenAI, ChatLLM
from .completions import LLM, AzureOpenAI, OpenAI
from .linear import GatedLinearPipeline, SimpleLinearPipeline
from .prompts import BasePromptComponent, PromptTemplate

BaseLLM = Union[ChatLLM, LLM]


__all__ = [
    "BaseLLM",
    # chat-specific components
    "ChatLLM",
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "AzureChatOpenAI",
    # completion-specific components
    "LLM",
    "OpenAI",
    "AzureOpenAI",
    # prompt-specific components
    "BasePromptComponent",
    "PromptTemplate",
    # strategies
    "SimpleLinearPipeline",
    "GatedLinearPipeline",
    "SimpleBranchingPipeline",
    "GatedBranchingPipeline",
]
