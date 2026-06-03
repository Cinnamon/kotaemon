from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Optional

from kotaemon.base import Document, DocumentWithEmbedding

from .base import BaseEmbeddings

if TYPE_CHECKING:
    from fastembed import TextEmbedding


@dataclass(kw_only=True)
class FastEmbedEmbeddings(BaseEmbeddings):
    """Utilize fastembed library for embeddings locally without GPU."""

    model_name: str = field(
        default="BAAI/bge-small-en-v1.5",
        metadata={"description": "fastembed model name"},
    )
    batch_size: int = field(
        default=256,
        metadata={"description": "Batch size for embeddings"},
    )
    parallel: Optional[int] = field(
        default=None,
        metadata={"description": "Thread count for encoding"},
    )

    @cached_property
    def client_(self) -> "TextEmbedding":
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError("Please install FastEmbed: `pip install fastembed`")
        return TextEmbedding(model_name=self.model_name)

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        input_ = self.prepare_input(text)
        embeddings = self.client_.embed(
            [_.content for _ in input_],
            batch_size=self.batch_size,
            parallel=self.parallel,
        )
        return [
            DocumentWithEmbedding(content=doc, embedding=list(embedding))
            for doc, embedding in zip(input_, embeddings)
        ]

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        return self.invoke(text, *args, **kwargs)
