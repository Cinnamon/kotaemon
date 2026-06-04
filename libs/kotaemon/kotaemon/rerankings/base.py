from __future__ import annotations

from dataclasses import dataclass

from kotaemon.base import Document
from kotaemon.base.describe import DataclassDescribe, describe_dataclass


@dataclass(kw_only=True)
class BaseReranking:
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)

    def __call__(
        self,
        documents: list[Document],
        query: str,
        *args,
        **kwargs,
    ) -> list[Document]:
        return self.run(documents, query, *args, **kwargs)

    def prepare_input(self, documents: list[str] | list[Document]) -> list[Document]:
        """Coerce a list of strings to a list of Documents."""
        return [
            d if isinstance(d, Document) else Document(content=d) for d in documents
        ]

    def run(
        self,
        documents: list[Document],
        query: str,
        *args,
        **kwargs,
    ) -> list[Document]:
        raise NotImplementedError
