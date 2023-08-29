import langchain.llms as langchain_llms

from .base import LangchainLLM


class OpenAI(LangchainLLM):
    """Wrapper around Langchain's OpenAI class"""
    _lc_class = langchain_llms.OpenAI


class AzureOpenAI(LangchainLLM):
    """Wrapper around Langchain's AzureOpenAI class"""
    _lc_class = langchain_llms.AzureOpenAI
