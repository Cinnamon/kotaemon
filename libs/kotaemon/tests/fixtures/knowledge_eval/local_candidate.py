"""Build and validate a local v2 knowledge-evaluation candidate.

Only snapshot metadata and normalized source units are read. The builder never
opens source documents and keeps source-derived candidate files outside Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any


_SOURCE_COUNT = 22
_V1_QUERY_COUNT = 26
_ADDITION_COUNT = 54
_QUERY_TYPES = {
    "direct_lookup": 16,
    "procedure_condition": 14,
    "comparison_synthesis": 12,
    "exception_scope": 8,
    "multi_hop": 4,
}
_TOPICS = {"Climate", "LLM", "Rice", "Environmental-health"}
_ADDITION_FIELDS = {
    "id",
    "query",
    "topic",
    "query_type",
    "relevant_ids",
    "scope_source_ids",
    "anchors",
}
_ADDITION_ANCHOR_FIELDS = {"source_id", "unit_id", "char_start", "char_end"}
_METADATA_FIELDS = {"query_id", "topic", "query_type"}
_OUTPUT_METADATA_FIELDS = {
    "query_id",
    "topic",
    "query_type",
    "relevant_source_count",
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
_V1_FILES = ("records.json", "judgments.jsonl", "anchors.jsonl")
_PAYLOAD_FILES = (
    "records.json",
    "judgments.jsonl",
    "anchors.jsonl",
    "question_metadata.jsonl",
)
_OUTPUT_FILES = (*_PAYLOAD_FILES, "manifest.json")
_DIGEST_RE = re.compile(r"[0-9a-f]{64}\Z")


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _manifest_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON object contains a duplicate field")
        result[key] = value
    return result


def _decode_json(payload: bytes, label: str) -> Any:
    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=_object_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} must be valid UTF-8 JSON") from error


def _read_jsonl(path: Path, label: str) -> tuple[list[dict[str, Any]], bytes]:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Could not read {label}") from error
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} must be valid UTF-8 JSONL") from error
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line, object_pairs_hook=_object_pairs)
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"{label} line {line_number} must be a JSON object") from error
        if not isinstance(row, dict):
            raise ValueError(f"{label} line {line_number} must be a JSON object (JSONL)")
        rows.append(row)
    return rows, payload


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _require_fields(row: dict[str, Any], fields: set[str], label: str) -> None:
    if set(row) != fields:
        raise ValueError(f"{label} must contain exactly the required fields")


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{label} must be a non-empty relative POSIX path")
    if "\x00" in value or "\\" in value or value.startswith("/"):
        raise ValueError(f"{label} must be a safe relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError(f"{label} must be a normalized relative POSIX path")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{label} must not contain dot or parent components")
    if re.match(r"^[A-Za-z]:", value):
        raise ValueError(f"{label} must not be a drive-qualified path")
    return value


def _id_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty IDs")
    if not allow_empty and not value:
        raise ValueError(f"{label} must not be empty")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} contains duplicate IDs")
    return value


def _normalized_prompt(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split()).casefold()


def _validate_topic_and_type(row: dict[str, Any], label: str) -> None:
    topic = row.get("topic")
    if not isinstance(topic, str) or topic not in _TOPICS:
        raise ValueError(f"{label} has an unsupported topic")
    query_type = row.get("query_type")
    if not isinstance(query_type, str) or query_type not in _QUERY_TYPES:
        raise ValueError(f"{label} has an unsupported query_type")


def _load_v1(v1_dir: Path) -> dict[str, Any]:
    raw_files: dict[str, bytes] = {}
    for name in (*_V1_FILES, "manifest.json"):
        path = v1_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"v1 {name} is missing or not a regular file")
        try:
            raw_files[name] = path.read_bytes()
        except OSError as error:
            raise ValueError(f"Could not read v1 {name}") from error

    records = _require_object(_decode_json(raw_files["records.json"], "v1 records.json"), "v1 records.json")
    manifest = _require_object(_decode_json(raw_files["manifest.json"], "v1 manifest.json"), "v1 manifest.json")
    if manifest.get("snapshot_version") != "v1":
        raise ValueError("v1 manifest snapshot_version must be 'v1'")
    if manifest.get("review_status") != "approved":
        raise ValueError("v1 manifest must have review_status='approved'")
    source_root = _safe_relative_path(
        manifest.get("source_root"), "v1 manifest source_root"
    )
    declared_hashes = manifest.get("payload_sha256")
    if not isinstance(declared_hashes, dict) or set(declared_hashes) != set(_V1_FILES):
        raise ValueError("v1 manifest must hash exactly records.json, judgments.jsonl, and anchors.jsonl")
    for name in _V1_FILES:
        if declared_hashes[name] != _sha256(raw_files[name]):
            raise ValueError(f"v1 {name} payload hash mismatch")

    raw_sources = records.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("v1 records.json sources must be a list")
    source_by_id: dict[str, dict[str, Any]] = {}
    source_order: list[str] = []
    for index, raw_source in enumerate(raw_sources, 1):
        source = _require_object(raw_source, f"v1 source row {index}")
        source_id = _digest(source.get("source_id"), f"v1 source row {index} source_id")
        source_sha256 = _digest(source.get("sha256"), f"v1 source row {index} sha256")
        if source_id != source_sha256:
            raise ValueError(f"v1 source row {index} source hash does not match source_id")
        if source.get("duplicate_of") is not None:
            continue
        if source_id in source_by_id:
            raise ValueError("v1 source set contains a duplicate canonical source hash")
        if source.get("status") != "parsed":
            raise ValueError("v1 source set contains a non-indexable source")
        source_by_id[source_id] = source
        source_order.append(source_id)
    if len(source_by_id) != _SOURCE_COUNT:
        raise ValueError(f"v1 must contain exactly {_SOURCE_COUNT} canonical source hashes")

    raw_units = records.get("source_units")
    if not isinstance(raw_units, list):
        raise ValueError("v1 records.json source_units must be a list")
    units_by_id: dict[str, dict[str, Any]] = {}
    for index, raw_unit in enumerate(raw_units, 1):
        unit = _require_object(raw_unit, f"v1 source unit {index}")
        unit_id = _nonempty_string(unit.get("unit_id"), f"v1 source unit {index} unit_id")
        source_id = unit.get("source_id")
        normalized_text = unit.get("normalized_text")
        locator = unit.get("locator")
        if source_id not in source_by_id:
            raise ValueError(f"v1 source unit {unit_id!r} references an unknown source")
        if not isinstance(normalized_text, str):
            raise ValueError(f"v1 source unit {unit_id!r} normalized_text must be a string")
        if not isinstance(locator, dict):
            raise ValueError(f"v1 source unit {unit_id!r} locator must be an object")
        if unit_id in units_by_id:
            raise ValueError(f"v1 source unit {unit_id!r} is duplicated")
        units_by_id[unit_id] = unit

    chunks = records.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError("v1 records.json chunks must be a list")
    chunk_sources: set[str] = set()
    for index, raw_chunk in enumerate(chunks, 1):
        chunk = _require_object(raw_chunk, f"v1 chunk {index}")
        source_id = chunk.get("source_id")
        unit = units_by_id.get(chunk.get("unit_id"))
        if source_id not in source_by_id or unit is None or unit.get("source_id") != source_id:
            raise ValueError(f"v1 chunk {index} has an invalid source-unit mapping")
        normalized_text = unit["normalized_text"]
        start, end = chunk.get("char_start"), chunk.get("char_end")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(normalized_text)
            or chunk.get("text") != normalized_text[start:end]
        ):
            raise ValueError(f"v1 chunk {index} has an invalid normalized-unit span")
        chunk_sources.add(source_id)
    if chunk_sources != set(source_by_id):
        raise ValueError("v1 source hash set does not match the indexable chunk source set")

    v1_judgments, _ = _read_jsonl(v1_dir / "judgments.jsonl", "v1 judgments.jsonl")
    expected_v1_ids = [f"q-{index:03d}" for index in range(1, _V1_QUERY_COUNT + 1)]
    if len(v1_judgments) != _V1_QUERY_COUNT:
        raise ValueError(f"v1 must contain exactly {_V1_QUERY_COUNT} judgments")
    query_by_id: dict[str, dict[str, Any]] = {}
    prompt_keys: set[str] = set()
    relevant_pairs: set[tuple[str, str]] = set()
    for index, row in enumerate(v1_judgments, 1):
        query_id = _nonempty_string(row.get("id"), f"v1 judgment {index} id")
        if query_id != expected_v1_ids[index - 1]:
            raise ValueError("v1 judgment IDs must be q-001 through q-026 in order")
        query = _nonempty_string(row.get("query"), f"v1 judgment {query_id} query")
        prompt_key = _normalized_prompt(query)
        if prompt_key in prompt_keys:
            raise ValueError(f"duplicate normalized prompt in v1 judgment {query_id}")
        prompt_keys.add(prompt_key)
        if row.get("judgment_level") != "source":
            raise ValueError(f"v1 judgment {query_id} must be source-level")
        relevant_ids = _id_list(row.get("relevant_ids"), f"v1 judgment {query_id} relevant_ids")
        if any(source_id not in source_by_id for source_id in relevant_ids):
            raise ValueError(f"v1 judgment {query_id} references an unknown source")
        query_by_id[query_id] = row
        relevant_pairs.update((query_id, source_id) for source_id in relevant_ids)

    anchors, _ = _read_jsonl(v1_dir / "anchors.jsonl", "v1 anchors.jsonl")
    seen_anchor_ids: set[str] = set()
    covered_pairs: set[tuple[str, str]] = set()
    for index, row in enumerate(anchors, 1):
        _require_fields(row, _ANCHOR_FIELDS, f"v1 anchor {index}")
        if row.get("schema_version") != 1 or isinstance(row.get("schema_version"), bool):
            raise ValueError(f"v1 anchor {index} has an unsupported schema version")
        anchor_id = _nonempty_string(row.get("id"), f"v1 anchor {index} id")
        if anchor_id in seen_anchor_ids:
            raise ValueError(f"v1 anchor {anchor_id!r} is duplicated")
        seen_anchor_ids.add(anchor_id)
        query_id = row.get("query_id")
        source_id = row.get("source_id")
        pair = (query_id, source_id)
        if query_id not in query_by_id or pair not in relevant_pairs:
            raise ValueError(f"v1 anchor {anchor_id!r} is not linked to a relevant query/source pair")
        source_sha256 = _digest(row.get("source_sha256"), f"v1 anchor {anchor_id!r} source_sha256")
        if source_id not in source_by_id or source_sha256 != source_by_id[source_id]["sha256"]:
            raise ValueError(f"v1 anchor {anchor_id!r} source SHA-256 mismatch")
        unit_id = row.get("unit_id")
        unit = units_by_id.get(unit_id)
        if unit is None or unit.get("source_id") != source_id:
            raise ValueError(f"v1 anchor {anchor_id!r} has an invalid source unit")
        if row.get("locator") != unit["locator"]:
            raise ValueError(f"v1 anchor {anchor_id!r} locator mismatch")
        start, end = row.get("char_start"), row.get("char_end")
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
            raise ValueError(f"v1 anchor {anchor_id!r} has an invalid evidence offset")
        evidence_sha256 = _digest(row.get("evidence_sha256"), f"v1 anchor {anchor_id!r} evidence_sha256")
        if evidence_sha256 != _sha256(normalized_text[start:end].encode("utf-8")):
            raise ValueError(f"v1 anchor {anchor_id!r} evidence SHA-256 mismatch")
        covered_pairs.add(pair)
    if covered_pairs != relevant_pairs:
        raise ValueError("v1 is missing an anchor for a relevant query/source pair")

    return {
        "raw_files": raw_files,
        "records": records,
        "source_ids": source_order,
        "source_by_id": source_by_id,
        "units_by_id": units_by_id,
        "v1_judgments": v1_judgments,
        "v1_anchors": anchors,
        "query_by_id": query_by_id,
        "prompt_keys": prompt_keys,
        "source_root": source_root,
        "manifest_sha256": _sha256(raw_files["manifest.json"]),
    }


def _load_legacy_metadata(path: Path) -> dict[str, dict[str, Any]]:
    rows, _ = _read_jsonl(path, "legacy metadata")
    expected_ids = [f"q-{index:03d}" for index in range(1, _V1_QUERY_COUNT + 1)]
    if len(rows) != _V1_QUERY_COUNT:
        raise ValueError(f"legacy metadata must contain exactly {_V1_QUERY_COUNT} rows")
    by_id: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        _require_fields(row, _METADATA_FIELDS, f"legacy metadata row {index}")
        query_id = _nonempty_string(row.get("query_id"), f"legacy metadata row {index} query_id")
        if query_id in by_id:
            raise ValueError(f"legacy metadata contains duplicate query ID {query_id!r}")
        _validate_topic_and_type(row, f"legacy metadata query {query_id}")
        by_id[query_id] = row
    if set(by_id) != set(expected_ids):
        raise ValueError("legacy metadata IDs must contain each v1 query ID q-001 through q-026 exactly once")
    return by_id


def _prepare_candidate(
    v1_dir: Path,
    additions_path: Path,
    legacy_metadata_path: Path,
) -> tuple[dict[str, bytes], dict[str, Any], dict[str, int], bytes, bytes]:
    parent = _load_v1(Path(v1_dir))
    metadata_by_id = _load_legacy_metadata(Path(legacy_metadata_path))
    additions, _ = _read_jsonl(Path(additions_path), "additions")
    if len(additions) != _ADDITION_COUNT:
        raise ValueError(f"additions must contain exactly {_ADDITION_COUNT} rows")

    all_query_ids = [f"q-{index:03d}" for index in range(1, _V1_QUERY_COUNT + _ADDITION_COUNT + 1)]
    expected_addition_ids = all_query_ids[_V1_QUERY_COUNT:]
    known_sources = set(parent["source_ids"])
    prompt_keys = set(parent["prompt_keys"])
    type_counts = {query_type: 0 for query_type in _QUERY_TYPES}
    multi_source_count = 0
    new_judgments: list[dict[str, Any]] = []
    new_anchors: list[dict[str, Any]] = []
    new_metadata: list[dict[str, Any]] = []
    anchor_ids = {row["id"] for row in parent["v1_anchors"]}

    for index, row in enumerate(additions, 1):
        _require_fields(row, _ADDITION_FIELDS, f"addition row {index}")
        query_id = _nonempty_string(row.get("id"), f"addition row {index} id")
        if query_id != expected_addition_ids[index - 1]:
            raise ValueError("addition IDs must be q-027 through q-080 in order")
        query = _nonempty_string(row.get("query"), f"addition {query_id} query")
        prompt_key = _normalized_prompt(query)
        if prompt_key in prompt_keys:
            raise ValueError(f"duplicate normalized prompt for query {query_id}")
        prompt_keys.add(prompt_key)
        _validate_topic_and_type(row, f"addition {query_id}")
        query_type = row["query_type"]
        type_counts[query_type] += 1

        relevant_ids = _id_list(row.get("relevant_ids"), f"addition {query_id} relevant_ids")
        scope_ids = _id_list(row.get("scope_source_ids"), f"addition {query_id} scope_source_ids")
        unknown = (set(relevant_ids) | set(scope_ids)) - known_sources
        if unknown:
            raise ValueError(f"addition {query_id} references an unknown source ID")
        if not set(relevant_ids) <= set(scope_ids):
            raise ValueError(f"addition {query_id} has a relevant source outside its declared scope")
        if len(relevant_ids) >= 2:
            multi_source_count += 1

        raw_anchors = row.get("anchors")
        if not isinstance(raw_anchors, list):
            raise ValueError(f"addition {query_id} anchors must be a list")
        covered: set[str] = set()
        allowed_anchors: list[dict[str, Any]] = []
        for anchor_index, raw_anchor in enumerate(raw_anchors, 1):
            anchor = _require_object(raw_anchor, f"addition {query_id} anchor {anchor_index}")
            _require_fields(anchor, _ADDITION_ANCHOR_FIELDS, f"addition {query_id} anchor {anchor_index}")
            source_id = _digest(anchor.get("source_id"), f"addition {query_id} anchor {anchor_index} source_id")
            if source_id not in known_sources:
                raise ValueError(f"addition {query_id} anchor references an unknown source ID")
            if source_id not in relevant_ids:
                raise ValueError(f"addition {query_id} anchor source is not relevant to the query")
            unit_id = _nonempty_string(anchor.get("unit_id"), f"addition {query_id} anchor {anchor_index} unit_id")
            unit = parent["units_by_id"].get(unit_id)
            if unit is None or unit.get("source_id") != source_id:
                raise ValueError(f"addition {query_id} anchor source does not match its source unit")
            start, end = anchor.get("char_start"), anchor.get("char_end")
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
                raise ValueError(f"addition {query_id} anchor has an invalid evidence offset")
            allowed_anchors.append(
                {
                    "source_id": source_id,
                    "unit_id": unit_id,
                    "char_start": start,
                    "char_end": end,
                    "unit": unit,
                }
            )
            covered.add(source_id)
        if not set(relevant_ids) <= covered:
            raise ValueError(f"addition {query_id} is missing an anchor for a relevant query/source pair")

        scope_set = set(scope_ids)
        disallowed_ids = [source_id for source_id in parent["source_ids"] if source_id not in scope_set]
        new_judgments.append(
            {
                "schema_version": 1,
                "id": query_id,
                "query": query,
                "judgment_level": "source",
                "relevant_ids": relevant_ids,
                "disallowed_source_ids": disallowed_ids,
                "allowed_source_ids": scope_ids,
            }
        )
        for anchor_index, anchor in enumerate(allowed_anchors, 1):
            anchor_id = f"anchor-v2-{query_id}-{anchor_index:02d}"
            if anchor_id in anchor_ids:
                raise ValueError(f"duplicate anchor ID {anchor_id!r}")
            anchor_ids.add(anchor_id)
            unit = anchor["unit"]
            start, end = anchor["char_start"], anchor["char_end"]
            new_anchors.append(
                {
                    "schema_version": 1,
                    "id": anchor_id,
                    "query_id": query_id,
                    "source_id": anchor["source_id"],
                    "source_sha256": parent["source_by_id"][anchor["source_id"]]["sha256"],
                    "unit_id": anchor["unit_id"],
                    "locator": unit["locator"],
                    "char_start": start,
                    "char_end": end,
                    "evidence_sha256": _sha256(unit["normalized_text"][start:end].encode("utf-8")),
                }
            )
        new_metadata.append(
            {
                "query_id": query_id,
                "topic": row["topic"],
                "query_type": query_type,
                "relevant_source_count": len(relevant_ids),
            }
        )

    if type_counts != _QUERY_TYPES:
        raise ValueError(f"addition query_type quotas do not match the required counts: {type_counts}")
    if multi_source_count < 16:
        raise ValueError("additions must include at least 16 multi-source questions")

    old_metadata = [
        {
            "query_id": row["id"],
            "topic": metadata_by_id[row["id"]]["topic"],
            "query_type": metadata_by_id[row["id"]]["query_type"],
            "relevant_source_count": len(row["relevant_ids"]),
        }
        for row in parent["v1_judgments"]
    ]
    payloads: dict[str, bytes] = {
        "records.json": parent["raw_files"]["records.json"],
        "judgments.jsonl": _append_jsonl(parent["raw_files"]["judgments.jsonl"], new_judgments),
        "anchors.jsonl": _append_jsonl(parent["raw_files"]["anchors.jsonl"], new_anchors),
        "question_metadata.jsonl": b"".join(_json_bytes(row) for row in [*old_metadata, *new_metadata]),
    }
    counts = {"documents": _SOURCE_COUNT, "queries": len(all_query_ids), "new_queries": _ADDITION_COUNT}
    manifest = {
        "snapshot_version": "v2-draft",
        "review_status": "draft",
        "review_date": None,
        "source_root": parent["source_root"],
        "parent_manifest_sha256": parent["manifest_sha256"],
        "counts": counts,
        "payload_sha256": {name: _sha256(payloads[name]) for name in _PAYLOAD_FILES},
    }
    return payloads, manifest, counts, parent["raw_files"]["judgments.jsonl"], parent["raw_files"]["anchors.jsonl"]


def _append_jsonl(prefix: bytes, rows: list[dict[str, Any]]) -> bytes:
    separator = b"" if not prefix or prefix.endswith(b"\n") else b"\n"
    return prefix + separator + b"".join(_json_bytes(row) for row in rows)


def _ensure_output_not_v1(v1_dir: Path, output_dir: Path) -> None:
    try:
        parent = v1_dir.resolve(strict=True)
        output = output_dir.resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ValueError("could not resolve candidate output and v1 parent paths") from error
    if output == parent:
        raise ValueError("candidate output must not resolve to the v1 parent directory")


def _check_output_targets(output_dir: Path) -> None:
    if output_dir.is_symlink():
        raise ValueError("candidate output directory must not be a symlink")
    if not output_dir.exists():
        return
    if not output_dir.is_dir():
        raise ValueError("candidate output must be a regular directory")
    for name in _OUTPUT_FILES:
        target = output_dir / name
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise ValueError(f"candidate output target {name} must not be a symlink")
        if not stat.S_ISREG(mode):
            raise ValueError(f"candidate output target {name} must be a regular file or absent")


def _write_output_atomically(output_dir: Path, files: dict[str, bytes]) -> None:
    temporary_paths: dict[str, Path] = {}
    try:
        for name, payload in files.items():
            descriptor, raw_path = tempfile.mkstemp(prefix=f".{name}.", dir=output_dir)
            temporary_path = Path(raw_path)
            temporary_paths[name] = temporary_path
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

        _check_output_targets(output_dir)
        for name in files:
            os.replace(temporary_paths.pop(name), output_dir / name)
    finally:
        for temporary_path in temporary_paths.values():
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def build_candidate(
    v1_dir: Path,
    additions_path: Path,
    legacy_metadata_path: Path,
    output_dir: Path,
) -> dict[str, int]:
    """Build a deterministic v2 draft from a validated v1 snapshot and JSONL inputs."""
    v1_path = Path(v1_dir)
    output_path = Path(output_dir)
    _ensure_output_not_v1(v1_path, output_path)
    _check_output_targets(output_path)
    payloads, manifest, counts, _, _ = _prepare_candidate(
        v1_path, Path(additions_path), Path(legacy_metadata_path)
    )
    output_path.mkdir(parents=True, exist_ok=True)
    _check_output_targets(output_path)
    files = {**payloads, "manifest.json": _manifest_bytes(manifest)}
    _write_output_atomically(output_path, files)
    return counts


def validate_candidate(
    v1_dir: Path,
    additions_path: Path,
    legacy_metadata_path: Path,
    output_dir: Path,
) -> dict[str, int]:
    """Validate a candidate against its parent and source-free metadata inputs."""
    v1_path = Path(v1_dir)
    output_path = Path(output_dir)
    _ensure_output_not_v1(v1_path, output_path)
    payloads, manifest, counts, v1_judgments, v1_anchors = _prepare_candidate(
        v1_path, Path(additions_path), Path(legacy_metadata_path)
    )
    output = output_path
    if output.is_symlink() or not output.is_dir():
        raise ValueError("candidate output must be a regular directory")
    names = {path.name for path in output.iterdir()}
    if names != set(_OUTPUT_FILES):
        raise ValueError("candidate output directory has missing or unexpected files")
    actual: dict[str, bytes] = {}
    for name in _OUTPUT_FILES:
        path = output / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"candidate {name} is missing or not a regular file")
        actual[name] = path.read_bytes()

    if actual["records.json"] != payloads["records.json"]:
        raise ValueError("candidate records.json does not preserve the v1 parent bytes and source hash set")
    for name, prefix in (("judgments.jsonl", v1_judgments), ("anchors.jsonl", v1_anchors)):
        if not actual[name].startswith(prefix):
            raise ValueError(f"candidate {name} v1 prefix changed")

    actual_manifest = _require_object(_decode_json(actual["manifest.json"], "candidate manifest.json"), "candidate manifest.json")
    actual_hashes = actual_manifest.get("payload_sha256")
    if not isinstance(actual_hashes, dict) or set(actual_hashes) != set(_PAYLOAD_FILES):
        raise ValueError("candidate manifest payload hashes are incomplete")
    for name in _PAYLOAD_FILES:
        if actual_hashes[name] != _sha256(actual[name]):
            raise ValueError(f"candidate manifest payload hash mismatch for {name}")
    for name in _PAYLOAD_FILES:
        if actual[name] != payloads[name]:
            raise ValueError(f"candidate {name} does not match the validated inputs")
    if actual_manifest != manifest or actual["manifest.json"] != _manifest_bytes(manifest):
        raise ValueError("candidate manifest does not match the current v1 parent and inputs")
    return counts


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--v1", type=Path, required=True)
        subparser.add_argument("--additions", type=Path, required=True)
        subparser.add_argument("--legacy-metadata", type=Path, required=True)
        subparser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    action = build_candidate if args.command == "build" else validate_candidate
    try:
        counts = action(args.v1, args.additions, args.legacy_metadata, args.output)
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
