from ..base import DocTransformer, LlamaIndexMixin


class BaseSplitter(DocTransformer):
    """Represent base splitter class"""

    ...


class TokenSplitter(LlamaIndexMixin, BaseSplitter):
    def _get_li_class(self):
        from llama_index.text_splitter import TokenTextSplitter

        return TokenTextSplitter


class SentenceWindowSplitter(LlamaIndexMixin, BaseSplitter):
    def _get_li_class(self):
        from llama_index.node_parser import SentenceWindowNodeParser

        return SentenceWindowNodeParser
