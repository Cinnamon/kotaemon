"""Deterministic, bounded query enrichment without retrieval authority."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Sequence

from kotaemon.indices.knowledge.retrieval.contracts import EnrichedQuery

_HISTORY_TURNS = 3
_MAX_REWRITE_CHARS = 4096
_QUOTED = re.compile(r"(?P<quote>['\"`])(?P<value>.+?)(?P=quote)")
_PATH = re.compile(
    r"(?<![\w])(?:\.{0,2}/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+(?![\w])"
)
_CODE_OR_VERSION = re.compile(
    r"(?<![\w])(?:[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)+|"
    r"[0-9]+(?:[-_.][A-Za-z0-9]+)+)(?![\w])"
)
_FOLLOW_UP_PREFIX = re.compile(
    r"^\s*(?:and\b|also\b|what about\b|how about\b|"
    r"what about that\b|which one\b|same for\b)",
    re.IGNORECASE,
)
_TRAILING_PATH_PUNCTUATION = ".,;:!?)]}"


def _normalized_route(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _lexical_variant(query: str) -> str | None:
    quoted_spans = [(match.start(), match.end()) for match in _QUOTED.finditer(query)]
    matches: list[tuple[int, str]] = []

    for match in _QUOTED.finditer(query):
        literal = match.group("value").strip()
        if literal:
            matches.append((match.start(), literal))

    for pattern in (_PATH, _CODE_OR_VERSION):
        for match in pattern.finditer(query):
            if any(
                start <= match.start() and match.end() <= end
                for start, end in quoted_spans
            ):
                continue
            value = match.group(0).rstrip(_TRAILING_PATH_PUNCTUATION)
            if value:
                matches.append((match.start(), value))

    matches.sort(key=lambda item: item[0])
    unique: list[str] = []
    seen: set[str] = set()
    for _offset, value in matches:
        key = _normalized_route(value)
        if key and key not in seen:
            seen.add(key)
            unique.append(value)
    return " ".join(unique) if unique else None


def _bounded_user_history(user_history: Sequence[str]) -> tuple[str, ...]:
    if isinstance(user_history, str):
        candidates = (user_history,)
    else:
        candidates = user_history
    turns = [
        turn.strip() for turn in candidates if isinstance(turn, str) and turn.strip()
    ]
    return tuple(turns[-_HISTORY_TURNS:])


def _is_clear_follow_up(query: str) -> bool:
    if "..." in query or "…" in query:
        return True
    if _FOLLOW_UP_PREFIX.search(query):
        return True
    compact = " ".join(query.strip().casefold().split())
    return compact.startswith(
        (
            "那",
            "那呢",
            "那么呢",
            "然后呢",
            "还有呢",
            "这个呢",
            "它呢",
            "上述",
            "前面提到的",
            "同样呢",
        )
    )


class QueryEnricher:
    """Create soft lexical routes and optionally rewrite a follow-up question."""

    def __init__(
        self,
        *,
        rewriter: Callable[[str, tuple[str, ...]], str] | None = None,
        max_variants: int = 3,
    ) -> None:
        if isinstance(max_variants, bool) or not isinstance(max_variants, int):
            raise ValueError("max_variants must be a positive integer")
        if max_variants < 1:
            raise ValueError("max_variants must be a positive integer")
        self.rewriter = rewriter
        self.max_variants = max_variants

    def enrich(self, query: str, user_history: Sequence[str] = ()) -> EnrichedQuery:
        if not isinstance(query, str):
            raise TypeError("query must be a string")

        original_query = query
        fallback_query = query.strip()
        standalone_query = fallback_query
        reason = "original"

        bounded_history = _bounded_user_history(user_history)
        is_follow_up = _is_clear_follow_up(fallback_query)
        if self.rewriter is not None and bounded_history and is_follow_up:
            try:
                rewritten = self.rewriter(query, bounded_history)
            except Exception:
                rewritten = None
                reason = "rewriter_fallback"

            if isinstance(rewritten, str):
                candidate = rewritten.strip()
                has_invalid_control = any(
                    ord(character) < 32 and character not in "\t\n\r"
                    for character in candidate
                )
                if (
                    candidate
                    and len(candidate) <= _MAX_REWRITE_CHARS
                    and not has_invalid_control
                ):
                    if _normalized_route(candidate) == _normalized_route(
                        fallback_query
                    ):
                        standalone_query = fallback_query
                        reason = "original"
                    else:
                        standalone_query = candidate
                        reason = "rewritten"
                elif reason != "rewriter_fallback":
                    reason = "rewriter_fallback"
            elif reason != "rewriter_fallback":
                reason = "rewriter_fallback"
        elif self.rewriter is not None and bounded_history and not is_follow_up:
            reason = "topic_switch"

        if self.max_variants == 1 and _normalized_route(
            standalone_query
        ) != _normalized_route(original_query):
            standalone_query = fallback_query
            reason = "route_limit_fallback"

        lexical = _lexical_variant(original_query)
        candidates = [standalone_query, original_query]
        if lexical:
            candidates.append(lexical)

        variants: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            normalized = _normalized_route(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            variants.append(candidate)
            if len(variants) == self.max_variants:
                break

        if lexical:
            reason = f"{reason}+lexical"
        return EnrichedQuery(
            original_query=original_query,
            standalone_query=standalone_query,
            variants=tuple(variants),
            reason=reason,
        )
