from ..base import DocTransformer, LlamaIndexDocTransformerMixin


class BaseSplitter(DocTransformer):
    """Represent base splitter class"""

    ...


class TokenSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 20,
        separator: str = " ",
        **params,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=separator,
            **params,
        )

    def _get_li_class(self):
        from llama_index.text_splitter import TokenTextSplitter

        return TokenTextSplitter


class SentenceWindowSplitter(LlamaIndexDocTransformerMixin, BaseSplitter):
    def __init__(self, window_size: int = 3, **params):
        super().__init__(window_size=window_size, **params)

    def _get_li_class(self):
        from llama_index.node_parser import SentenceWindowNodeParser

        return SentenceWindowNodeParser
