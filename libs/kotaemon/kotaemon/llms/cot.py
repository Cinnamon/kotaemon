from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, List

from kotaemon.base import Document

from .completions import LLM
from .prompts import BasePromptComponent


@dataclass(kw_only=True)
class Thought:
    prompt: str
    llm: LLM
    post_process: Callable[[str], dict]

    @cached_property
    def prompt_template(self) -> BasePromptComponent:
        return BasePromptComponent(template=self.prompt)

    def run(self, **kwargs) -> Document:
        prompt = self.prompt_template(**kwargs).text
        response = self.post_process(self.llm(prompt).text)
        return Document(response)

    def __call__(self, **kwargs) -> Document:
        return self.run(**kwargs)

    def __add__(self, next_thought: "Thought") -> "ManualSequentialChainOfThought":
        return ManualSequentialChainOfThought(
            thoughts=[self, next_thought], llm=self.llm
        )


@dataclass(kw_only=True)
class ManualSequentialChainOfThought:
    thoughts: List[Thought] = field(default_factory=list)
    llm: LLM
    terminate: Callable[[dict], bool] = field(default=lambda _: False)

    def run(self, **kwargs) -> Document:
        inputs = deepcopy(kwargs)
        for thought in self.thoughts:
            if self.llm:
                thought.llm = self.llm
            output = thought(**inputs)
            inputs.update(output.content)
            if self.terminate(inputs):
                break
        return Document(inputs)
