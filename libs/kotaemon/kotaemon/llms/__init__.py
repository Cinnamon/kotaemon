from kotaemon.base.schema import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .base import BaseLLM
from .branching import GatedBranchingPipeline, SimpleBranchingPipeline
from .chats import (
    AzureChatOpenAI,
    ChatLLM,
    ChatOpenAI,
    EndpointChatLLM,
    LCAnthropicChat,
    LCAzureChatOpenAI,
    LCChatOpenAI,
    LCCohereChat,
    LCGeminiChat,
    LCOllamaChat,
    LlamaCppChat,
    StructuredOutputChatOpenAI,
)
from .completions import LLM, AzureOpenAI, LlamaCpp, OpenAI
from .cot import ManualSequentialChainOfThought, Thought
from .linear import GatedLinearPipeline, SimpleLinearPipeline
from .prompts import BasePromptComponent, PromptTemplate

__all__ = [
    "BaseLLM",
    # chat-specific components
    "ChatLLM",
    "EndpointChatLLM",
    "BaseMessage",
    "HumanMessage",
    "AIMessage",
    "SystemMessage",
    "AzureChatOpenAI",
    "ChatOpenAI",
    "StructuredOutputChatOpenAI",
    "LCAnthropicChat",
    "LCGeminiChat",
    "LCCohereChat",
    "LCOllamaChat",
    "LCAzureChatOpenAI",
    "LCChatOpenAI",
    "LlamaCppChat",
    # completion-specific components
    "LLM",
    "OpenAI",
    "AzureOpenAI",
    "LlamaCpp",
    # prompt-specific components
    "BasePromptComponent",
    "PromptTemplate",
    # strategies
    "SimpleLinearPipeline",
    "GatedLinearPipeline",
    "SimpleBranchingPipeline",
    "GatedBranchingPipeline",
    # chain-of-thoughts
    "ManualSequentialChainOfThought",
    "Thought",
]
