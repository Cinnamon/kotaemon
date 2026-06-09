from __future__ import annotations

from typing import Callable, Optional, Union

from kotaemon.base import Runnable
from kotaemon.base.schema import Document, IO_Type

from .chats import ChatLLM
from .completions import LLM
from .prompts import BasePromptComponent


class SimpleLinearPipeline:
    def __init__(
        self,
        prompt: BasePromptComponent,
        llm: Union[ChatLLM, LLM],
        post_processor: Union[Runnable, Callable[[IO_Type], IO_Type]] | None = None,
    ) -> None:
        self.prompt = prompt
        self.llm = llm
        self.post_processor = post_processor

    def run(
        self,
        *,
        llm_kwargs: Optional[dict] = None,
        post_processor_kwargs: Optional[dict] = None,
        **prompt_kwargs,
    ):
        llm_kwargs = llm_kwargs or {}
        post_processor_kwargs = post_processor_kwargs or {}
        prompt = self.prompt(**prompt_kwargs)
        llm_output = self.llm(prompt.text, **llm_kwargs)
        if self.post_processor is not None:
            final_output = self.post_processor(llm_output, **post_processor_kwargs)[0]
        else:
            final_output = llm_output
        return Document(final_output)


class GatedLinearPipeline(SimpleLinearPipeline):
    def __init__(self, prompt, llm, condition, post_processor=None):
        super().__init__(prompt=prompt, llm=llm, post_processor=post_processor)
        self.condition = condition

    def run(self, *, condition_text: Optional[str] = None, **kwargs) -> Document:
        if condition_text is None:
            raise ValueError("`condition_text` must be provided")
        if self.condition(condition_text)[0]:
            return super().run(**kwargs)
        return Document(None)
