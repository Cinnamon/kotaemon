from __future__ import annotations

from abc import abstractmethod

from kotaemon.base import BaseComponent, Document


class BaseRerankings(BaseComponent):
    @abstractmethod
    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Main method to transform list of documents
        (re-ranking, filtering, etc)"""
        ...

    def prepare_input(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[Document]:
        if isinstance(text, (str, Document)):
            return [Document(content=text)]
        elif isinstance(text, list):
            return [Document(content=_) for _ in text]
        return text
