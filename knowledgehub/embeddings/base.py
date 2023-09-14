from abc import abstractmethod
from typing import List, Type

from langchain.embeddings.base import Embeddings as LCEmbeddings
from theflow import Param

from ..components import BaseComponent
from ..documents.base import Document


class BaseEmbeddings(BaseComponent):
    @abstractmethod
    def run_raw(self, text: str) -> List[float]:
        ...

    @abstractmethod
    def run_batch_raw(self, text: List[str]) -> List[List[float]]:
        ...

    @abstractmethod
    def run_document(self, text: Document) -> List[float]:
        ...

    @abstractmethod
    def run_batch_document(self, text: List[Document]) -> List[List[float]]:
        ...

    def is_document(self, text) -> bool:
        if isinstance(text, Document):
            return True
        elif isinstance(text, List) and isinstance(text[0], Document):
            return True
        return False

    def is_batch(self, text) -> bool:
        if isinstance(text, list):
            return True
        return False


class LangchainEmbeddings(BaseEmbeddings):
    _lc_class: Type[LCEmbeddings]

    def __init__(self, **params):
        if self._lc_class is None:
            raise AttributeError(
                "Should set _lc_class attribute to the LLM class from Langchain "
                "if using LLM from Langchain"
            )

        self._kwargs: dict = {}
        for param in list(params.keys()):
            if param in self._lc_class.__fields__:  # type: ignore
                self._kwargs[param] = params.pop(param)
        super().__init__(**params)

    def __setattr__(self, name, value):
        if name in self._lc_class.__fields__:
            setattr(self.agent, name, value)
        else:
            super().__setattr__(name, value)

    @Param.decorate(no_cache=True)
    def agent(self):
        return self._lc_class(**self._kwargs)

    def run_raw(self, text: str) -> List[float]:
        return self.agent.embed_query(text)  # type: ignore

    def run_batch_raw(self, text: List[str]) -> List[List[float]]:
        return self.agent.embed_documents(text)  # type: ignore

    def run_document(self, text: Document) -> List[float]:
        return self.agent.embed_query(text.text)  # type: ignore

    def run_batch_document(self, text: List[Document]) -> List[List[float]]:
        return self.agent.embed_documents([each.text for each in text])  # type: ignore
