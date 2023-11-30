from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseSplitter(DocTransformer):
    """Represent base splitter class"""

    ...


class TokenSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def _get_li_class(self):
        from llama_index.text_splitter import TokenTextSplitter

        return TokenTextSplitter


class SentenceWindowSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def _get_li_class(self):
        from llama_index.node_parser import SentenceWindowNodeParser

        return SentenceWindowNodeParser
