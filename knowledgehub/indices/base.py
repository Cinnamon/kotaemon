from __future__ import annotations

from abc import abstractmethod
from typing import Any, Type

from llama_index.node_parser.interface import NodeParser

from ..base import BaseComponent, Document


class DocTransformer(BaseComponent):
    """This is a base class for document transformers

    A document transformer transforms a list of documents into another list
    of documents. Transforming can mean splitting a document into multiple documents,
    reducing a large list of documents into a smaller list of documents, or adding
    metadata to each document in a list of documents, etc.
    """

    @abstractmethod
    def run(
        self,
        documents: list[Document],
        **kwargs,
    ) -> list[Document]:
        ...


class LlamaIndexMixin:
    """Allow automatically wrapping a Llama-index component into kotaemon component

    Example:
        class TokenSplitter(LlamaIndexMixin, BaseSplitter):
            def _get_li_class(self):
                from llama_index.text_splitter import TokenTextSplitter
                return TokenTextSplitter

    To use this mixin, please:
        1. Use this class as the 1st parent class, so that Python will prefer to use
        the attributes and methods of this class whenever possible.
        2. Overwrite `_get_li_class` to return the relevant LlamaIndex component.
    """

    def _get_li_class(self) -> Type[NodeParser]:
        raise NotImplementedError(
            "Please return the relevant LlamaIndex class in _get_li_class"
        )

    def __init__(self, *args, **kwargs):
        _li_cls = self._get_li_class()
        self._obj = _li_cls(*args, **kwargs)
        super().__init__()

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in self._protected_keywords():
            return super().__setattr__(name, value)

        return setattr(self._obj, name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._obj, name)

    def run(
        self,
        documents: list[Document],
        **kwargs,
    ) -> list[Document]:
        """Run Llama-index node parser and convert the output to Document from
        kotaemon
        """
        docs = self._obj(documents, **kwargs)  # type: ignore
        return [Document.from_dict(doc.to_dict()) for doc in docs]
