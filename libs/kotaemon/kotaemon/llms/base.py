from langchain_core.language_models.base import BaseLanguageModel

from kotaemon.base import BaseComponent


class BaseLLM(BaseComponent):
    def to_langchain_format(self) -> BaseLanguageModel:
        raise NotImplementedError
