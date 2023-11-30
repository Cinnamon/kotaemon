from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseDocParser(DocTransformer):
    ...


class TitleExtractor(LlamaIndexDocTransformerMixin, BaseDocParser):
    def _get_li_class(self):
        from llama_index.extractors import TitleExtractor

        return TitleExtractor


class SummaryExtractor(LlamaIndexDocTransformerMixin, BaseDocParser):
    def _get_li_class(self):
        from llama_index.extractors import SummaryExtractor

        return SummaryExtractor
