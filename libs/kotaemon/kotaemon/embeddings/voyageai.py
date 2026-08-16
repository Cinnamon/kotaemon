"""Implements embeddings from [Voyage AI](https://voyageai.com)."""

import importlib

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings

vo = None

# Maximum number of texts Voyage AI accepts in a single request.
MAX_BATCH_SIZE = 1000

# Total-token budget per request for each model. Batches are built so the
# estimated token count never exceeds the model's limit. Unknown models fall
# back to the smallest common budget. Kept in sync with the Voyage AI catalog
# at https://docs.voyageai.com/docs/embeddings.
VOYAGE_TOTAL_TOKEN_LIMITS: dict[str, int] = {
    # contextualized-chunk embeddings
    "voyage-context-4": 120_000,
    "voyage-context-3": 120_000,
    # general / domain embeddings
    "voyage-4-large": 120_000,
    "voyage-4": 320_000,
    "voyage-4-lite": 1_000_000,
    "voyage-4-nano": 1_000_000,
    "voyage-code-4": 120_000,
    "voyage-3-large": 120_000,
    "voyage-3.5": 320_000,
    "voyage-3.5-lite": 1_000_000,
    "voyage-3": 120_000,
    "voyage-3-lite": 120_000,
    "voyage-code-3": 120_000,
    "voyage-code-2": 120_000,
    "voyage-finance-2": 120_000,
    "voyage-law-2": 120_000,
    "voyage-multilingual-2": 120_000,
    "voyage-large-2-instruct": 120_000,
    "voyage-large-2": 120_000,
    "voyage-2": 320_000,
}

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

    Supports both the regular text embedding models (``voyage-3.5``,
    ``voyage-3-large``, ``voyage-code-3``, ...) and the contextualized-chunk
    embedding models (``voyage-context-4``, ``voyage-context-3``).

    Note on contextualized models: every input string is embedded as its **own,
    independent document**. The batch is sent as a flat ``list[str]`` with
    server-side auto-chunking so each string resolves to exactly one chunk and
    therefore exactly one embedding. Cross-input contextualization is
    intentionally not used, because generic ``embed_many`` callers pass
    unrelated texts.
    """

    api_key: str = Param(None, help="Voyage API key", required=False)
    model: str = Param(
        "voyage-3.5",
        help=(
            "Model name to use. The Voyage "
            "[documentation](https://docs.voyageai.com/docs/embeddings) "
            "lists the available embedding models; the contextualized-chunk "
            "models (e.g. `voyage-context-4`) are documented "
            "[here](https://docs.voyageai.com/docs/contextualized-chunk-embeddings)."
        ),
        required=True,
    )
    chunk_size: int = Param(
        32_000,
        help=(
            "Target chunk size (in tokens) for contextualized models. Set to the "
            "per-chunk context window so each document-side input resolves to a "
            "single chunk and a single embedding."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.api_key:
            raise ValueError("API key must be provided for VoyageAIEmbeddings.")

        self._client = _import_voyageai().Client(api_key=self.api_key)
        self._aclient = _import_voyageai().AsyncClient(api_key=self.api_key)

    @property
    def _is_contextualized(self) -> bool:
        return self.model.startswith("voyage-context")

    def _token_limit(self) -> int:
        return VOYAGE_TOTAL_TOKEN_LIMITS.get(self.model, DEFAULT_TOKEN_LIMIT)

    def _iter_batches(self, texts: list[str]):
        """Yield batches bounded by both item count and estimated token count.

        Batches respect ``MAX_BATCH_SIZE`` items and the model's total-token
        budget. A single text larger than the token budget is still yielded on
        its own rather than being dropped.
        """
        max_tokens = self._token_limit()
        index = 0
        while index < len(texts):
            batch: list[str] = []
            batch_tokens = 0
            while index < len(texts) and len(batch) < MAX_BATCH_SIZE:
                tokens = self._client.tokenize([texts[index]], model=self.model)
                n_tokens = len(tokens[0])
                # Close the batch once adding this text would overflow the token
                # budget, unless the batch is empty (oversized text goes alone).
                if batch_tokens + n_tokens > max_tokens and batch:
                    break
                batch.append(texts[index])
                batch_tokens += n_tokens
                index += 1
            yield batch

    def _embed_contextualized(self, texts: list[str], input_type: str) -> list[list]:
        # Auto-chunking is rejected by the API for queries, so only document-side
        # inputs enable it (and carry chunk_size).
        enable_auto_chunking = input_type != "query"
        embeddings: list[list] = []
        for batch in self._iter_batches(texts):
            params: dict = {
                "inputs": batch,  # flat list[str]: each string is its own document
                "model": self.model,
                "input_type": input_type,
                "enable_auto_chunking": enable_auto_chunking,
            }
            if enable_auto_chunking:
                params["chunk_size"] = self.chunk_size
            response = self._client.contextualized_embed(**params)
            # Each input resolves to exactly one chunk -> one embedding.
            embeddings.extend(result.embeddings[0] for result in response.results)
        return embeddings

    async def _aembed_contextualized(
        self, texts: list[str], input_type: str
    ) -> list[list]:
        enable_auto_chunking = input_type != "query"
        embeddings: list[list] = []
        for batch in self._iter_batches(texts):
            params: dict = {
                "inputs": batch,
                "model": self.model,
                "input_type": input_type,
                "enable_auto_chunking": enable_auto_chunking,
            }
            if enable_auto_chunking:
                params["chunk_size"] = self.chunk_size
            response = await self._aclient.contextualized_embed(**params)
            embeddings.extend(result.embeddings[0] for result in response.results)
        return embeddings

    def _embed_regular(self, texts: list[str], input_type: str) -> list[list]:
        embeddings: list[list] = []
        for batch in self._iter_batches(texts):
            response = self._client.embed(
                batch, model=self.model, input_type=input_type
            )
            embeddings.extend(response.embeddings)
        return embeddings

    async def _aembed_regular(self, texts: list[str], input_type: str) -> list[list]:
        embeddings: list[list] = []
        for batch in self._iter_batches(texts):
            response = await self._aclient.embed(
                batch, model=self.model, input_type=input_type
            )
            embeddings.extend(response.embeddings)
        return embeddings

    def invoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        input_type: str = "document",
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]
        if not texts:
            return []

        if self._is_contextualized:
            embeddings = self._embed_contextualized(texts, input_type)
        else:
            embeddings = self._embed_regular(texts, input_type)

        return _format_output(texts, embeddings)

    async def ainvoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        input_type: str = "document",
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        texts = [t.content for t in self.prepare_input(text)]
        if not texts:
            return []

        if self._is_contextualized:
            embeddings = await self._aembed_contextualized(texts, input_type)
        else:
            embeddings = await self._aembed_regular(texts, input_type)

        return _format_output(texts, embeddings)
