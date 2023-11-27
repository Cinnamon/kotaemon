from __future__ import annotations

from abc import abstractmethod
from typing import Type

from langchain.schema.embeddings import Embeddings as LCEmbeddings
from theflow import Param

from kotaemon.base import BaseComponent, Document, DocumentWithEmbedding


class BaseEmbeddings(BaseComponent):
    @abstractmethod
    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[DocumentWithEmbedding]:
        ...


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
            self._kwargs[name] = value
        else:
            super().__setattr__(name, value)

    @Param.auto(cache=False)
    def agent(self):
        return self._lc_class(**self._kwargs)

    def run(self, text):
        input_: list[str] = []
        if not isinstance(text, list):
            text = [text]

        for item in text:
            if isinstance(item, str):
                input_.append(item)
            elif isinstance(item, Document):
                input_.append(item.text)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )

        embeddings = self.agent.embed_documents(input_)

        return [
            DocumentWithEmbedding(text=each_text, embedding=each_embedding)
            for each_text, each_embedding in zip(input_, embeddings)
        ]
