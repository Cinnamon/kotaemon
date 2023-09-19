from dataclasses import dataclass, field
from typing import List

from ..base import BaseComponent


@dataclass
class LLMInterface:
    text: List[str]
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens: int = -1
    logits: List[List[float]] = field(default_factory=list)


class PromptTemplate(BaseComponent):
    pass


class Extract(BaseComponent):
    pass


class PromptNode(BaseComponent):
    pass
