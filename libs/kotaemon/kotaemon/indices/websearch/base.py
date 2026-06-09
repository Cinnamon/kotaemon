from __future__ import annotations

from dataclasses import dataclass

from kotaemon.base import RetrievedDocument


@dataclass(kw_only=True)
class BaseWebSearch:
    """Base class for internet search backends used as a chat retriever."""

    def run(self, text: str, *args, **kwargs) -> list[RetrievedDocument]:
        raise NotImplementedError

    def generate_relevant_scores(
        self,
        text: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        return documents
