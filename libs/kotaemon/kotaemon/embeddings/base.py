from __future__ import annotations

from kotaemon.base import BaseComponent, Document, DocumentWithEmbedding


class BaseEmbeddings(BaseComponent):
    def run(
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
