from .base import ChatLLM as BaseChatLLM
from .openai import AzureChatOpenAI
from .env import AzureLLMSettings


class LLMFactory:
    @staticmethod
    def azure(env: AzureLLMSettings) -> BaseChatLLM:
        return AzureChatOpenAI(
            azure_endpoint=env.AZURE_OPENAI_ENDPOINT,
            api_key=env.AZURE_OPENAI_API_KEY,
            api_version=env.AZURE_OPENAI_API_VERSION,
            azure_deployment=env.AZURE_OPENAI_CHAT_DEPLOYMENT,
        )

    @staticmethod
    def supported_vendors() -> list[type[BaseChatLLM]]:
        return [
            AzureChatOpenAI,
        ]
