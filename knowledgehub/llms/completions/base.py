from typing import List, Type

from langchain.schema.language_model import BaseLanguageModel
from theflow.base import Param

from ...base import BaseComponent
from ..base import LLMInterface


class LLM(BaseComponent):
    pass


class LangchainLLM(LLM):
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

    @Param.decorate(no_cache=True)
    def agent(self):
        return self._lc_class(**self._kwargs)

    def run_raw(self, text: str) -> LLMInterface:
        pred = self.agent.generate([text])
        return LLMInterface(
            text=[each.text for each in pred.generations[0]],
            completion_tokens=pred.llm_output["token_usage"]["completion_tokens"],
            total_tokens=pred.llm_output["token_usage"]["total_tokens"],
            prompt_tokens=pred.llm_output["token_usage"]["prompt_tokens"],
            logits=[],
        )

    def run_batch_raw(self, text: List[str]) -> List[LLMInterface]:
        outputs = []
        for each_text in text:
            outputs.append(self.run_raw(each_text))
        return outputs

    def run_document(self, text: str) -> LLMInterface:
        return self.run_raw(text)

    def run_batch_document(self, text: List[str]) -> List[LLMInterface]:
        return self.run_batch_raw(text)

    def is_document(self, text) -> bool:
        return False

    def is_batch(self, text) -> bool:
        return False if isinstance(text, str) else True

    def __setattr__(self, name, value):
        if name in self._lc_class.__fields__:
            setattr(self.agent, name, value)
        else:
            super().__setattr__(name, value)


class LLMChat(BaseComponent):
    pass
