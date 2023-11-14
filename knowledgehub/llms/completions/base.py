import logging
from typing import Type

from langchain.llms.base import BaseLLM
from theflow.base import Param

from ...base import BaseComponent
from ...base.schema import LLMInterface

logger = logging.getLogger(__name__)


class LLM(BaseComponent):
    pass


class LangchainLLM(LLM):
    _lc_class: Type[BaseLLM]

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
    def agent(self):
        return self._lc_class(**self._kwargs)

    def run(self, text: str) -> LLMInterface:
        pred = self.agent.generate([text])
        all_text = [each.text for each in pred.generations[0]]

        completion_tokens, total_tokens, prompt_tokens = 0, 0, 0
        try:
            if pred.llm_output is not None:
                completion_tokens = pred.llm_output["token_usage"]["completion_tokens"]
                total_tokens = pred.llm_output["token_usage"]["total_tokens"]
                prompt_tokens = pred.llm_output["token_usage"]["prompt_tokens"]
        except Exception:
            logger.warning(
                f"Cannot get token usage from LLM output for {self._lc_class.__name__}"
            )

        return LLMInterface(
            text=all_text[0] if len(all_text) > 0 else "",
            candidates=all_text,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            logits=[],
        )

    def __setattr__(self, name, value):
        if name in self._lc_class.__fields__:
            self._kwargs[name] = value
            setattr(self.agent, name, value)
        else:
            super().__setattr__(name, value)


class LLMChat(BaseComponent):
    pass
