from kotaemon.base import BaseComponent
from langchain_core.language_models.base import BaseLanguageModel


class BaseLLM(BaseComponent):
    def to_langchain_format(self) -> BaseLanguageModel:
        raise NotImplementedError
