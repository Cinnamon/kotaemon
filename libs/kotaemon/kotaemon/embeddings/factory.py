from __future__ import annotations

from enum import Enum

from .base import BaseEmbeddings
from .endpoint_based import EndpointEmbeddings
from .fastembed import FastEmbedEmbeddings
from .langchain_based import (
    LCAzureOpenAIEmbeddings,
    LCCohereEmbeddings,
    LCGoogleEmbeddings,
    LCHuggingFaceEmbeddings,
    LCMistralEmbeddings,
    LCOpenAIEmbeddings,
)
from .openai import AzureOpenAIEmbeddings, OpenAIEmbeddings
from .tei_endpoint_embed import TeiEndpointEmbeddings
from .voyageai import VoyageAIEmbeddings


class EmbeddingVendor(str, Enum):
    AZURE_OPENAI = "AzureOpenAIEmbeddings"
    OPENAI = "OpenAIEmbeddings"
    VOYAGE_AI = "VoyageAIEmbeddings"
    FAST_EMBED = "FastEmbedEmbeddings"
    ENDPOINT = "EndpointEmbeddings"
    TEI_ENDPOINT = "TeiEndpointEmbeddings"
    LC_OPENAI = "LCOpenAIEmbeddings"
    LC_AZURE_OPENAI = "LCAzureOpenAIEmbeddings"
    LC_COHERE = "LCCohereEmbeddings"
    LC_HUGGING_FACE = "LCHuggingFaceEmbeddings"
    LC_GOOGLE = "LCGoogleEmbeddings"
    LC_MISTRAL = "LCMistralEmbeddings"


MP_VENDOR_CLS: dict[EmbeddingVendor, type[BaseEmbeddings]] = {
    EmbeddingVendor.AZURE_OPENAI: AzureOpenAIEmbeddings,
    EmbeddingVendor.OPENAI: OpenAIEmbeddings,
    EmbeddingVendor.VOYAGE_AI: VoyageAIEmbeddings,
    EmbeddingVendor.FAST_EMBED: FastEmbedEmbeddings,
    EmbeddingVendor.ENDPOINT: EndpointEmbeddings,
    EmbeddingVendor.TEI_ENDPOINT: TeiEndpointEmbeddings,
    EmbeddingVendor.LC_OPENAI: LCOpenAIEmbeddings,
    EmbeddingVendor.LC_AZURE_OPENAI: LCAzureOpenAIEmbeddings,
    EmbeddingVendor.LC_COHERE: LCCohereEmbeddings,
    EmbeddingVendor.LC_HUGGING_FACE: LCHuggingFaceEmbeddings,
    EmbeddingVendor.LC_GOOGLE: LCGoogleEmbeddings,
    EmbeddingVendor.LC_MISTRAL: LCMistralEmbeddings,
}


class EmbeddingFactory:
    @staticmethod
    def get_cls(vendor: EmbeddingVendor | str) -> type[BaseEmbeddings]:
        """Return the class for *vendor*, coercing bare strings."""
        key = EmbeddingVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid embedding vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[EmbeddingVendor]:
        return list(MP_VENDOR_CLS.keys())
