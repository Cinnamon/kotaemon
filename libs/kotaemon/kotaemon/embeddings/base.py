from __future__ import annotations

from dataclasses import dataclass

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.base.describe import DataclassDescribe, describe_dataclass


@dataclass(kw_only=True)
class BaseEmbeddings:
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)

    def __call__(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        return self.invoke(text, *args, **kwargs)

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        raise NotImplementedError

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        raise NotImplementedError

    def prepare_input(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[Document]:
        if isinstance(text, (str, Document)):
            return [Document(content=text)]
        elif isinstance(text, list):
            return [Document(content=_) for _ in text]
        return text
