"""Implements embeddings from [Voyage AI by MongoDB](https://voyageai.com)."""

import importlib
from dataclasses import dataclass
from importlib.metadata import version
from typing import Optional

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

vo = None

# Limits of the Voyage embeddings endpoints.
MAX_INPUTS_PER_REQUEST = 1000
# Contextualized models: `enable_auto_chunking` needs flat `list[str]` input and
# `input_type="document"`; the chunk size is the maximum the API accepts.
CONTEXTUALIZED_CHUNK_SIZE = 32_000
INPUT_TYPES = ("document", "query")


@dataclass(frozen=True)
class VoyageEmbeddingModel:
    """Request limits of one Voyage embedding model.

    Attributes:
        max_request_tokens: ceiling for the total number of tokens in one request.
            `None` means the Voyage docs do not state a ceiling, so requests are
            only split by `MAX_INPUTS_PER_REQUEST`.
        contextualized: the model is served by the contextualized chunk
            embeddings endpoint.
        max_query_request_tokens: ceiling for a contextualized request without
            auto-chunking (queries), when it differs from `max_request_tokens`.
    """

    max_request_tokens: Optional[int]
    contextualized: bool = False
    max_query_request_tokens: Optional[int] = None


_LITE = 1_000_000
_MID = 320_000
_STANDARD = 120_000

# Source: https://docs.voyageai.com/docs/embeddings and
# https://docs.voyageai.com/docs/contextualized-chunk-embeddings
VOYAGE_EMBEDDING_MODELS: dict[str, VoyageEmbeddingModel] = {
    # Current models
    "voyage-4-large": VoyageEmbeddingModel(_STANDARD),
    "voyage-4": VoyageEmbeddingModel(_MID),
    "voyage-4-lite": VoyageEmbeddingModel(_LITE),
    # Voyage documents no total-token ceiling for voyage-code-4.
    "voyage-code-4": VoyageEmbeddingModel(None),
    "voyage-finance-2": VoyageEmbeddingModel(_STANDARD),
    "voyage-law-2": VoyageEmbeddingModel(_STANDARD),
    "voyage-context-4": VoyageEmbeddingModel(
        _STANDARD, contextualized=True, max_query_request_tokens=32_000
    ),
    # Older models, still served by the API
    "voyage-3-large": VoyageEmbeddingModel(_STANDARD),
    "voyage-3.5": VoyageEmbeddingModel(_MID),
    "voyage-3.5-lite": VoyageEmbeddingModel(_LITE),
    "voyage-code-3": VoyageEmbeddingModel(_STANDARD),
    "voyage-context-3": VoyageEmbeddingModel(
        _STANDARD, contextualized=True, max_query_request_tokens=_STANDARD
    ),
    "voyage-3": VoyageEmbeddingModel(_STANDARD),
    "voyage-3-lite": VoyageEmbeddingModel(_STANDARD),
    "voyage-multilingual-2": VoyageEmbeddingModel(_STANDARD),
    "voyage-large-2-instruct": VoyageEmbeddingModel(_STANDARD),
    "voyage-large-2": VoyageEmbeddingModel(_STANDARD),
    "voyage-code-2": VoyageEmbeddingModel(_STANDARD),
    "voyage-2": VoyageEmbeddingModel(_MID),
    "voyage-lite-02-instruct": VoyageEmbeddingModel(_STANDARD),
    "voyage-02": VoyageEmbeddingModel(_STANDARD),
    "voyage-01": VoyageEmbeddingModel(_STANDARD),
    "voyage-lite-01": VoyageEmbeddingModel(_STANDARD),
    "voyage-lite-01-instruct": VoyageEmbeddingModel(_STANDARD),
}


def _import_voyageai():
    global vo
    if not vo:
        vo = importlib.import_module("voyageai")
    return vo


def _sdk_version() -> tuple[int, int]:
    major, minor = version("voyageai").split(".")[:2]
    return int(major), int(minor)


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


def split_into_batches(
    token_counts: list[int],
    max_tokens: Optional[int],
    max_inputs: int = MAX_INPUTS_PER_REQUEST,
) -> list[tuple[int, int]]:
    """Split consecutive texts into request-sized `(start, end)` ranges.

    A request holds at most `max_inputs` texts and, when `max_tokens` is set, at
    most `max_tokens` tokens in total. A single text above `max_tokens` is sent
    alone. The ranges are consecutive, so concatenating the per-range results
    keeps the input order.

    Args:
        token_counts: token count of each text
        max_tokens: total-token ceiling of one request, `None` for no ceiling
        max_inputs: maximum number of texts in one request
    """
    batches: list[tuple[int, int]] = []
    start = 0
    batch_tokens = 0
    for idx, count in enumerate(token_counts):
        over_tokens = max_tokens is not None and batch_tokens + count > max_tokens
        if idx > start and (idx - start >= max_inputs or over_tokens):
            batches.append((start, idx))
            start = idx
            batch_tokens = 0
        batch_tokens += count
    if len(token_counts) > start:
        batches.append((start, len(token_counts)))
    return batches


