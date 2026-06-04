from __future__ import annotations

from enum import Enum

from .base import BaseWebSearch
from .jina import JinaWebSearch
from .tavily import TavilyWebSearch


class WebSearchVendor(str, Enum):
    TAVILY = "TavilyWebSearch"
    JINA = "JinaWebSearch"


MP_VENDOR_CLS: dict[WebSearchVendor, type[BaseWebSearch]] = {
    WebSearchVendor.TAVILY: TavilyWebSearch,
    WebSearchVendor.JINA: JinaWebSearch,
}


class WebSearchFactory:
    @staticmethod
    def get_cls(vendor: WebSearchVendor | str) -> type[BaseWebSearch]:
        """Return the class for *vendor*, coercing bare strings."""
        key = WebSearchVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid web search vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[WebSearchVendor]:
        return list(MP_VENDOR_CLS.keys())
