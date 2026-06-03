from functools import cached_property
from typing import Callable

from kotaemon.base import Document

from .template import PromptTemplate


class BasePromptComponent:
    def __init__(self, template: str | PromptTemplate, **kwargs) -> None:
        self.template = template
        self.__dict__.update(kwargs)

    @cached_property
    def template__(self) -> PromptTemplate:
        if isinstance(self.template, PromptTemplate):
            return self.template
        return PromptTemplate(self.template)

    def run(self, **kwargs):
        self.__dict__.update(kwargs)
        prepared = {
            k: str(getattr(self, k)() if callable(getattr(self, k)) else getattr(self, k))
            for k in self.template__.placeholders
        }
        return Document(
            text=self.template__.populate(**prepared),
            metadata={"origin": "PromptComponent"},
        )

    def __call__(self, **kwargs):
        return self.run(**kwargs)
