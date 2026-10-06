"""Thread-safe request-local retrieval traces with conservative serialization."""

from __future__ import annotations

import json
import logging
import math
import numbers
import threading
from collections.abc import Mapping
from copy import deepcopy
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_OMIT = object()
_CONTENT_KEYS = {
    "answer",
    "body",
    "chunk_text",
    "content",
    "data",
    "evidence",
    "evidence_html",
    "html",
    "image_data",
    "image_origin",
    "images",
    "payload",
    "source_text",
    "text",
}
_NEVER_EXPORT_KEYS = {
    "absolute_path",
    "file_path",
    "local_path",
    "metadata",
    "physical_path",
    "storage_path",
    "upload_path",
}


def _looks_like_physical_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith(
        (
            "/Users/",
            "/home/",
            "/tmp/",
            "/private/",
            "/var/folders/",
            "file://",
        )
    ) or (len(value) >= 3 and value[1:3] == ":\\")


def _safe_value(value: Any, *, include_content: bool, key: str = "") -> Any:
    """Copy a value into JSON primitives while dropping content and raw models."""
    normalized_key = key.casefold()
    if normalized_key in _NEVER_EXPORT_KEYS:
        return _OMIT
    if normalized_key in _CONTENT_KEYS and not include_content:
        return _OMIT
    if normalized_key == "branch_errors" and isinstance(value, Mapping):
        # Existing dict hooks include backend exception messages. Keep only their
        # type in structured exports because messages may contain local paths or text.
        output = {}
        for branch, error in value.items():
            if isinstance(error, BaseException):
                error_type = type(error).__name__
            elif isinstance(error, str):
                error_type = error.split(":", 1)[0].split(".")[-1]
            elif isinstance(error, Mapping):
                error_type = error.get("type", "Error")
            else:
                error_type = type(error).__name__
            output[str(branch)] = {"type": str(error_type)}
        return output

    if value is None or isinstance(value, (bool, int, str)):
        if isinstance(value, str) and _looks_like_physical_path(value):
            return _OMIT
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return _safe_value(value.value, include_content=include_content, key=key)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, BaseException):
        return {"type": type(value).__name__}
    if isinstance(value, Mapping):
        result = {}
        for raw_key, item in value.items():
            if not isinstance(raw_key, (str, int, float, bool)):
                continue
            string_key = str(raw_key)
            cleaned = _safe_value(item, include_content=include_content, key=string_key)
            if cleaned is not _OMIT:
                result[string_key] = cleaned
        return result
    if isinstance(value, (list, tuple)):
        result = []
        for item in value:
            cleaned = _safe_value(item, include_content=include_content)
            if cleaned is not _OMIT:
                result.append(cleaned)
        return result
    if isinstance(value, (set, frozenset)):
        cleaned = [_safe_value(item, include_content=include_content) for item in value]
        return sorted(
            (item for item in cleaned if item is not _OMIT), key=lambda item: str(item)
        )
    # Document, exception wrappers, NumPy arrays, and model objects do not belong
    # in a trace snapshot. Producers must extract IDs and numeric fields explicitly.
    return _OMIT


