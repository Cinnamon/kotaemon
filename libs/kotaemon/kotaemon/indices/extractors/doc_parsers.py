from typing import Any, Type

from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseDocParser(DocTransformer): ...


class TitleExtractor(LlamaIndexDocTransformerMixin, BaseDocParser):
    def __init__(
        self,
        llm: Any = None,
        nodes: int = 5,
        **params: Any,
    ) -> None:
        super().__init__(llm=llm, nodes=nodes, **params)

    def _get_li_class(self) -> Type[Any]:
        from llama_index.core.extractors import TitleExtractor

        return TitleExtractor


class SummaryExtractor(LlamaIndexDocTransformerMixin, BaseDocParser):
    def __init__(
        self,
        llm: Any = None,
        summaries: list[str] = ["self"],
        **params: Any,
    ) -> None:
        super().__init__(llm=llm, summaries=summaries, **params)

    def _get_li_class(self) -> Type[Any]:
        from llama_index.core.extractors import SummaryExtractor

        return SummaryExtractor
