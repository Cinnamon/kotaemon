from typing import Optional

from kotaemon.base import Document, DocumentWithEmbedding, Param

from .base import BaseEmbeddings


class LiteLLMEmbeddings(BaseEmbeddings):
    """LiteLLM AI Gateway embeddings — unified interface to 100+ providers

    LiteLLM provides a single API to generate embeddings from OpenAI,
    Cohere, Bedrock, Azure, Hugging Face, and many other providers.

    Provider-specific model formats:
        - OpenAI: ``text-embedding-3-small``
        - Cohere: ``cohere/embed-english-v3.0``
        - Azure: ``azure/my-embedding-deployment``
        - Bedrock: ``bedrock/amazon.titan-embed-text-v1``

    See https://docs.litellm.ai/docs/embedding/supported_embedding
    for the full list of supported embedding providers.

    Attributes:
        model: Embedding model identifier in LiteLLM format.
        api_key: API key for the underlying provider.
        api_base: Custom API base URL (e.g. for LiteLLM proxy gateway).
        dimensions: Number of dimensions for the output embeddings.
    """

    _dependencies = ["litellm"]

    model: str = Param(
        help=(
            "LiteLLM embedding model identifier. Format varies by "
            "provider, e.g. 'text-embedding-3-small', "
            "'cohere/embed-english-v3.0'. "
            "See https://docs.litellm.ai/docs/embedding/supported_embedding"
        ),
        required=True,
    )
    api_key: Optional[str] = Param(None, help="API key for the underlying provider")
    api_base: Optional[str] = Param(
        None,
        help="Custom API base URL (e.g. for a LiteLLM proxy gateway)",
    )
    dimensions: Optional[int] = Param(
        None,
        help=(
            "Number of dimensions for the output embeddings. "
            "Only supported by certain models."
        ),
    )

    def _prepare_params(self, **kwargs) -> dict:
        params: dict = {"model": self.model}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.api_base:
            params["api_base"] = self.api_base
        if self.dimensions is not None:
            params["dimensions"] = self.dimensions
        params.update(kwargs)
        return params

    def invoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        import litellm

        input_docs = self.prepare_input(text)
        texts = [doc.text if doc.text else " " for doc in input_docs]
        params = self._prepare_params(**kwargs)

        resp = litellm.embedding(input=texts, **params)
        resp_dict = resp.model_dump()
        data = sorted(resp_dict["data"], key=lambda x: x["index"])

        return [
            DocumentWithEmbedding(embedding=item["embedding"], content=doc)
            for doc, item in zip(input_docs, data)
        ]

    async def ainvoke(
        self,
        text: str | list[str] | Document | list[Document],
        *args,
        **kwargs,
    ) -> list[DocumentWithEmbedding]:
        import litellm

        input_docs = self.prepare_input(text)
        texts = [doc.text if doc.text else " " for doc in input_docs]
        params = self._prepare_params(**kwargs)

        resp = await litellm.aembedding(input=texts, **params)
        resp_dict = resp.model_dump()
        data = sorted(resp_dict["data"], key=lambda x: x["index"])

        return [
            DocumentWithEmbedding(embedding=item["embedding"], content=doc)
            for doc, item in zip(input_docs, data)
        ]
