from __future__ import annotations

from abc import abstractmethod

from kotaemon.base import BaseComponent, Document, DocumentWithEmbedding


class BaseEmbeddings(BaseComponent):
    @abstractmethod
    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[DocumentWithEmbedding]:
        ...
