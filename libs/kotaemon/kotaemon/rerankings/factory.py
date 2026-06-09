from __future__ import annotations

from enum import Enum

from .base import BaseReranking
from .cohere import CohereReranking
from .tei_fast_rerank import TeiFastReranking
from .voyageai import VoyageAIReranking


class RerankingVendor(str, Enum):
    COHERE = "CohereReranking"
    VOYAGE_AI = "VoyageAIReranking"
    TEI_FAST = "TeiFastReranking"


MP_VENDOR_CLS: dict[RerankingVendor, type[BaseReranking]] = {
    RerankingVendor.COHERE: CohereReranking,
    RerankingVendor.VOYAGE_AI: VoyageAIReranking,
    RerankingVendor.TEI_FAST: TeiFastReranking,
}


class RerankingFactory:
    @staticmethod
    def get_cls(vendor: RerankingVendor | str) -> type[BaseReranking]:
        """Return the class for *vendor*, coercing bare strings."""
        key = RerankingVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid reranking vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[RerankingVendor]:
        return list(MP_VENDOR_CLS.keys())
