from typing import AsyncGenerator, Iterator, Any

from langchain_core.language_models.base import BaseLanguageModel

from kotaemon.base import BaseComponent, LLMInterface


class BaseLLM(BaseComponent):
    def to_langchain_format(self) -> BaseLanguageModel:
        raise NotImplementedError

    def invoke(self, *args: Any, **kwargs: Any) -> LLMInterface:
        raise NotImplementedError

    async def ainvoke(self, *args: Any, **kwargs: Any) -> LLMInterface:
        raise NotImplementedError

    def stream(self, *args: Any, **kwargs: Any) -> Iterator[LLMInterface]:
        raise NotImplementedError

    def astream(self, *args: Any, **kwargs: Any) -> AsyncGenerator[LLMInterface, None]:
        raise NotImplementedError

    def run(self, *args: Any, **kwargs: Any) -> LLMInterface:
        return self.invoke(*args, **kwargs)
