from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type

from llama_index.core.node_parser.interface import NodeParser

from kotaemon.base import Document, RetrievedDocument


class DocTransformer(ABC):
    @abstractmethod
    def run(self, documents: list[Document], **kwargs) -> list[Document]:
        ...

    def __call__(self, documents: list[Document], **kwargs) -> list[Document]:
        return self.run(documents, **kwargs)


class LlamaIndexDocTransformerMixin:
    def _get_li_class(self) -> Type[NodeParser]:
        raise NotImplementedError(
            "Please return the relevant LlamaIndex class in _get_li_class"
        )

    def __init__(self, **params):
        self._li_cls = self._get_li_class()
        self._obj = self._li_cls(**params)
        self._kwargs = params

    def __repr__(self):
        kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in self._kwargs.items())
        return f"{self.__class__.__name__}({kwargs_repr})"

    def __str__(self):
        parts = []
        for key, value_obj in self._kwargs.items():
            value = str(value_obj)
            if len(value) > 20:
                value = f"{value[:15]}..."
            parts.append(f"{key}={value}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in self._protected_keywords():
            return super().__setattr__(name, value)
        self._kwargs[name] = value
        return setattr(self._obj, name, value)

    def __getattr__(self, name: str) -> Any:
        if name in self._kwargs:
            return self._kwargs[name]
        return getattr(self._obj, name)

    def run(self, documents: list[Document], **kwargs) -> list[Document]:
        docs = self._obj(documents, **kwargs)  # type: ignore
        return [Document.from_dict(doc.to_dict()) for doc in docs]


class BaseRetrieval(ABC):
    @abstractmethod
    def run(self, *args, **kwargs) -> list[RetrievedDocument]:
        ...

    def __call__(self, *args, **kwargs) -> list[RetrievedDocument]:
        return self.run(*args, **kwargs)