class RetrievalTrace:
    """A request-owned event collector safe to share with recall worker threads.

    ``update`` intentionally accepts both ``mapping`` and keyword fields so the
    existing plain-dict trace hooks can use it without changing call sites.
    The event list is authoritative; summary fields make common values easier to
    inspect and are detached whenever a snapshot is requested.
    """

    schema_version = 1

    def __init__(self, *, include_content: bool = False):
        self.include_content = bool(include_content)
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {
            "schema_version": self.schema_version,
            "events": [],
        }

    def update(self, mapping: Mapping[str, Any] | None = None, **fields: Any) -> None:
        """Update summary fields using the built-in dict adapter calling shape."""
        if mapping is not None:
            if not isinstance(mapping, Mapping):
                raise TypeError("RetrievalTrace.update expects a mapping")
            fields = {**mapping, **fields}
        cleaned = self._clean_fields(fields)
        with self._lock:
            target = self._projection_target(cleaned)
            for key, value in cleaned.items():
                if key in {"events", "attempts", "rerankers"}:
                    # These histories are append-only so a legacy update cannot
                    # erase evidence recorded by earlier stages.
                    if key == "events":
                        continue
                    existing = target.setdefault(key, [])
                    if isinstance(value, list):
                        existing.extend(deepcopy(value))
                    continue
                target[key] = deepcopy(value)

    def record(self, stage: str, **fields: Any) -> None:
        """Append one named stage event and update its useful summary projection."""
        if not isinstance(stage, str) or not stage:
            raise ValueError("Trace stage must be a non-empty string")
        clean = self._clean_fields(fields)
        event = {"stage": stage, **clean}
        with self._lock:
            self._state["events"].append(deepcopy(event))
            self._project_event(stage, clean, self._projection_target(clean))

    def scoped(self, **context: Any) -> "_TraceScope":
        """Return a lightweight writer that tags events for one QA subquery."""
        return _TraceScope(self, context)

    def _clean_fields(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        result = {}
        for key, value in fields.items():
            if not isinstance(key, str):
                continue
            cleaned = _safe_value(value, include_content=self.include_content, key=key)
            if cleaned is not _OMIT:
                result[key] = cleaned
        return result

    def _projection_target(self, fields: Mapping[str, Any]) -> dict[str, Any]:
        if fields.get("query_kind") != "extra_table":
            return self._state
        auxiliary = self._state.setdefault("auxiliary_retrievals", {})
        target = auxiliary.setdefault("extra_table", {})
        target.setdefault("query_kind", "extra_table")
        return target

    def _project_event(
        self, stage: str, fields: dict[str, Any], target: dict[str, Any]
    ) -> None:
        if stage == "request":
            target.update(fields)
        elif stage in {
            "plan",
            "explicit_filters",
            "source_scope",
            "chunk_scope",
            "context",
        }:
            target[stage] = deepcopy(fields.get(stage, fields))
        elif stage == "recall_attempt":
            target.setdefault("attempts", []).append(deepcopy(fields))
        elif stage == "merged":
            target["merged_ids"] = deepcopy(fields.get("ids", []))
        elif stage == "reranker":
            target.setdefault("rerankers", []).append(deepcopy(fields))
        elif stage == "diversity":
            target["diversity"] = deepcopy(fields)
            if "selected_ids" in fields:
                target["diversity_selected_ids"] = deepcopy(fields["selected_ids"])
        elif stage == "scope_fallback":
            target["scope_fallback"] = True
            target["scope_fallback_reason"] = fields.get("reason")
        elif stage == "final":
            target["final_chunk_ids"] = deepcopy(fields.get("ids", []))
        elif stage == "final_ui":
            target["final_ui_chunk_ids"] = deepcopy(fields.get("ids", []))
        elif stage == "no_search":
            target["search_status"] = "not_run"
            target["no_search_reason"] = fields.get("reason")

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible snapshot."""
        with self._lock:
            return deepcopy(self._state)

    def to_json(self, **kwargs: Any) -> str:
        options = {"ensure_ascii": False, "allow_nan": False}
        options.update(kwargs)
        return json.dumps(self.to_dict(), **options)

    def __getstate__(self):
        # Theflow records component inputs by pickling them. Preserve only a
        # detached snapshot in that log copy; the live request collector and lock
        # remain owned by the caller.
        return {
            "include_content": self.include_content,
            "state": self.to_dict(),
        }

    def __setstate__(self, state):
        self.include_content = bool(state.get("include_content", False))
        self._lock = threading.RLock()
        self._state = deepcopy(state.get("state", {"schema_version": 1, "events": []}))


class _TraceScope:
    """Context-tagged facade sharing the parent collector and its lock."""

    def __init__(self, trace: RetrievalTrace, context: Mapping[str, Any]):
        self._trace = trace
        self._context = dict(context)
        self.include_content = trace.include_content

    def update(self, mapping: Mapping[str, Any] | None = None, **fields: Any) -> None:
        if mapping is not None:
            fields = {**mapping, **fields}
        fields.update(self._context)
        self._trace.update(fields)

    def record(self, stage: str, **fields: Any) -> None:
        fields.update(self._context)
        self._trace.record(stage, **fields)

    def scoped(self, **context: Any) -> "_TraceScope":
        return _TraceScope(self._trace, {**self._context, **context})

    def to_dict(self) -> dict[str, Any]:
        return self._trace.to_dict()

    def to_json(self, **kwargs: Any) -> str:
        return self._trace.to_json(**kwargs)

    def __getstate__(self):
        return {"trace": self._trace, "context": self._context}

    def __setstate__(self, state):
        self._trace = state["trace"]
        self._context = dict(state["context"])
        self.include_content = self._trace.include_content


def trace_update(trace: Any, **fields: Any) -> None:
    """Best-effort update shared by structured collectors and legacy dict hooks."""
    if trace is None:
        return
    try:
        trace.update(fields)
    except Exception:
        logger.exception("Could not update optional retrieval trace")


def trace_event(trace: Any, stage: str, **fields: Any) -> None:
    """Best-effort named event write; plain dict traces keep their field contract."""
    if trace is None:
        return
    try:
        recorder = getattr(trace, "record", None)
        if callable(recorder):
            recorder(stage, **fields)
        elif isinstance(trace, dict):
            trace.update(fields)
        else:
            trace.update(fields)
    except Exception:
        logger.exception("Could not record optional retrieval trace stage %s", stage)


def trace_scoped(trace: Any, **context: Any) -> Any:
    """Return a context-tagged trace writer, falling back to the original sink."""
    if trace is None:
        return None
    try:
        scoped = getattr(trace, "scoped", None)
        if callable(scoped):
            result = scoped(**context)
            return trace if result is None else result
    except Exception:
        logger.exception("Could not scope optional retrieval trace")
    return trace


__all__ = ["RetrievalTrace", "trace_event", "trace_scoped", "trace_update"]
