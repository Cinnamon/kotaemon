from typing import Any, List, Sequence, Type

from llama_index.node_parser import (
    SentenceWindowNodeParser as LISentenceWindowNodeParser,
)
from llama_index.node_parser import SimpleNodeParser as LISimpleNodeParser
from llama_index.node_parser.interface import NodeParser
from llama_index.text_splitter import TokenTextSplitter

from ..base import BaseComponent, Document

__all__ = ["TokenTextSplitter"]


class LINodeParser(BaseComponent):
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

    def get_nodes_from_documents(
        self,
        documents: Sequence[Document],
        show_progress: bool = False,
    ) -> List[Document]:
        documents = self._parser.get_nodes_from_documents(
            documents=documents, show_progress=show_progress
        )
        # convert Document to new base class from kotaemon
        converted_documents = [Document.from_dict(doc.to_dict()) for doc in documents]
        return converted_documents

    def run(
        self,
        documents: Sequence[Document],
        show_progress: bool = False,
    ) -> List[Document]:
        return self.get_nodes_from_documents(
            documents=documents, show_progress=show_progress
        )


class SimpleNodeParser(LINodeParser):
    _parser_class = LISimpleNodeParser

    def __init__(self, *args, **kwargs):
        chunk_size = kwargs.pop("chunk_size", 512)
        chunk_overlap = kwargs.pop("chunk_overlap", 0)
        kwargs["text_splitter"] = TokenTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        super().__init__(*args, **kwargs)


class SentenceWindowNodeParser(LINodeParser):
    _parser_class = LISentenceWindowNodeParser