class VoyageAIEmbeddings(BaseEmbeddings):
    """Voyage AI by MongoDB provides best-in-class embedding models and rerankers.

    Requests are split by the model's token ceiling and the 1000-input limit, and
    the vectors come back in the order of the inputs.

    `voyage-context-*` models use the contextualized chunk embeddings API. Each
    input text is embedded as one document (sent with `enable_auto_chunking` and
    a chunk size of 32000 tokens), so an input must fit into one chunk: a longer
    one raises an error. Pass `input_type="query"` for queries.

    Pass `input_type` (`"document"` or `"query"`) when calling the model. Without
    it, regular models send no input type (as before) and contextualized models
    use `"document"`.
    """

    api_key: str = Param(None, help="Voyage API key", required=False)
    model: str = Param(
        "voyage-4",
        help=(
            "Model name to use: "
            + ", ".join(VOYAGE_EMBEDDING_MODELS)
            + ". See the Voyage "
            "[documentation](https://docs.voyageai.com/docs/embeddings) "
            "for all available embedding models."
        ),
        required=True,
    )
    output_dimension: Optional[int] = Param(
        None,
        help=(
            "The number of dimensions of the output embeddings. Only sent if set. "
            "The 4 series, 3.5 series, voyage-3-large, voyage-code-3 and "
            "contextualized models support 2048, 1024 (default), 512 and 256."
        ),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIEmbeddings.")
        if self.model not in VOYAGE_EMBEDDING_MODELS:
            raise ValueError(
                f"Unknown Voyage embedding model {self.model!r}. "
                f"Supported models: {', '.join(VOYAGE_EMBEDDING_MODELS)}."
            )

        self._spec = VOYAGE_EMBEDDING_MODELS[self.model]
        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)
        if self._spec.contextualized:
            if _sdk_version() < (0, 4):
                raise RuntimeError(
                    f"{self.model} needs voyageai>=0.4.0 "
                    "(contextualized embeddings with auto-chunking)."
                )

    @staticmethod
    def _check_input_type(input_type: Optional[str]):
        if input_type is not None and input_type not in INPUT_TYPES:
            raise ValueError(
                f"input_type must be one of {INPUT_TYPES} or None, got {input_type!r}"
            )

    def _batches(
        self, texts: list[str], input_type: Optional[str]
    ) -> list[tuple[int, int]]:
        """Split the texts into requests that respect the model's limits."""
        max_tokens = self._spec.max_request_tokens
        if self._spec.contextualized and (input_type or "document") == "query":
            max_tokens = self._spec.max_query_request_tokens

        if max_tokens is None or len(texts) < 2:
            # no ceiling to respect, or a single text: nothing to count
            return split_into_batches([0] * len(texts), None)
        encodings = self._client.tokenize(texts, model=self.model)
        return split_into_batches([len(e.ids) for e in encodings], max_tokens)

    def _embed_kwargs(self, input_type: Optional[str]) -> dict:
        kwargs: dict = {"model": self.model}
        if input_type is not None:
            kwargs["input_type"] = input_type
        if self.output_dimension is not None:
            kwargs["output_dimension"] = self.output_dimension
        return kwargs

    def _contextualized_kwargs(self, input_type: Optional[str]) -> dict:
        input_type = input_type or "document"
        kwargs = self._embed_kwargs(input_type)
        if input_type == "document":
            # auto-chunking is only valid for documents, as flat `list[str]`
            kwargs["enable_auto_chunking"] = True
            kwargs["chunk_size"] = CONTEXTUALIZED_CHUNK_SIZE
        return kwargs

    def _contextualized_vectors(self, result, count: int) -> list[list]:
        """One vector per input: an input must not be split into several chunks."""
        vectors = []
        for item in sorted(result.results, key=lambda r: r.index):
            if len(item.embeddings) != 1:
                raise ValueError(
                    f"Input {item.index} was split into {len(item.embeddings)} "
                    f"chunks by {self.model}; inputs must fit into one "
                    f"{CONTEXTUALIZED_CHUNK_SIZE}-token chunk."
                )
            vectors.append(item.embeddings[0])
        if len(vectors) != count:
            raise ValueError(
                f"{self.model} returned {len(vectors)} results for {count} inputs."
            )
        return vectors

    def invoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        self._check_input_type(input_type)
        texts = [t.content for t in self.prepare_input(text)]
        embeddings: list[list] = []
        for start, end in self._batches(texts, input_type):
            batch = texts[start:end]
            if self._spec.contextualized:
                result = self._client.contextualized_embed(
                    batch, **self._contextualized_kwargs(input_type)
                )
                embeddings.extend(self._contextualized_vectors(result, len(batch)))
            else:
                result = self._client.embed(batch, **self._embed_kwargs(input_type))
                embeddings.extend(result.embeddings)
        return _format_output(texts, embeddings)

    async def ainvoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        input_type: Optional[str] = None,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        self._check_input_type(input_type)
        texts = [t.content for t in self.prepare_input(text)]
        embeddings: list[list] = []
        for start, end in self._batches(texts, input_type):
            batch = texts[start:end]
            if self._spec.contextualized:
                result = await self._aclient.contextualized_embed(
                    batch, **self._contextualized_kwargs(input_type)
                )
                embeddings.extend(self._contextualized_vectors(result, len(batch)))
            else:
                result = await self._aclient.embed(
                    batch, **self._embed_kwargs(input_type)
                )
                embeddings.extend(result.embeddings)
        return _format_output(texts, embeddings)
