from typing import Type, TypeVar

from theflow.base import Param
from langchain.schema.language_model import BaseLanguageModel

from langchain.schema.messages import (
    BaseMessage,
    HumanMessage,
)

from ...components import BaseComponent
from ..base import LLMInterface


Message = TypeVar("Message", bound=BaseMessage)


class ChatLLM(BaseComponent):
    ...


class LangchainChatLLM(ChatLLM):
    _lc_class: Type[BaseLanguageModel]

    def __init__(self, **params):
        if self._lc_class is None:
            raise AttributeError(
                "Should set _lc_class attribute to the LLM class from Langchain "
                "if using LLM from Langchain"
            )

        self._kwargs: dict = {}
        for param in list(params.keys()):
            if param in self._lc_class.__fields__:
                self._kwargs[param] = params.pop(param)
        super().__init__(**params)

    @Param.decorate()
    def agent(self):
        return self._lc_class(**self._kwargs)

    def run_raw(self, text: str) -> LLMInterface:
        message = HumanMessage(content=text)
        return self.run_document([message])

    def run_batch_raw(self, text: list[str]) -> list[LLMInterface]:
        inputs = [[HumanMessage(content=each)] for each in text]
        return self.run_batch_document(inputs)

    def run_document(self, text: list[Message]) -> LLMInterface:
        pred = self.agent.generate([text])
        return LLMInterface(
            text=[each.text for each in pred.generations[0]],
            completion_tokens=pred.llm_output["token_usage"]["completion_tokens"],
            total_tokens=pred.llm_output["token_usage"]["total_tokens"],
            prompt_tokens=pred.llm_output["token_usage"]["prompt_tokens"],
            logits=[],
        )

    def run_batch_document(self, text: list[list[Message]]) -> list[LLMInterface]:
        outputs = []
        for each_text in text:
            outputs.append(self.run_document(each_text))
        return outputs

    def is_document(self, text) -> bool:
        if isinstance(text, str):
            return False
        elif isinstance(text, list) and isinstance(text[0], str):
            return False
        return True

    def is_batch(self, text) -> bool:
        if isinstance(text, str):
            return False
        elif isinstance(text, list):
            if isinstance(text[0], BaseMessage):
                return False
        return True

    def __setattr__(self, name, value):
        if name in self._lc_class.__fields__:
            setattr(self.agent, name, value)
        else:
            super().__setattr__(name, value)
