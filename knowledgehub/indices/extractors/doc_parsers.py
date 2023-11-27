from ..base import DocTransformer, LlamaIndexMixin


class BaseDocParser(DocTransformer):
    ...


class TitleExtractor(LlamaIndexMixin, BaseDocParser):
    def _get_li_class(self):
        from llama_index.extractors import TitleExtractor

        return TitleExtractor


class SummaryExtractor(LlamaIndexMixin, BaseDocParser):
    def _get_li_class(self):
        from llama_index.extractors import SummaryExtractor

        return SummaryExtractor
