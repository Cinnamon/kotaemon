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

    def run(
        self,
        documents: list[Document],
        query: str,
        *args,
        **kwargs,
    ) -> list[Document]:
        raise NotImplementedError
