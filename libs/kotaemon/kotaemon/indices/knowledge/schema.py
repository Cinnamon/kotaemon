"""Shared types for canonical knowledge metadata."""

from typing import Literal

SourceType = Literal["markdown", "pdf", "faq", "ppt", "excel", "code", "wiki", "other"]

SUPPORTED_SOURCE_TYPES: tuple[SourceType, ...] = (
    "markdown",
    "pdf",
    "faq",
    "ppt",
    "excel",
    "code",
    "wiki",
    "other",
)
