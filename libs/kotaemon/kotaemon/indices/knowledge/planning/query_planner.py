"""Deterministic, metadata-backed query scoping with safe global fallback."""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from kotaemon.indices.knowledge.schema import SUPPORTED_SOURCE_TYPES

from .retrieval_plan import RetrievalPlan


@dataclass(frozen=True)
class KnowledgeSource:
    """Safe logical metadata for one SQL Source row.

    Legacy sources are represented with ``None`` canonical fields. ``source_name``
    is retained for catalog listing, but is deliberately not a planner fallback.
    """

    source_id: str
    source_type: str | None = None
    virtual_path: str | None = None
    document_name: str | None = None
    entity: Mapping[str, Any] = field(default_factory=dict)
    source_name: str | None = None


class SourceCatalog(Protocol):
    def list_sources(
        self, allowed_source_ids: Sequence[str] | None = None
    ) -> Sequence[KnowledgeSource]: ...


_CJK_CONTEXT_AFTER = (
    "实习",
    "工作",
    "在",
    "的",
    "负责",
    "做",
    "担任",
    "期间",
    "相关",
    "经历",
    "项目",
    "介绍",
    "背景",
    "简历",
    "信息",
    "情况",
    "如何",
    "怎么",
    "什么",
    "是谁",
    "是否",
    "有什么",
    "参与",
    "开展",
    "完成",
    "曾",
    "提到",
    "了",
    "过",
)
_CJK_CONTEXT_BEFORE = "、，。；：？?！!（()【】及与和跟向请找问到让对于关于是把由在同"
_CJK_CONJUNCTIONS = ("以及", "和", "及", "与", "跟", "、")
_GLOB_CHARS = frozenset("*?[]")


