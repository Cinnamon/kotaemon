from typing import List

from pydantic import Field

from kotaemon.documents.base import Document


class LLMInterface(Document):
    candidates: List[str] = Field(default_factory=list)
    completion_tokens: int = -1
    total_tokens: int = -1
    prompt_tokens: int = -1
    logits: List[List[float]] = Field(default_factory=list)
