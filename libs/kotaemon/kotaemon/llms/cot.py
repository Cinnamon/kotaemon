from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, List

from kotaemon.base import BaseComponent, Document

from .completions import LLM
from .prompts import BasePromptComponent


@dataclass(kw_only=True)
class Thought(BaseComponent):
    """A single chain-of-thought step: prompt → LLM → post_process."""

    prompt: str = field(metadata={"description": "Prompt template with placeholders"})
    llm: LLM = field(metadata={"description": "LLM to execute the prompt"})
    post_process: Callable[[str], dict] = field(
        metadata={"description": "Post-process LLM output into a dict"}
    )

    @cached_property
    def prompt_template(self) -> BasePromptComponent:
        return BasePromptComponent(template=self.prompt)

    def run(self, **kwargs) -> Document:
        prompt = self.prompt_template(**kwargs).text
        response = self.llm(prompt).text
        response = self.post_process(response)
        return Document(response)

    def get_variables(self) -> List[str]:
        return []

    def __add__(self, next_thought: "Thought") -> "ManualSequentialChainOfThought":
        return ManualSequentialChainOfThought(
            thoughts=[self, next_thought], llm=self.llm
        )


@dataclass(kw_only=True)
class ManualSequentialChainOfThought(BaseComponent):
    """Sequential chain-of-thought over multiple Thought steps."""

    thoughts: List[Thought] = field(
        default_factory=list,
        metadata={"description": "Ordered thought steps"},
    )
    llm: LLM = field(metadata={"description": "Shared LLM for all thoughts"})
    terminate: Callable[[dict], bool] = field(
        default=lambda _: False,
        metadata={"description": "Stop early when this returns True"},
    )

    def run(self, **kwargs) -> Document:
        inputs = deepcopy(kwargs)
        for idx, thought in enumerate(self.thoughts):
            if self.llm:
                thought.llm = self.llm
            self._prepare_child(thought, f"thought{idx}")

            output = thought(**inputs)
            inputs.update(output.content)
            if self.terminate(inputs):
                break

        return Document(inputs)

    def __add__(self, next_thought: Thought) -> "ManualSequentialChainOfThought":
        return ManualSequentialChainOfThought(
            thoughts=self.thoughts + [next_thought], llm=self.llm
        )
