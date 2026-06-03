from __future__ import annotations

from enum import Enum

from .base import ChatLLM as BaseChatLLM
from .openai import AzureChatOpenAI


class LLMVendor(str, Enum):
    AZURE_CHAT_OPENAI = "AzureChatOpenAI"


MP_VENDOR_CLS: dict[LLMVendor, type[BaseChatLLM]] = {
    LLMVendor.AZURE_CHAT_OPENAI: AzureChatOpenAI,
}


class LLMFactory:
    @staticmethod
    def get_cls(vendor: LLMVendor) -> type[BaseChatLLM]:
        """Return the class for *vendor*, coercing bare strings."""
        key = LLMVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid LLM vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[LLMVendor]:
        return list(MP_VENDOR_CLS.keys())
