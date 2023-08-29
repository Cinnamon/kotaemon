from langchain.chat_models import AzureChatOpenAI as AzureChatOpenAILC

from .base import LangchainChatLLM


class AzureChatOpenAI(LangchainChatLLM):
    _lc_class = AzureChatOpenAILC
