from typing import Any, Sequence, Type

from llama_index.extractors import SummaryExtractor as LISummaryExtractor
from llama_index.extractors import TitleExtractor as LITitleExtractor
from llama_index.node_parser import (
    SentenceWindowNodeParser as LISentenceWindowNodeParser,
)
from llama_index.node_parser.interface import NodeParser
from llama_index.text_splitter import TokenTextSplitter as LITokenTextSplitter

from ..base import BaseComponent, Document


class LIDocParser(BaseComponent):
    _parser_class: Type[NodeParser]

    def __init__(self, *args, **kwargs):
        if self._parser_class is None:
            raise AttributeError(
                "Require `_parser_class` to set a NodeParser class from LlamarIndex"
            )
        self._parser = self._parser_class(*args, **kwargs)
        super().__init__()

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in self._protected_keywords():
            return super().__setattr__(name, value)

        return setattr(self._parser, name, value)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._parser, name)

    def run(
        self,
        documents: Sequence[Document],
        **kwargs,
    ) -> Sequence[Document]:
        documents = self._parser(documents, **kwargs)
        # convert Document to new base class from kotaemon
        converted_documents = [Document.from_dict(doc.to_dict()) for doc in documents]
        return converted_documents


class TokenSplitter(LIDocParser):
    _parser_class = LITokenTextSplitter


class SentenceWindowNodeParser(LIDocParser):
    _parser_class = LISentenceWindowNodeParser


class TitleExtractor(LIDocParser):
    _parser_class = LITitleExtractor


class SummaryExtractor(LIDocParser):
    _parser_class = LISummaryExtractor
