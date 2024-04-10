from typing import TYPE_CHECKING, Optional

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

if TYPE_CHECKING:
    from fastembed import TextEmbedding


class FastEmbedEmbeddings(BaseEmbeddings):
    """Utilize fastembed library for embeddings locally without GPU.

    Supported model: https://qdrant.github.io/fastembed/examples/Supported_Models/
    Code: https://github.com/qdrant/fastembed
    """

    model_name: str = Param(
        "BAAI/bge-small-en-v1.5",
        help=(
            "Model name for fastembed. Please refer "
            "[here](https://qdrant.github.io/fastembed/examples/Supported_Models/) "
            "for the list of supported models."
        ),
        required=True,
    )
    batch_size: int = Param(
        256,
        help="Batch size for embeddings. Higher values use more memory, but are faster",
    )
    parallel: Optional[int] = Param(
        None,
        help=(
            "Number of threads to use for embeddings. "
            "If > 1, data-parallel encoding will be used. "
            "If 0, use all available CPUs. "
            "If None, use default onnxruntime threading. "
            "Defaults to None."
        ),
    )

    @Param.auto()
    def client_(self) -> "TextEmbedding":
        from fastembed import TextEmbedding

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
            DocumentWithEmbedding(
                content=doc,
                embedding=list(embedding),
            )
            for doc, embedding in zip(input_, embeddings)
        ]

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        """Fastembed does not support async API."""
        return self.invoke(text, *args, **kwargs)
