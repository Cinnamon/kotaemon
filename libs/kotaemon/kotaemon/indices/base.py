from __future__ import annotations

from abc import abstractmethod
from typing import Any, Type

from llama_index.core.node_parser.interface import NodeParser

from kotaemon.base import BaseComponent, Document, RetrievedDocument


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


class LlamaIndexDocTransformerMixin:
    """Allow automatically wrapping a Llama-index component into kotaemon component

    Example:
        class TokenSplitter(LlamaIndexMixin, BaseSplitter):
            def _get_li_class(self):
                from llama_index.core.text_splitter import TokenTextSplitter
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

    def __init__(self, **params):
        self._li_cls = self._get_li_class()
        self._obj = self._li_cls(**params)
        self._kwargs = params
        super().__init__()

    def __repr__(self):
        kwargs = []
        for key, value_obj in self._kwargs.items():
            value = repr(value_obj)
            kwargs.append(f"{key}={value}")
        kwargs_repr = ", ".join(kwargs)
        return f"{self.__class__.__name__}({kwargs_repr})"

    def __str__(self):
        kwargs = []
        for key, value_obj in self._kwargs.items():
            value = str(value_obj)
            if len(value) > 20:
                value = f"{value[:15]}..."
            kwargs.append(f"{key}={value}")
        kwargs_repr = ", ".join(kwargs)
        return f"{self.__class__.__name__}({kwargs_repr})"

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in self._protected_keywords():
            return super().__setattr__(name, value)

        self._kwargs[name] = value
        return setattr(self._obj, name, value)

    def __getattr__(self, name: str) -> Any:
        if name in self._kwargs:
            return self._kwargs[name]
        return getattr(self._obj, name)

    def dump(self, *args, **kwargs):
        from theflow.utils.modules import serialize

        params = {key: serialize(value) for key, value in self._kwargs.items()}
        return {
            "__type__": f"{self.__module__}.{self.__class__.__qualname__}",
            **params,
        }

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


class BaseIndexing(BaseComponent):
    """Define the base interface for indexing pipeline"""

    def to_retrieval_pipeline(self, **kwargs):
        """Convert the indexing pipeline to a retrieval pipeline"""
        raise NotImplementedError

    def to_qa_pipeline(self, **kwargs):
        """Convert the indexing pipeline to a QA pipeline"""
        raise NotImplementedError


class BaseRetrieval(BaseComponent):
    """Define the base interface for retrieval pipeline"""

    @abstractmethod
    def run(self, *args, **kwargs) -> list[RetrievedDocument]:
        ...
