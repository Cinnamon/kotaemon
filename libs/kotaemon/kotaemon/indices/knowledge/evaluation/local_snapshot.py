"""Fail-closed validation for reviewed, source-level local gold snapshots.

Snapshot payloads are read only after their manifest and filesystem shape have
been checked. Source documents are never opened here; their repository-relative
provenance is checked against the records payload and manifest only.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import stat
import tempfile
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Any, Mapping

from .retrieval_eval import (
    SCHEMA_VERSION as JUDGMENT_SCHEMA_VERSION,
    EvaluationFixture,
    IndexedCatalog,
    load_fixture,
    resolve_judgments,
)

MANIFEST_SCHEMA_VERSION = 1
RECORDS_SCHEMA_VERSION = 1
ANCHOR_SCHEMA_VERSION = 1
_PAYLOAD_NAMES = ("records.json", "judgments.jsonl", "anchors.jsonl")
_MANIFEST_FIELDS = {
    "schema_version",
    "snapshot_version",
    "schema_versions",
    "payload_sha256",
    "review_status",
    "review_date",
    "source_root",
    "source_provenance",
    "parser_configuration",
    "splitter_configuration",
    "counts",
}
_SOURCE_FIELDS = {
    "source_id",
    "relative_path",
    "sha256",
    "suffix",
    "byte_size",
    "duplicate_of",
    "selected_reader",
    "reader_attempts",
    "reader_fallback_used",
    "reader_granularity",
    "status",
}
_UNIT_FIELDS = {
    "unit_id",
    "source_id",
    "relative_path",
    "unit_ordinal",
    "locator",
    "text",
    "normalized_text",
}
_CHUNK_FIELDS = {
    "chunk_id",
    "source_id",
    "relative_path",
    "unit_id",
    "unit_ordinal",
    "chunk_ordinal",
    "locator",
    "text",
    "char_start",
    "char_end",
}
_ANCHOR_FIELDS = {
    "schema_version",
    "id",
    "query_id",
    "source_id",
    "source_sha256",
    "unit_id",
    "locator",
    "char_start",
    "char_end",
    "evidence_sha256",
}
_COUNT_FIELDS = {
    "source_paths",
    "documents",
    "source_units",
    "chunks",
    "queries",
    "anchors",
}
_TOPIC_CANDIDATE_FIELDS = {
    "candidate_id",
    "source_id",
    "relative_path",
    "unit_id",
    "text",
    "locator",
    "needs_review",
}
_QUALITY_ROW_FIELDS = {
    "empty_locators": {"relative_path", "source_id", "locator", "reason"},
    "unusable_locators": {"relative_path", "source_id", "locator", "reason"},
    "reader_diagnostics": {
        "relative_path",
        "source_id",
        "reader_used",
        "attempted_readers",
        "fallback_used",
        "granularity",
        "needs_review",
        "detail",
    },
    "extraction_failures": {
        "relative_path",
        "source_id",
        "error_type",
        "reason",
    },
    "chunk_mapping_issues": {
        "relative_path",
        "source_id",
        "unit_id",
        "locator",
        "reason",
        "error_type",
        "needs_review",
    },
    "pages": {
        "relative_path",
        "source_id",
        "total_pages",
        "extracted_pages",
        "empty_pages",
    },
    "sheets": {
        "relative_path",
        "source_id",
        "sheet_name",
        "extracted_rows",
        "blank_rows",
    },
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".xlsx"}


@dataclass(frozen=True)
class EvidenceAnchor:
    """One query-linked source span in normalized source-unit text."""

    id: str
    query_id: str
    source_id: str
    source_sha256: str
    unit_id: str
    locator: Mapping[str, Any]
    char_start: int
    char_end: int
    evidence_sha256: str


@dataclass(frozen=True)
class LocalSnapshot:
    """Validated snapshot inputs; nested record mappings are immutable."""

    root: Path
    records: Mapping[str, Any]
    sources: tuple[Mapping[str, Any], ...]
    canonical_sources: tuple[Mapping[str, Any], ...]
    selected_sources: tuple[Mapping[str, Any], ...]
    judgments: EvaluationFixture
    anchors: tuple[EvidenceAnchor, ...]
    fingerprint: str


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON object contains duplicate field {key!r}")
        result[key] = value
    return result


def _decode_json(payload: bytes, label: str) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing {sorted(missing)}")
        if extra:
            details.append(f"unexpected {sorted(extra)}")
        raise ValueError(f"{label} has invalid fields: {'; '.join(details)}")


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{label} must not have surrounding whitespace")
    return value


def _safe_relative_path(value: Any, label: str, *, repository: bool = False) -> str:
    path = _nonempty_string(value, label)
    if "\x00" in path:
        raise ValueError(f"{label} must not contain NUL")
    if "\\" in path:
        raise ValueError(f"{label} must not contain a backslash")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(
            f"{label} must be a safe {('repository-' if repository else '')}relative POSIX path"
        )
    parts = path.split("/")
    if any(part == ".." for part in parts):
        raise ValueError(f"{label} must not contain parent traversal")
    if any(part in {"", "."} for part in parts):
        raise ValueError(f"{label} must use normalized POSIX path components")
    if PurePosixPath(path).as_posix() != path:
        raise ValueError(f"{label} must use a normalized POSIX path")
    return path


def _valid_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(
            f"invalid SHA-256 digest for {label}; expected 64 lowercase hex characters"
        )
    return value


def _check_regular_path(path: Path, label: str, *, directory: bool = False) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise ValueError(f"Required snapshot {label} is missing") from error
    if stat.S_ISLNK(mode):
        raise ValueError(f"Snapshot {label} must not be a symlink")
    expected = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
    if not expected:
        kind = "directory" if directory else "regular file"
        raise ValueError(f"Snapshot {label} must be a {kind}")


def _read_checked_file(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError as error:
        raise ValueError(f"Required snapshot {label} is missing") from error
    except OSError as error:
        if getattr(error, "errno", None) == errno.ELOOP:
            raise ValueError(f"Snapshot {label} must not be a symlink") from error
        raise
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError(f"Snapshot {label} must be a regular file")
        return stream.read()


def _validate_manifest(value: Any, root: Path) -> dict[str, Any]:
    manifest = _require_object(value, "manifest.json")
    _require_exact_fields(manifest, _MANIFEST_FIELDS, "manifest.json")
    version = manifest.get("schema_version")
    if isinstance(version, bool) or version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported manifest schema_version {version!r}; expected {MANIFEST_SCHEMA_VERSION}"
        )

    snapshot_version = _nonempty_string(
        manifest.get("snapshot_version"), "snapshot_version"
    )
    if (
        _VERSION_RE.fullmatch(snapshot_version) is None
        or snapshot_version in {".", ".."}
        or snapshot_version != root.name
    ):
        raise ValueError(
            "snapshot_version must be a safe name matching the snapshot directory"
        )

    schema_versions = _require_object(
        manifest.get("schema_versions"), "schema_versions"
    )
    expected_versions = {
        "records": RECORDS_SCHEMA_VERSION,
        "judgments": JUDGMENT_SCHEMA_VERSION,
        "anchors": ANCHOR_SCHEMA_VERSION,
    }
    if schema_versions != expected_versions:
        raise ValueError(f"schema_versions must equal {expected_versions!r}")

    payload_hashes = _require_object(manifest.get("payload_sha256"), "payload_sha256")
    if set(payload_hashes) != set(_PAYLOAD_NAMES):
        raise ValueError(
            "payload_sha256 must contain exactly records.json, judgments.jsonl, and anchors.jsonl"
        )
    for name, digest in payload_hashes.items():
        _valid_digest(digest, f"payload_sha256[{name!r}]")

    review_status = manifest.get("review_status")
    if review_status not in {"approved", "draft"}:
        raise ValueError("review_status must be 'approved' or 'draft'")
    review_date = manifest.get("review_date")
    if review_status == "approved":
        if not isinstance(review_date, str):
            raise ValueError("approved snapshots require an ISO review_date")
        try:
            if date.fromisoformat(review_date).isoformat() != review_date:
                raise ValueError
        except ValueError as error:
            raise ValueError("approved snapshots require an ISO review_date") from error
    elif review_date is not None:
        raise ValueError("draft snapshots must have a null review_date")

    manifest["source_root"] = _safe_relative_path(
        manifest.get("source_root"), "source_root", repository=True
    )
    for field in ("parser_configuration", "splitter_configuration"):
        _require_object(manifest.get(field), field)

    counts = _require_object(manifest.get("counts"), "counts")
    _require_exact_fields(counts, _COUNT_FIELDS, "counts")
    for name, count in counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"counts.{name} must be a non-negative integer")

    provenance = manifest.get("source_provenance")
    if not isinstance(provenance, list):
        raise ValueError("source_provenance must be a list")
    for index, item in enumerate(provenance, 1):
        item = _require_object(item, f"source_provenance[{index}]")
        _require_exact_fields(
            item,
            {"source_id", "repository_path", "sha256"},
            f"source_provenance[{index}]",
        )
        _nonempty_string(item.get("source_id"), f"source_provenance[{index}].source_id")
        _nonempty_string(
            item.get("repository_path"),
            f"source_provenance[{index}].repository_path",
        )
        _nonempty_string(item.get("sha256"), f"source_provenance[{index}].sha256")
    return manifest


def _validate_records_shape(value: Any) -> dict[str, Any]:
    records = _require_object(value, "records.json")
    version = records.get("schema_version")
    if isinstance(version, bool) or version != RECORDS_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported records schema_version {version!r}; expected {RECORDS_SCHEMA_VERSION}"
        )
    for field in (
        "parser_configuration",
        "splitter_configuration",
        "quality",
    ):
        _require_object(records.get(field), f"records.{field}")
    for field in (
        "sources",
        "source_units",
        "chunks",
        "topic_candidates",
        "topic_review_source_ids",
        "excluded_inputs",
    ):
        if not isinstance(records.get(field), list):
            raise ValueError(f"records.{field} must be a list")
    return records


def _validate_sources(
    records: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    paths: set[str] = set()
    canonical_by_path: dict[str, dict[str, Any]] = {}
    canonical_by_id: dict[str, dict[str, Any]] = {}
    previous_path: str | None = None

    for index, raw in enumerate(records["sources"], 1):
        row = _require_object(raw, f"records.sources[{index}]")
        _require_exact_fields(row, _SOURCE_FIELDS, f"records.sources[{index}]")
        relative_path = _safe_relative_path(
            row.get("relative_path"), f"records.sources[{index}].relative_path"
        )
        if relative_path in paths:
            raise ValueError(f"duplicate source path {relative_path!r}")
        if previous_path is not None and relative_path < previous_path:
            raise ValueError("source records must be sorted by relative_path")
        previous_path = relative_path
        paths.add(relative_path)

        digest = _valid_digest(row.get("sha256"), f"source {relative_path!r} SHA-256")
        source_id = _valid_digest(
            row.get("source_id"), f"source {relative_path!r} source_id"
        )
        if source_id != digest:
            raise ValueError(
                f"source_id for {relative_path!r} must equal its SHA-256 digest"
            )
        suffix = row.get("suffix")
        actual_suffix = PurePosixPath(relative_path).suffix.lower()
        if suffix != actual_suffix or suffix not in _SUPPORTED_SUFFIXES:
            raise ValueError(f"source {relative_path!r} has an invalid suffix")
        size = row.get("byte_size")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError(f"source {relative_path!r} byte_size must be non-negative")
        if not isinstance(row.get("reader_attempts"), list) or not all(
            isinstance(item, str) for item in row["reader_attempts"]
        ):
            raise ValueError(
                f"source {relative_path!r} reader_attempts must be a string list"
            )
        if not isinstance(row.get("reader_fallback_used"), bool):
            raise ValueError(
                f"source {relative_path!r} reader_fallback_used must be boolean"
            )
        for field in ("selected_reader", "reader_granularity"):
            value = row.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(
                    f"source {relative_path!r} {field} must be a string or null"
                )

        duplicate_of = row.get("duplicate_of")
        status = row.get("status")
        if duplicate_of is None:
            if source_id in canonical_by_id:
                raise ValueError(f"duplicate canonical source ID {source_id!r}")
            if status not in {"parsed", "failed", "not_selected"}:
                raise ValueError(
                    f"canonical source {relative_path!r} has an invalid status"
                )
            canonical_by_path[relative_path] = row
            canonical_by_id[source_id] = row
        else:
            duplicate_of = _safe_relative_path(
                duplicate_of, f"source {relative_path!r} duplicate_of"
            )
            if status != "duplicate_bytes":
                raise ValueError(
                    f"duplicate source {relative_path!r} must have duplicate_bytes status"
                )
            row["duplicate_of"] = duplicate_of
        rows.append(row)

    if not rows:
        raise ValueError("records.sources must contain at least one source path")

    for row in rows:
        duplicate_of = row["duplicate_of"]
        if duplicate_of is None:
            continue
        canonical = canonical_by_path.get(duplicate_of)
        if canonical is None:
            raise ValueError(
                f"duplicate_of for {row['relative_path']!r} must point to the canonical source path"
            )
        if duplicate_of >= row["relative_path"]:
            raise ValueError(
                "duplicate source path must sort after its canonical source path"
            )
        if (
            row["source_id"] != canonical["source_id"]
            or row["sha256"] != canonical["sha256"]
            or row["byte_size"] != canonical["byte_size"]
        ):
            raise ValueError(
                f"duplicate source {row['relative_path']!r} has mismatched provenance"
            )

    return rows, list(canonical_by_path.values())


def _validate_locator(value: Any, label: str) -> dict[str, Any]:
    locator = _require_object(value, label)
    for key, item in locator.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} keys must be non-empty strings")
        if isinstance(item, (dict, list)) or item is None:
            raise ValueError(f"{label} values must be non-null JSON scalars")
        if not isinstance(item, (str, int, float, bool)):
            raise ValueError(f"{label} values must be JSON scalars")
    return locator


def _validate_units_and_chunks(
    records: dict[str, Any], canonical_sources: list[dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    canonical_by_id = {row["source_id"]: row for row in canonical_sources}
    units: dict[str, dict[str, Any]] = {}
    unit_ordinals: set[tuple[str, int]] = set()
    for index, raw in enumerate(records["source_units"], 1):
        unit = _require_object(raw, f"records.source_units[{index}]")
        _require_exact_fields(unit, _UNIT_FIELDS, f"records.source_units[{index}]")
        unit_id = _nonempty_string(unit.get("unit_id"), f"source unit {index} unit_id")
        if unit_id in units:
            raise ValueError(f"duplicate source unit ID {unit_id!r}")
        source_id = unit.get("source_id")
        source = canonical_by_id.get(source_id)
        if source is None:
            raise ValueError(
                f"source unit {unit_id!r} references unknown Source ID {source_id!r}"
            )
        if source["status"] != "parsed":
            raise ValueError(
                f"source unit {unit_id!r} references a source not parsed for indexing"
            )
        relative_path = _safe_relative_path(
            unit.get("relative_path"), f"source unit {unit_id!r} relative_path"
        )
        if relative_path != source["relative_path"]:
            raise ValueError(f"source unit path does not match source {source_id!r}")
        ordinal = unit.get("unit_ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise ValueError(
                f"source unit {unit_id!r} unit_ordinal must be non-negative"
            )
        if (source_id, ordinal) in unit_ordinals:
            raise ValueError(
                f"duplicate source unit ordinal for Source ID {source_id!r}"
            )
        unit_ordinals.add((source_id, ordinal))
        _validate_locator(unit.get("locator"), f"source unit {unit_id!r} locator")
        if not isinstance(unit.get("text"), str) or not isinstance(
            unit.get("normalized_text"), str
        ):
            raise ValueError(f"source unit {unit_id!r} text fields must be strings")
        units[unit_id] = unit

    chunks: dict[str, dict[str, Any]] = {}
    chunk_ordinals: set[tuple[str, int]] = set()
    for index, raw in enumerate(records["chunks"], 1):
        chunk = _require_object(raw, f"records.chunks[{index}]")
        _require_exact_fields(chunk, _CHUNK_FIELDS, f"records.chunks[{index}]")
        chunk_id = _nonempty_string(chunk.get("chunk_id"), f"chunk {index} chunk_id")
        if chunk_id in chunks:
            raise ValueError(f"duplicate chunk ID {chunk_id!r}")
        unit_id = chunk.get("unit_id")
        unit = units.get(unit_id)
        if unit is None:
            raise ValueError(
                f"chunk {chunk_id!r} references unknown source unit {unit_id!r}"
            )
        if chunk.get("source_id") != unit["source_id"]:
            raise ValueError(f"chunk {chunk_id!r} Source ID does not match source unit")
        if canonical_by_id[unit["source_id"]]["status"] != "parsed":
            raise ValueError(
                f"chunk {chunk_id!r} references a source not parsed for indexing"
            )
        relative_path = _safe_relative_path(
            chunk.get("relative_path"), f"chunk {chunk_id!r} relative_path"
        )
        if relative_path != unit["relative_path"]:
            raise ValueError(f"chunk {chunk_id!r} path does not match source unit")
        if chunk.get("unit_ordinal") != unit["unit_ordinal"]:
            raise ValueError(
                f"chunk {chunk_id!r} unit_ordinal does not match source unit"
            )
        if chunk.get("locator") != unit["locator"]:
            raise ValueError(f"chunk {chunk_id!r} locator does not match source unit")
        chunk_ordinal = chunk.get("chunk_ordinal")
        if (
            isinstance(chunk_ordinal, bool)
            or not isinstance(chunk_ordinal, int)
            or chunk_ordinal < 0
        ):
            raise ValueError(f"chunk {chunk_id!r} chunk_ordinal must be non-negative")
        ordinal_key = (unit_id, chunk_ordinal)
        if ordinal_key in chunk_ordinals:
            raise ValueError(f"duplicate chunk ordinal for source unit {unit_id!r}")
        chunk_ordinals.add(ordinal_key)
        start, end = chunk.get("char_start"), chunk.get("char_end")
        text = chunk.get("text")
        normalized_text = unit["normalized_text"]
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(normalized_text)
        ):
            raise ValueError(f"chunk {chunk_id!r} has an invalid source-unit span")
        if not isinstance(text, str) or text != normalized_text[start:end]:
            raise ValueError(
                f"chunk text does not match source unit span for {chunk_id!r}"
            )
        chunks[chunk_id] = chunk
    return units, chunks


def _mapping_contains(parent: Mapping[str, Any], child: Mapping[str, Any]) -> bool:
    return all(
        key in parent and type(parent[key]) is type(value) and parent[key] == value
        for key, value in child.items()
    )


def _validate_topic_records(
    records: dict[str, Any],
    canonical_sources: list[dict[str, Any]],
    units: dict[str, dict[str, Any]],
) -> None:
    canonical_by_id = {source["source_id"]: source for source in canonical_sources}
    topic_review_ids = records["topic_review_source_ids"]
    seen_review_ids: set[str] = set()
    for index, raw_source_id in enumerate(topic_review_ids, 1):
        source_id = _valid_digest(raw_source_id, f"topic_review_source_ids[{index}]")
        if source_id in seen_review_ids:
            raise ValueError(
                f"topic_review_source_ids contains duplicate Source ID {source_id!r}"
            )
        seen_review_ids.add(source_id)
        source = canonical_by_id.get(source_id)
        if source is None:
            raise ValueError(
                f"topic_review_source_ids contains unknown Source ID {source_id!r}"
            )
        if source["status"] == "not_selected":
            raise ValueError(
                f"topic_review_source_ids must name selected canonical sources; "
                f"{source_id!r} is not selected"
            )

    seen_candidate_ids: set[str] = set()
    for index, raw_candidate in enumerate(records["topic_candidates"], 1):
        candidate = _require_object(raw_candidate, f"topic_candidates[{index}]")
        _require_exact_fields(
            candidate, _TOPIC_CANDIDATE_FIELDS, f"topic_candidates[{index}]"
        )
        candidate_id = _nonempty_string(
            candidate.get("candidate_id"), f"topic_candidates[{index}].candidate_id"
        )
        if candidate_id in seen_candidate_ids:
            raise ValueError(f"topic_candidates contains duplicate ID {candidate_id!r}")
        seen_candidate_ids.add(candidate_id)
        source_id = _valid_digest(
            candidate.get("source_id"), f"topic candidate {candidate_id!r} source_id"
        )
        source = canonical_by_id.get(source_id)
        if source is None:
            raise ValueError(
                f"topic candidate {candidate_id!r} references unknown Source ID {source_id!r}"
            )
        if source["status"] == "not_selected":
            raise ValueError(
                f"topic candidate {candidate_id!r} references a source that was not selected"
            )
        unit_id = _nonempty_string(
            candidate.get("unit_id"), f"topic candidate {candidate_id!r} unit_id"
        )
        unit = units.get(unit_id)
        if unit is None:
            raise ValueError(
                f"topic candidate {candidate_id!r} references unknown source unit {unit_id!r}"
            )
        if unit["source_id"] != source_id:
            raise ValueError(
                f"topic candidate {candidate_id!r} Source ID does not match source unit"
            )
        relative_path = _safe_relative_path(
            candidate.get("relative_path"),
            f"topic candidate {candidate_id!r} relative_path",
        )
        if (
            relative_path != source["relative_path"]
            or relative_path != unit["relative_path"]
        ):
            raise ValueError(
                f"topic candidate {candidate_id!r} path does not match source unit"
            )
        locator = _validate_locator(
            candidate.get("locator"), f"topic candidate {candidate_id!r} locator"
        )
        if not _mapping_contains(locator, unit["locator"]):
            raise ValueError(
                f"topic candidate {candidate_id!r} locator does not match source unit"
            )
        _nonempty_string(
            candidate.get("text"), f"topic candidate {candidate_id!r} text"
        )
        if not isinstance(candidate.get("needs_review"), bool):
            raise ValueError(
                f"topic candidate {candidate_id!r} needs_review must be boolean"
            )


def _validate_quality_provenance(
    records: dict[str, Any],
    source_rows: list[dict[str, Any]],
    units: dict[str, dict[str, Any]],
) -> None:
    quality = records["quality"]
    _require_exact_fields(quality, set(_QUALITY_ROW_FIELDS), "records.quality")
    source_by_path = {source["relative_path"]: source for source in source_rows}
    for section, expected_fields in _QUALITY_ROW_FIELDS.items():
        entries = quality.get(section)
        if not isinstance(entries, list):
            raise ValueError(f"records.quality.{section} must be a list")
        for index, raw_entry in enumerate(entries, 1):
            label = f"quality.{section}[{index}]"
            entry = _require_object(raw_entry, label)
            _require_exact_fields(entry, expected_fields, label)
            relative_path = _safe_relative_path(
                entry.get("relative_path"), f"{label}.relative_path"
            )
            source_id = _valid_digest(entry.get("source_id"), f"{label}.source_id")
            source = source_by_path.get(relative_path)
            if (
                source is None
                or source["duplicate_of"] is not None
                or source["source_id"] != source_id
            ):
                raise ValueError(
                    f"{label} Source ID and path do not match a canonical source record"
                )
            if source["status"] == "not_selected":
                raise ValueError(f"{label} references a source that was not selected")
            if "locator" in entry:
                locator = _validate_locator(entry["locator"], f"{label}.locator")
                matching_units = [
                    unit
                    for unit in units.values()
                    if unit["source_id"] == source_id
                    and unit["relative_path"] == relative_path
                ]
                if not any(
                    _mapping_contains(locator, unit["locator"])
                    for unit in matching_units
                ):
                    raise ValueError(f"{label}.locator does not match a source unit")
            if "unit_id" in entry:
                unit_id = _nonempty_string(entry["unit_id"], f"{label}.unit_id")
                unit = units.get(unit_id)
                if (
                    unit is None
                    or unit["source_id"] != source_id
                    or unit["relative_path"] != relative_path
                ):
                    raise ValueError(
                        f"{label} source unit does not match source provenance"
                    )
                if not _mapping_contains(entry["locator"], unit["locator"]):
                    raise ValueError(f"{label}.locator does not match source unit")


def _validate_excluded_input_provenance(
    records: dict[str, Any], source_rows: list[dict[str, Any]]
) -> None:
    source_by_path = {source["relative_path"]: source for source in source_rows}
    canonical_by_path = {
        source["relative_path"]: source
        for source in source_rows
        if source["duplicate_of"] is None
    }
    for index, raw_entry in enumerate(records["excluded_inputs"], 1):
        label = f"excluded_inputs[{index}]"
        entry = _require_object(raw_entry, label)
        _require_exact_fields(
            entry,
            {"relative_path", "source_id", "reason", "duplicate_of"},
            label,
        )
        relative_path = _safe_relative_path(
            entry.get("relative_path"), f"{label}.relative_path"
        )
        reason = _nonempty_string(entry.get("reason"), f"{label}.reason")
        source_id = entry.get("source_id")
        duplicate_of = entry.get("duplicate_of")
        if source_id is None:
            if reason != "unsupported_suffix" or duplicate_of is not None:
                raise ValueError(
                    f"{label} without a source ID must be unsupported_suffix"
                )
            if relative_path in source_by_path:
                raise ValueError(f"{label} path already has a source record")
            continue

        source_id = _valid_digest(source_id, f"{label}.source_id")
        source = source_by_path.get(relative_path)
        if source is None or source["source_id"] != source_id:
            raise ValueError(f"{label} source path does not match source provenance")
        expected_duplicate_of = source["duplicate_of"]
        if duplicate_of is not None:
            duplicate_of = _safe_relative_path(duplicate_of, f"{label}.duplicate_of")
        if duplicate_of != expected_duplicate_of:
            raise ValueError(f"{label} duplicate_of does not match source provenance")
        canonical = (
            source
            if source["duplicate_of"] is None
            else canonical_by_path.get(source["duplicate_of"])
        )
        if canonical is None:
            raise ValueError(f"{label} does not resolve to canonical source provenance")
        expected_reason = (
            "not_selected"
            if canonical["status"] == "not_selected"
            else "duplicate_bytes" if source["duplicate_of"] is not None else None
        )
        if expected_reason is None or reason != expected_reason:
            raise ValueError(
                f"{label} reason does not match source selection provenance"
            )


def _load_fixture_from_verified_bytes(
    payload: bytes, source_path: Path
) -> EvaluationFixture:
    # The existing loader owns the judgments schema. It reads a temporary copy
    # of bytes already verified above, never the original snapshot file again.
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("judgments.jsonl must be valid UTF-8 JSONL") from error
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            json.loads(line, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(
                f"judgments.jsonl line {line_number} is invalid JSON"
            ) from error
    with tempfile.TemporaryDirectory(prefix="kotaemon-snapshot-") as temporary_dir:
        temporary_path = Path(temporary_dir) / "judgments.jsonl"
        temporary_path.write_bytes(payload)
        fixture = load_fixture(temporary_path)
    immutable_cases = tuple(
        replace(
            case,
            filters=(
                None if case.filters is None else MappingProxyType(dict(case.filters))
            ),
        )
        for case in fixture.cases
    )
    return replace(fixture, cases=immutable_cases, source_path=str(source_path))


def _validate_judgments(
    fixture: EvaluationFixture, canonical_sources: list[dict[str, Any]]
) -> None:
    if any(case.judgment_level != "source" for case in fixture.cases):
        raise ValueError("local snapshots require source-level judgments")
    source_ids = {row["source_id"] for row in canonical_sources}
    catalog = IndexedCatalog(source_ids=source_ids, chunk_to_source={})
    resolve_judgments(fixture, catalog)
    for case in fixture.cases:
        relevant = set(case.relevant_ids)
        disallowed = set(case.disallowed_source_ids or ())
        allowed = (
            None if case.allowed_source_ids is None else set(case.allowed_source_ids)
        )
        if relevant & disallowed:
            raise ValueError(
                f"Query {case.case_id!r} has a source ID both relevant and disallowed"
            )
        if allowed is not None and allowed & disallowed:
            raise ValueError(
                f"Query {case.case_id!r} has a source ID both allowed and disallowed"
            )
        if allowed is not None and not relevant <= allowed:
            raise ValueError(
                f"Query {case.case_id!r} has a relevant source ID not in allowed_source_ids"
            )


def _parse_anchors(payload: bytes) -> list[dict[str, Any]]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("anchors.jsonl must be valid UTF-8 JSONL") from error
    anchors = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        anchor = _require_object(
            _decode_json(line.encode("utf-8"), f"anchors.jsonl line {line_number}"),
            f"anchors.jsonl line {line_number}",
        )
        _require_exact_fields(
            anchor, _ANCHOR_FIELDS, f"anchors.jsonl line {line_number}"
        )
        version = anchor.get("schema_version")
        if isinstance(version, bool) or version != ANCHOR_SCHEMA_VERSION:
            raise ValueError(
                f"Anchor line {line_number} has unsupported schema_version"
            )
        anchors.append(anchor)
    return anchors


def _validate_anchors(
    anchors: list[dict[str, Any]],
    fixture: EvaluationFixture,
    canonical_sources: list[dict[str, Any]],
    units: dict[str, dict[str, Any]],
) -> tuple[EvidenceAnchor, ...]:
    source_by_id = {row["source_id"]: row for row in canonical_sources}
    case_by_id = {case.case_id: case for case in fixture.cases}
    relevant_pairs = {
        (case.case_id, source_id)
        for case in fixture.cases
        for source_id in case.relevant_ids
    }
    seen_ids: set[str] = set()
    covered_pairs: set[tuple[str, str]] = set()
    validated: list[EvidenceAnchor] = []

    for index, row in enumerate(anchors, 1):
        anchor_id = _nonempty_string(row.get("id"), f"anchor {index} id")
        if anchor_id in seen_ids:
            raise ValueError(f"duplicate anchor ID {anchor_id!r}")
        seen_ids.add(anchor_id)
        query_id = _nonempty_string(
            row.get("query_id"), f"anchor {anchor_id!r} query_id"
        )
        case = case_by_id.get(query_id)
        if case is None:
            raise ValueError(f"Unknown query ID {query_id!r} in anchor {anchor_id!r}")
        source_id = _valid_digest(
            row.get("source_id"), f"anchor {anchor_id!r} source_id"
        )
        source = source_by_id.get(source_id)
        if source is None:
            raise ValueError(f"Unknown Source ID {source_id!r} in anchor {anchor_id!r}")
        if source_id not in case.relevant_ids:
            raise ValueError(
                f"Anchor {anchor_id!r} source {source_id!r} is not relevant to query {query_id!r}"
            )
        source_sha256 = _valid_digest(
            row.get("source_sha256"), f"anchor {anchor_id!r} source_sha256"
        )
        if source_sha256 != source["sha256"]:
            raise ValueError(f"Anchor {anchor_id!r} source SHA-256 mismatch")
        unit_id = _nonempty_string(row.get("unit_id"), f"anchor {anchor_id!r} unit_id")
        unit = units.get(unit_id)
        if unit is None:
            raise ValueError(
                f"Unknown source unit ID {unit_id!r} in anchor {anchor_id!r}"
            )
        if unit["source_id"] != source_id:
            raise ValueError(f"Anchor {anchor_id!r} source does not match source unit")
        locator = _validate_locator(row.get("locator"), f"anchor {anchor_id!r} locator")
        if locator != unit["locator"]:
            raise ValueError(f"Anchor {anchor_id!r} locator does not match source unit")
        start, end = row.get("char_start"), row.get("char_end")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
        ):
            raise ValueError(
                f"Anchor {anchor_id!r} must have a non-empty evidence span"
            )
        normalized_text = unit["normalized_text"]
        if end > len(normalized_text):
            raise ValueError(
                f"Anchor {anchor_id!r} span is outside normalized source unit"
            )
        evidence_sha256 = _valid_digest(
            row.get("evidence_sha256"), f"anchor {anchor_id!r} evidence_sha256"
        )
        actual_evidence_hash = hashlib.sha256(
            normalized_text[start:end].encode("utf-8")
        ).hexdigest()
        if evidence_sha256 != actual_evidence_hash:
            raise ValueError(f"Anchor {anchor_id!r} evidence SHA-256 mismatch")
        covered_pairs.add((query_id, source_id))
        validated.append(
            EvidenceAnchor(
                id=anchor_id,
                query_id=query_id,
                source_id=source_id,
                source_sha256=source_sha256,
                unit_id=unit_id,
                locator=MappingProxyType(dict(locator)),
                char_start=start,
                char_end=end,
                evidence_sha256=evidence_sha256,
            )
        )

    missing_pairs = sorted(relevant_pairs - covered_pairs)
    if missing_pairs:
        query_id, source_id = missing_pairs[0]
        raise ValueError(
            f"Snapshot is missing evidence anchor for relevant query/source pair "
            f"({query_id!r}, {source_id!r})"
        )
    return tuple(validated)


def _validate_manifest_against_payloads(
    manifest: dict[str, Any],
    records: dict[str, Any],
    fixture: EvaluationFixture,
    anchors: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    canonical_sources: list[dict[str, Any]],
) -> None:
    if manifest["parser_configuration"] != records["parser_configuration"]:
        raise ValueError("manifest parser_configuration does not match records.json")
    if manifest["splitter_configuration"] != records["splitter_configuration"]:
        raise ValueError("manifest splitter_configuration does not match records.json")
    source_root = manifest["source_root"]
    provenance = manifest["source_provenance"]
    if len(provenance) != len(source_rows):
        raise ValueError(
            "source_provenance must match every source path in records.json"
        )
    for index, (item, source) in enumerate(zip(provenance, source_rows), 1):
        expected_repository_path = f"{source_root}/{source['relative_path']}"
        item_path = _safe_relative_path(
            item["repository_path"],
            f"repository-relative source path at source_provenance[{index}]",
            repository=True,
        )
        item_digest = _valid_digest(
            item["sha256"], f"source_provenance[{index}].sha256"
        )
        if (
            item["source_id"] != source["source_id"]
            or item["sha256"] != source["sha256"]
        ):
            raise ValueError(
                f"source_provenance[{index}] identity does not match records.json"
            )
        if item_digest != source["sha256"] or item_path != expected_repository_path:
            raise ValueError(
                f"source_provenance[{index}] repository-relative source path does not map to source_root"
            )
    counts = manifest["counts"]
    indexed_source_ids = {chunk["source_id"] for chunk in records["chunks"]}
    expected_counts = {
        "source_paths": len(source_rows),
        "documents": sum(
            row["status"] == "parsed" and row["source_id"] in indexed_source_ids
            for row in canonical_sources
        ),
        "source_units": len(records["source_units"]),
        "chunks": len(records["chunks"]),
        "queries": len(fixture.cases),
        "anchors": len(anchors),
    }
    for name, expected in expected_counts.items():
        if counts[name] != expected:
            label = "chunk" if name == "chunks" else name.removesuffix("s")
            raise ValueError(f"manifest {label} count does not match payloads")


def load_local_snapshot(path: Path, *, require_reviewed: bool = True) -> LocalSnapshot:
    """Load and validate one self-contained local snapshot directory.

    The three payload files are read exactly once and their exact bytes are
    checked against the manifest before any payload is parsed. Source files
    named by provenance are intentionally never opened.
    """
    if not isinstance(require_reviewed, bool):
        raise TypeError("require_reviewed must be a boolean")
    root = Path(path)
    _check_regular_path(root, "root", directory=True)
    manifest_path = root / "manifest.json"
    _check_regular_path(manifest_path, "manifest.json")
    for name in _PAYLOAD_NAMES:
        _check_regular_path(root / name, name)

    manifest_bytes = _read_checked_file(manifest_path, "manifest.json")
    manifest = _validate_manifest(_decode_json(manifest_bytes, "manifest.json"), root)
    if require_reviewed and manifest["review_status"] != "approved":
        raise ValueError("Local snapshot must have review_status='approved'")

    payloads: dict[str, bytes] = {}
    for name in _PAYLOAD_NAMES:
        payload = _read_checked_file(root / name, name)
        payloads[name] = payload
        actual = hashlib.sha256(payload).hexdigest()
        if actual != manifest["payload_sha256"][name]:
            raise ValueError(f"{name} payload hash mismatch")

    records = _validate_records_shape(
        _decode_json(payloads["records.json"], "records.json")
    )
    fixture = _load_fixture_from_verified_bytes(
        payloads["judgments.jsonl"], root / "judgments.jsonl"
    )
    if fixture.schema_version != manifest["schema_versions"]["judgments"]:
        raise ValueError(
            "Judgment schema_version does not match manifest schema_versions"
        )
    if records["schema_version"] != manifest["schema_versions"]["records"]:
        raise ValueError(
            "Records schema_version does not match manifest schema_versions"
        )
    anchors = _parse_anchors(payloads["anchors.jsonl"])

    source_rows, canonical_sources = _validate_sources(records)
    units, chunks = _validate_units_and_chunks(records, canonical_sources)
    _validate_topic_records(records, canonical_sources, units)
    _validate_quality_provenance(records, source_rows, units)
    _validate_excluded_input_provenance(records, source_rows)
    indexed_source_ids = {chunk["source_id"] for chunk in chunks.values()}
    selected_sources = [
        row
        for row in canonical_sources
        if row["status"] == "parsed" and row["source_id"] in indexed_source_ids
    ]
    _validate_judgments(fixture, selected_sources)
    _validate_manifest_against_payloads(
        manifest, records, fixture, anchors, source_rows, canonical_sources
    )
    validated_anchors = _validate_anchors(anchors, fixture, selected_sources, units)

    frozen_records = _freeze(records)
    frozen_sources = tuple(_freeze(row) for row in source_rows)
    frozen_canonical_sources = tuple(_freeze(row) for row in canonical_sources)
    frozen_selected_sources = tuple(_freeze(row) for row in selected_sources)
    return LocalSnapshot(
        root=root,
        records=frozen_records,
        sources=frozen_sources,
        canonical_sources=frozen_canonical_sources,
        selected_sources=frozen_selected_sources,
        judgments=fixture,
        anchors=validated_anchors,
        fingerprint=hashlib.sha256(manifest_bytes).hexdigest(),
    )
