"""Implements embeddings from [Voyage AI](https://voyageai.com).
"""

import importlib
from typing import Generator, Literal, Optional

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

vo = None

# Token limits per batch for each VoyageAI model
# See: https://docs.voyageai.com/docs/embeddings
VOYAGE_TOKEN_LIMITS = {
    # voyage-4 family
    "voyage-4": 320_000,
    "voyage-4-lite": 1_000_000,
    "voyage-4-large": 120_000,
    # voyage-3 family
    "voyage-3": 120_000,
    "voyage-3-lite": 120_000,
    "voyage-3-large": 120_000,
    "voyage-3.5": 320_000,
    "voyage-3.5-lite": 1_000_000,
    # Specialized models
    "voyage-code-3": 120_000,
    "voyage-finance-2": 120_000,
    "voyage-law-2": 120_000,
    "voyage-multilingual-2": 120_000,
    "voyage-large-2": 120_000,
    "voyage-large-2-instruct": 120_000,
    "voyage-code-2": 120_000,
    # Context models (use contextualized_embed API)
    "voyage-context-3": 32_000,
}

# Default token limit for unknown models
DEFAULT_TOKEN_LIMIT = 120_000


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


def _format_output(texts: list[str], embeddings: list[list]):
    """Formats the output of all `.embed` calls.
    Args:
        texts: List of original documents
        embeddings: Embeddings corresponding to each document
    """
    return [
        DocumentWithEmbedding(content=text, embedding=embedding)
        for text, embedding in zip(texts, embeddings)
    ]


class VoyageAIEmbeddings(BaseEmbeddings):
    """Voyage AI provides best-in-class embedding models and rerankers.

    Supports token-aware batching to optimize API calls within model limits.
    """

    api_key: str = Param(None, help="Voyage API key", required=False)
    model: str = Param(
        "voyage-3",
        help=(
            "Model name to use. The Voyage "
            "[documentation](https://docs.voyageai.com/docs/embeddings) "
            "provides a list of all available embedding models."
        ),
        required=True,
    )
    batch_size: int = Param(
        128,
        help=(
            "Maximum number of texts per batch. "
            "Will be further limited by token count."
        ),
    )
    truncation: bool = Param(
        True,
        help="Whether to truncate texts that exceed the model's max token limit.",
    )
    output_dimension: Optional[Literal[256, 512, 1024, 2048]] = Param(
        None,
        help=(
            "Output embedding dimension. Only supported by voyage-4 family models. "
            "If None, uses the model's default (1024 for voyage-4 models)."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIEmbeddings.")

        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    def _get_token_limit(self) -> int:
        """Get the token limit for the current model."""
        return VOYAGE_TOKEN_LIMITS.get(self.model, DEFAULT_TOKEN_LIMIT)

    def _is_context_model(self) -> bool:
        """Check if the model is a contextualized embedding model."""
        return "context" in self.model

    def _build_batches(
        self, texts: list[str]
    ) -> Generator[tuple[list[str], list[int]], None, None]:
        """Generate batches of texts respecting token limits.

        Yields:
            Tuple of (batch_texts, original_indices) for each batch
        """
        max_tokens = self._get_token_limit()
        index = 0

        while index < len(texts):
            batch: list[str] = []
            batch_indices: list[int] = []
            batch_tokens = 0

            while index < len(texts) and len(batch) < self.batch_size:
                # Tokenize the current text to get its token count
                token_count = len(
                    self._client.tokenize([texts[index]], model=self.model)[0]
                )

                # Check if adding this text would exceed the token limit
                if batch_tokens + token_count > max_tokens and len(batch) > 0:
                    # Yield current batch and start a new one
                    break

                batch_tokens += token_count
                batch.append(texts[index])
                batch_indices.append(index)
                index += 1

            if batch:
                yield batch, batch_indices

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a single batch of texts."""
        if self._is_context_model():
            return self._embed_context_batch(texts)
        return self._embed_regular_batch(texts)

    def _embed_regular_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed using regular embedding API."""
        kwargs = {
            "model": self.model,
            "truncation": self.truncation,
        }
        if self.output_dimension is not None:
            kwargs["output_dimension"] = self.output_dimension

        return self._client.embed(texts, **kwargs).embeddings

    def _embed_context_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed using contextualized embedding API (for voyage-context-3)."""
        if self.output_dimension is not None:
            result = self._client.contextualized_embed(
                inputs=[texts],
                model=self.model,
                output_dimension=self.output_dimension,
            )
        else:
            result = self._client.contextualized_embed(
                inputs=[texts],
                model=self.model,
            )
        return result.results[0].embeddings

    async def _aembed_batch(self, texts: list[str]) -> list[list[float]]:
        """Async embed a single batch of texts."""
        if self._is_context_model():
            return await self._aembed_context_batch(texts)
        return await self._aembed_regular_batch(texts)

    async def _aembed_regular_batch(self, texts: list[str]) -> list[list[float]]:
        """Async embed using regular embedding API."""
        kwargs = {
            "model": self.model,
            "truncation": self.truncation,
        }
        if self.output_dimension is not None:
            kwargs["output_dimension"] = self.output_dimension

        result = await self._aclient.embed(texts, **kwargs)
        return result.embeddings

    async def _aembed_context_batch(self, texts: list[str]) -> list[list[float]]:
        """Async embed using contextualized embedding API."""
        if self.output_dimension is not None:
            result = await self._aclient.contextualized_embed(
                inputs=[texts],
                model=self.model,
                output_dimension=self.output_dimension,
            )
        else:
            result = await self._aclient.contextualized_embed(
                inputs=[texts],
                model=self.model,
            )
        return result.results[0].embeddings

    def invoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]

        # For small inputs, skip batching overhead
        if len(texts) <= self.batch_size:
            token_count = sum(
                len(tokens) for tokens in self._client.tokenize(texts, model=self.model)
            )
            if token_count <= self._get_token_limit():
                embeddings = self._embed_batch(texts)
                return _format_output(texts, embeddings)

        # Use token-aware batching for larger inputs
        all_embeddings: list[list[float]] = [[] for _ in range(len(texts))]

        for batch_texts, batch_indices in self._build_batches(texts):
            batch_embeddings = self._embed_batch(batch_texts)
            for idx, embedding in zip(batch_indices, batch_embeddings):
                all_embeddings[idx] = embedding

        return _format_output(texts, all_embeddings)

    async def ainvoke(
        self, text: str | list[str] | Document | list[Document], *args, **kwargs
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]

        # For small inputs, skip batching overhead
        if len(texts) <= self.batch_size:
            token_count = sum(
                len(tokens) for tokens in self._client.tokenize(texts, model=self.model)
            )
            if token_count <= self._get_token_limit():
                embeddings = await self._aembed_batch(texts)
                return _format_output(texts, embeddings)

        # Use token-aware batching for larger inputs
        all_embeddings: list[list[float]] = [[] for _ in range(len(texts))]

        for batch_texts, batch_indices in self._build_batches(texts):
            batch_embeddings = await self._aembed_batch(batch_texts)
            for idx, embedding in zip(batch_indices, batch_embeddings):
                all_embeddings[idx] = embedding

        return _format_output(texts, all_embeddings)