def normalize_logical_path(value: str) -> str:
    """Normalize a logical POSIX path without filesystem access.

    Parent traversal and glob syntax are rejected because callers need exact
    logical names, not paths to resolve or patterns to expand.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Logical path must be a non-empty string")
    raw = value.strip()
    if "\x00" in raw or "\\" in raw or any(char in _GLOB_CHARS for char in raw):
        raise ValueError("Logical path contains unsupported characters")
    if re.match(r"^[A-Za-z]:/", raw):
        raise ValueError("Logical path cannot be a drive-qualified filesystem path")
    parts: list[str] = []
    for part in raw.split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError("Logical path cannot contain parent traversal")
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/"


def _normalized_text(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _is_cjk(char: str) -> bool:
    if not char:
        return False
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2FA1F
    )


def _is_word_char(char: str) -> bool:
    return bool(char) and (
        char == "_" or char.isalnum() or unicodedata.category(char).startswith("M")
    )


def _has_cjk_context_boundary(query: str, offset: int, known_values: set[str]) -> bool:
    """Consume query-context terms and conjoined metadata values.

    A known catalog value after a conjunction is treated as another exact
    mention, so the planner sees both sides of queries such as ``张三和李四``.
    Unknown adjacent CJK text remains a boundary failure.
    """
    while offset < len(query) and _is_cjk(query[offset]):
        conjunction = next(
            (
                candidate
                for candidate in _CJK_CONJUNCTIONS
                if query.startswith(candidate, offset)
            ),
            None,
        )
        if conjunction is not None:
            offset += len(conjunction)
            value = next(
                (
                    candidate
                    for candidate in sorted(known_values, key=len, reverse=True)
                    if all(_is_cjk(char) for char in candidate)
                    and query.startswith(candidate, offset)
                ),
                None,
            )
            if value is None:
                return False
            offset += len(value)
            continue

        context = next(
            (
                candidate
                for candidate in sorted(_CJK_CONTEXT_AFTER, key=len, reverse=True)
                if query.startswith(candidate, offset)
            ),
            None,
        )
        if context is None:
            return False
        offset += len(context)
    return True


def _find_mentions(
    query: str, value: str, known_values: set[str]
) -> list[tuple[int, int]]:
    """Return exact mentions with conservative CJK name boundaries.

    Latin and numeric names use Unicode word boundaries. Chinese names have no
    whitespace tokens, so a short value is rejected when it would consume the
    prefix of a longer known catalog value; a small set of common query-context
    continuations permits natural questions such as ``张三实习期间``.
    """
    if not query or not value:
        return []
    results: list[tuple[int, int]] = []
    cursor = 0
    all_cjk = all(_is_cjk(char) for char in value)
    while True:
        start = query.find(value, cursor)
        if start < 0:
            break
        end = start + len(value)
        cursor = start + 1

        if any(
            longer != value
            and len(longer) > len(value)
            and longer.startswith(value)
            and query.startswith(longer, start)
            for longer in known_values
        ):
            continue

        before = query[start - 1] if start else ""
        after = query[end] if end < len(query) else ""
        if all_cjk:
            left_ok = not before or not _is_cjk(before) or before in _CJK_CONTEXT_BEFORE
            right_ok = (
                not after
                or not _is_cjk(after)
                or _has_cjk_context_boundary(query, end, known_values)
            )
        else:
            left_ok = not _is_word_char(before)
            right_ok = not _is_word_char(after)
        if left_ok and right_ok:
            results.append((start, end))
    return results


def _safe_scalar(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized if normalized else None
    if isinstance(value, (bool, int, float)):
        return str(value)
    return None


@dataclass(frozen=True)
class _Mention:
    source_id: str
    kind: str
    value: str
    entity_key: str | None = None


class QueryPlanner:
    """Resolve exact metadata references and keep uncertain queries global."""

    HIGH_CONFIDENCE = 0.85

    def plan(
        self,
        query: str,
        catalog: SourceCatalog,
        *,
        path: str | None = None,
        source_types: Sequence[str] | None = None,
        filters: Mapping[str, Any] | None = None,
        allowed_source_ids: Sequence[str] | None = None,
    ) -> RetrievalPlan:
        original_query = str(query)
        entries = self._visible_entries(catalog, allowed_source_ids)
        normalized_path = normalize_logical_path(path) if path is not None else None
        requested_types = self._normalize_source_types(source_types)
        requested_filters = self._normalize_filters(filters, entries)
        has_explicit_constraints = (
            normalized_path is not None
            or source_types is not None
            or bool(requested_filters)
        )
        if not entries:
            return RetrievalPlan(
                query=original_query,
                semantic_query=original_query,
                source_types=requested_types,
                metadata_filters=requested_filters,
                confidence=1.0,
                reason="catalog has no visible sources",
                source_ids=(),
            )

        candidates = entries
        if normalized_path is not None:
            candidates = [
                item
                for item in candidates
                if self._metadata_path(item) == normalized_path
            ]
        if source_types is not None:
            candidates = [
                item for item in candidates if item.source_type in requested_types
            ]
        if filters is not None:
            candidates = [
                item
                for item in candidates
                if self._entity_contains(item.entity, requested_filters)
            ]

        query_norm = _normalized_text(original_query)
        mentions = self._query_mentions(query_norm, candidates)
        mentioned_ids = {mention.source_id for mention in mentions}
        unique_query_scope = len(mentioned_ids) == 1

        if not mentions:
            if has_explicit_constraints:
                scoped = candidates
                confidence = 1.0
                reason = "explicit constraints resolved; no exact query reference"
            else:
                scoped = None
                confidence = 0.0
                reason = "no exact metadata reference; global search"
        elif unique_query_scope:
            scoped = [item for item in candidates if item.source_id in mentioned_ids]
            confidence = 1.0
            reason = "one unambiguous exact metadata reference"
        elif has_explicit_constraints:
            scoped = candidates
            confidence = 1.0
            reason = "ambiguous query reference; explicit constraints retained"
        else:
            scoped = None
            confidence = 0.0
            reason = "ambiguous exact metadata reference; global search"

        if scoped is None:
            source_ids = None
            resolved_paths: tuple[str, ...] = ()
            resolved_types = requested_types
            metadata_filters = dict(requested_filters)
        else:
            scoped = sorted(scoped, key=lambda item: item.source_id)
            source_ids = tuple(item.source_id for item in scoped)
            resolved_paths = tuple(
                sorted(
                    {
                        logical_path
                        for item in scoped
                        if (logical_path := self._metadata_path(item)) is not None
                    }
                )
            )
            resolved_types = (
                requested_types
                if source_types is not None
                else tuple(
                    sorted({item.source_type for item in scoped if item.source_type})
                )
            )
            metadata_filters = dict(requested_filters)
            if unique_query_scope and len(scoped) == 1:
                target_id = scoped[0].source_id
                for mention in mentions:
                    if mention.source_id == target_id and mention.kind == "entity":
                        metadata_filters[mention.entity_key or ""] = mention.value
                metadata_filters.pop("", None)

        return RetrievalPlan(
            query=original_query,
            semantic_query=original_query,
            source_types=tuple(sorted(resolved_types)),
            virtual_paths=resolved_paths,
            metadata_filters=dict(sorted(metadata_filters.items())),
            confidence=confidence,
            reason=reason,
            source_ids=source_ids,
        )

    @staticmethod
    def _visible_entries(catalog, allowed_source_ids):
        allowed = None
        if allowed_source_ids is not None:
            if isinstance(allowed_source_ids, str):
                normalized_allowed_ids = [allowed_source_ids]
                allowed = {allowed_source_ids}
            else:
                normalized_allowed_ids = [
                    str(value) for value in allowed_source_ids if value is not None
                ]
                allowed = set(normalized_allowed_ids)
        else:
            normalized_allowed_ids = None
        entries = catalog.list_sources(allowed_source_ids=normalized_allowed_ids)
        output = []
        seen: set[str] = set()
        for item in entries:
            source_id = getattr(item, "source_id", None)
            if not isinstance(source_id, str) or not source_id or source_id in seen:
                continue
            if allowed is not None and source_id not in allowed:
                continue
            seen.add(source_id)
            output.append(
                KnowledgeSource(
                    source_id=source_id,
                    source_type=(
                        item.source_type
                        if item.source_type in SUPPORTED_SOURCE_TYPES
                        else None
                    ),
                    virtual_path=QueryPlanner._metadata_path(item),
                    document_name=(
                        item.document_name
                        if isinstance(item.document_name, str)
                        and item.document_name.strip()
                        and "/" not in item.document_name
                        and "\\" not in item.document_name
                        else None
                    ),
                    entity=QueryPlanner._safe_entity(item.entity),
                    source_name=getattr(item, "source_name", None),
                )
            )
        return output

    @staticmethod
    def _metadata_path(item: KnowledgeSource) -> str | None:
        if not isinstance(item.virtual_path, str):
            return None
        try:
            return normalize_logical_path(item.virtual_path)
        except ValueError:
            return None

    @staticmethod
    def _safe_entity(entity) -> dict[str, str]:
        if not isinstance(entity, Mapping):
            return {}
        return {
            key: value
            for raw_key, raw_value in entity.items()
            if isinstance(raw_key, str)
            and (key := raw_key.strip())
            and (value := _safe_scalar(raw_value)) is not None
        }

    @classmethod
    def _normalize_source_types(cls, source_types):
        if source_types is None:
            return ()
        if isinstance(source_types, str):
            source_types = [source_types]
        if not isinstance(source_types, Sequence):
            raise ValueError("Source types must be a sequence")
        values = tuple(sorted({str(value).strip().lower() for value in source_types}))
        unsupported = sorted(set(values) - set(SUPPORTED_SOURCE_TYPES))
        if unsupported:
            raise ValueError(f"Unsupported source type: {', '.join(unsupported)}")
        return values

    @classmethod
    def _normalize_filters(cls, filters, entries):
        if filters is None:
            return {}
        if not isinstance(filters, Mapping):
            raise ValueError("Metadata filters must be a mapping")
        available_keys = {
            key for item in entries for key in cls._safe_entity(item.entity)
        }
        output = {}
        for key, value in filters.items():
            if not isinstance(key, str) or key not in available_keys:
                raise ValueError(f"Unsupported metadata filter: {key}")
            scalar = _safe_scalar(value)
            if scalar is None:
                raise ValueError(f"Metadata filter {key!r} must be a scalar value")
            output[key] = scalar
        return dict(sorted(output.items()))

    @classmethod
    def _entity_contains(cls, entity, filters):
        safe_entity = cls._safe_entity(entity)
        return all(
            key in safe_entity
            and _normalized_text(safe_entity[key]) == _normalized_text(value)
            for key, value in filters.items()
        )

    @classmethod
    def _query_mentions(cls, query, entries):
        values: set[str] = set()
        candidates: list[tuple[KnowledgeSource, str, str, str, str | None]] = []
        for item in entries:
            for key, value in cls._safe_entity(item.entity).items():
                normalized = _normalized_text(value)
                if normalized:
                    values.add(normalized)
                    candidates.append((item, "entity", normalized, value, key))
            logical_path = cls._metadata_path(item)
            if logical_path:
                for segment in logical_path.split("/"):
                    normalized = _normalized_text(segment)
                    if normalized:
                        values.add(normalized)
                        candidates.append((item, "path", normalized, segment, None))
            if item.document_name:
                name = item.document_name.strip()
                stem = re.sub(r"\.[^.]+$", "", name)
                for candidate in {name, stem}:
                    normalized = _normalized_text(candidate)
                    if normalized:
                        values.add(normalized)
                        candidates.append(
                            (item, "document", normalized, candidate, None)
                        )

        mentions: set[_Mention] = set()
        for item, kind, normalized, original_value, key in candidates:
            if _find_mentions(query, normalized, values):
                mentions.add(_Mention(item.source_id, kind, original_value, key))
        return sorted(
            mentions,
            key=lambda item: (
                item.source_id,
                item.kind,
                item.entity_key or "",
                item.value,
            ),
        )
