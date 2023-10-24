from typing import List, Type, TypeVar

from langchain.schema.language_model import BaseLanguageModel
from langchain.schema.messages import BaseMessage, HumanMessage
from theflow.base import Param

from ...base import BaseComponent
from ..base import LLMInterface

Message = TypeVar("Message", bound=BaseMessage)


class ChatLLM(BaseComponent):
    def flow(self):
        if self.inflow is None:
            raise ValueError("No inflow provided.")

        if not isinstance(self.inflow, BaseComponent):
            raise ValueError(
                f"inflow must be a BaseComponent, found {type(self.inflow)}"
            )

        text = self.inflow.flow().text
        return self.__call__(text)


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

    @Param.auto(cache=False)
    def agent(self) -> BaseLanguageModel:
        return self._lc_class(**self._kwargs)

    def run_raw(self, text: str, **kwargs) -> LLMInterface:
        message = HumanMessage(content=text)
        return self.run_document([message], **kwargs)

    def run_batch_raw(self, text: List[str], **kwargs) -> List[LLMInterface]:
        inputs = [[HumanMessage(content=each)] for each in text]
        return self.run_batch_document(inputs, **kwargs)

    def run_document(self, text: List[Message], **kwargs) -> LLMInterface:
        pred = self.agent.generate([text], **kwargs)  # type: ignore
        all_text = [each.text for each in pred.generations[0]]
        return LLMInterface(
            text=all_text[0] if len(all_text) > 0 else "",
            candidates=all_text,
            completion_tokens=pred.llm_output["token_usage"]["completion_tokens"],
            total_tokens=pred.llm_output["token_usage"]["total_tokens"],
            prompt_tokens=pred.llm_output["token_usage"]["prompt_tokens"],
            logits=[],
        )

    def run_batch_document(
        self, text: List[List[Message]], **kwargs
    ) -> List[LLMInterface]:
        outputs = []
        for each_text in text:
            outputs.append(self.run_document(each_text, **kwargs))
        return outputs

    def is_document(self, text, **kwargs) -> bool:
        if isinstance(text, str):
            return False
        elif isinstance(text, List) and isinstance(text[0], str):
            return False
        return True

    def is_batch(self, text, **kwargs) -> bool:
        if isinstance(text, str):
            return False
        elif isinstance(text, List):
            if isinstance(text[0], BaseMessage):
                return False
        return True

    def __setattr__(self, name, value):
        if name in self._lc_class.__fields__:
            setattr(self.agent, name, value)
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        if name in self._lc_class.__fields__:
            getattr(self.agent, name)
        else:
            super().__getattr__(name)
