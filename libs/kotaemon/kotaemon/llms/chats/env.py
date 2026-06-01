from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    AZURE_OPENAI_CHAT_DEPLOYMENT: str = Field(default="")
    AZURE_OPENAI_ENDPOINT: str = Field(default="")
    AZURE_OPENAI_API_KEY: str = Field(default="")
    AZURE_OPENAI_API_VERSION: str = Field(default="2024-02-15-preview")


class AnthropicLLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=False,
    )

    ANTHROPIC_API_KEY: str = Field(default="")
    ANTHROPIC_CHAT_MODEL: str = Field(default="claude-3-5-sonnet-20240620")


class LLMSettings(
    AzureLLMSettings,
    AnthropicLLMSettings,
    BaseSettings,
):
    ...