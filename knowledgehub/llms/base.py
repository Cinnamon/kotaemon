from dataclasses import dataclass, field

from ..components import BaseComponent


@dataclass
class LLMInterface:
    text: list[str]
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens: int = -1
    logits: list[list[float]] = field(default_factory=list)


class PromptTemplate(BaseComponent):
    pass


class Extract(BaseComponent):
    pass


class PromptNode(BaseComponent):
    pass
