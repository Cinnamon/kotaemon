from __future__ import annotations

from enum import Enum

from .base import ChatLLM as BaseChatLLM
from .endpoint_based import EndpointChatLLM
from .langchain_based import (
    LCAnthropicChat,
    LCAzureChatOpenAI,
    LCChatOpenAI,
    LCCohereChat,
    LCGeminiChat,
    LCOllamaChat,
)
from .llamacpp import LlamaCppChat
from .openai import AzureChatOpenAI, ChatOpenAI, StructuredOutputChatOpenAI


class LLMVendor(str, Enum):
    AZURE_CHAT_OPENAI = "AzureChatOpenAI"
    CHAT_OPENAI = "ChatOpenAI"
    STRUCTURED_OUTPUT_CHAT_OPENAI = "StructuredOutputChatOpenAI"
    ENDPOINT = "EndpointChatLLM"
    LC_CHAT_OPENAI = "LCChatOpenAI"
    LC_AZURE_CHAT_OPENAI = "LCAzureChatOpenAI"
    LC_ANTHROPIC = "LCAnthropicChat"
    LC_GEMINI = "LCGeminiChat"
    LC_COHERE = "LCCohereChat"
    LC_OLLAMA = "LCOllamaChat"
    LLAMA_CPP = "LlamaCppChat"


MP_VENDOR_CLS: dict[LLMVendor, type[BaseChatLLM]] = {
    LLMVendor.AZURE_CHAT_OPENAI: AzureChatOpenAI,
    LLMVendor.CHAT_OPENAI: ChatOpenAI,
    LLMVendor.STRUCTURED_OUTPUT_CHAT_OPENAI: StructuredOutputChatOpenAI,
    LLMVendor.ENDPOINT: EndpointChatLLM,
    LLMVendor.LC_CHAT_OPENAI: LCChatOpenAI,
    LLMVendor.LC_AZURE_CHAT_OPENAI: LCAzureChatOpenAI,
    LLMVendor.LC_ANTHROPIC: LCAnthropicChat,
    LLMVendor.LC_GEMINI: LCGeminiChat,
    LLMVendor.LC_COHERE: LCCohereChat,
    LLMVendor.LC_OLLAMA: LCOllamaChat,
    LLMVendor.LLAMA_CPP: LlamaCppChat,
}


class LLMFactory:
    @staticmethod
    def get_cls(vendor: LLMVendor | str) -> type[BaseChatLLM]:
        """Return the class for *vendor*, coercing bare strings."""
        key = LLMVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid LLM vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[LLMVendor]:
        return list(MP_VENDOR_CLS.keys())
