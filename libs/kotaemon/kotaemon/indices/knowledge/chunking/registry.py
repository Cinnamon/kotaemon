"""Extensible registry for source-aware chunk strategy factories."""

from collections.abc import Callable, Iterable

from kotaemon.indices.splitters import BaseSplitter

from .base import ChunkStrategy
from .code import PythonCodeChunkStrategy
from .faq import FAQChunkStrategy
from .markdown import MarkdownChunkStrategy
from .structured import StructuredChunkStrategy
from .token import TokenChunkStrategy

_STRATEGIES: dict[str, Callable[..., ChunkStrategy]] = {}


def register_chunk_strategy(
    source_types: Iterable[str], factory: Callable[..., ChunkStrategy]
) -> None:
    for source_type in source_types:
        _STRATEGIES[source_type] = factory


def get_chunk_strategy(source_type: str, token_splitter: BaseSplitter) -> ChunkStrategy:
    factory = _STRATEGIES.get(source_type, TokenChunkStrategy)
    return factory(token_splitter=token_splitter)


register_chunk_strategy(["wiki", "markdown"], MarkdownChunkStrategy)
register_chunk_strategy(["faq"], FAQChunkStrategy)
register_chunk_strategy(["code"], PythonCodeChunkStrategy)
register_chunk_strategy(["pdf", "ppt", "excel"], StructuredChunkStrategy)
