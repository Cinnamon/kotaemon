"""Local-only commands for reviewing and running knowledge evaluation data.

Every artifact produced by this module is placed under a caller-selected local
root. Source-derived review material stays under ``draft/`` until a person
completes and approves it; model assets and their verified manifest stay under
``models/``; frozen snapshots and experiment output stay under their own
dedicated subdirectories.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

import click

from .local_corpus import scan_sources
from .local_ingest import build_local_draft
from .local_experiment import run_local_experiment
from .combination_eval import (
    repack_completed_combination_experiment,
    run_combination_experiment,
)
from .local_models import (
    EMBEDDING_MODEL_ID,
    RERANKER_MODEL_ID,
    LocalModelPaths,
    _hash_file,
    _local_weight_files,
    _require_offline_inference_process,
    _validate_and_hash_model_dir,
)
from .local_snapshot import load_local_snapshot
from .supplemental_baseline import run_supplemental_baseline


MODEL_MANIFEST_NAME = "model-manifest.json"
MODEL_MANIFEST_SCHEMA_VERSION = 2
_MODEL_SPECS = (
    ("embedding", EMBEDDING_MODEL_ID, "bge-m3"),
    ("reranker", RERANKER_MODEL_ID, "bge-reranker-v2-m3"),
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MANIFEST_FIELDS = {"schema_version", "models"}
_MODEL_ROW_FIELDS = {
    "role",
    "model_id",
    "revision",
    "directory",
    "weights_sha256",
    "assets_sha256",
    "source",
}


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


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


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _ensure_contained(path: Path, root: Path, label: str) -> Path:
    resolved_root = root.resolve()
    expanded_path = path.expanduser()
    if not expanded_path.is_absolute():
        expanded_path = Path.cwd() / expanded_path
    lexical_path = Path(os.path.abspath(expanded_path))
    try:
        lexical_path.relative_to(resolved_root)
    except ValueError:
        pass
    else:
        _reject_symlink_components(lexical_path, stop=resolved_root)
    resolved_path = expanded_path.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            f"{label} must resolve beneath the selected local root"
        ) from error
    return resolved_path


def _reject_symlink_components(path: Path, *, stop: Path) -> None:
    """Reject existing symlink components between ``path`` and ``stop``."""
    stop = stop.resolve()
    current = path
    while current != stop:
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(mode):
                raise ValueError(
                    f"Output/input path must not contain a symlink: {current}"
                )
        if current.parent == current:
            raise ValueError(f"Path is not beneath its expected root: {path}")
        current = current.parent


def _repository_root() -> Path:
    module_directory = Path(__file__).resolve().parent
    result = subprocess.run(
        ["git", "-C", str(module_directory), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("Unable to determine the Git checkout root for privacy checks")
    return Path(result.stdout.strip()).resolve()


def _require_ignored_repo_local_root(value: Path) -> None:
    """Require in-checkout output roots to be ignored before creating them."""
    root = Path(value).expanduser().resolve(strict=False)
    repository_root = _repository_root()
    try:
        relative = root.relative_to(repository_root)
    except ValueError:
        return

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "check-ignore",
            "--quiet",
            "--no-index",
            "--",
            relative.as_posix(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return
    if result.returncode == 1:
        raise ValueError(
            "A local root inside the Git checkout must be Git-ignored before "
            "the CLI writes there"
        )
    raise ValueError("Unable to verify that the selected local root is Git-ignored")


def _local_root(value: Path) -> Path:
    root = Path(value).expanduser().resolve(strict=False)
    if root.exists() and not root.is_dir():
        raise ValueError(f"Local root must be a directory: {root}")
    _require_ignored_repo_local_root(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _category_dir(root: Path, name: str) -> Path:
    path = root / name
    resolved = _ensure_contained(path, root, f"{name}/ output")
    _reject_symlink_components(resolved, stop=root)
    if resolved.exists() and not resolved.is_dir():
        raise ValueError(f"Local {name}/ output must be a directory")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _safe_relative_path(value: str, label: str) -> str:
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


def _source_root_label(value: str | None, source_root: Path) -> str:
    if value is not None:
        return _safe_relative_path(value, "source-root-label")

    source = Path(source_root).expanduser()
    if not source.is_absolute():
        return _safe_relative_path(source.as_posix(), "source-root-label")
    try:
        relative = source.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError as error:
        raise ValueError(
            "An absolute source root outside the working tree requires an explicit "
            "--source-root-label containing only repository-relative provenance"
        ) from error
    return _safe_relative_path(relative, "source-root-label")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def _write_draft_manifest(
    records: dict[str, Any], source_root: str, version: str
) -> dict[str, Any]:
    payloads = {
        "records.json": _canonical_json(records),
        "judgments.jsonl": b"",
        "anchors.jsonl": b"",
    }
    indexed_sources = {chunk["source_id"] for chunk in records["chunks"]}
    manifest = {
        "schema_version": 1,
        "snapshot_version": version,
        "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
        "payload_sha256": {
            name: _sha256(payload) for name, payload in payloads.items()
        },
        "review_status": "draft",
        "review_date": None,
        "source_root": source_root,
        "source_provenance": [
            {
                "source_id": source["source_id"],
                "repository_path": f"{source_root}/{source['relative_path']}",
                "sha256": source["sha256"],
            }
            for source in records["sources"]
        ],
        "parser_configuration": records["parser_configuration"],
        "splitter_configuration": records["splitter_configuration"],
        "counts": {
            "source_paths": len(records["sources"]),
            "documents": sum(
                source["duplicate_of"] is None
                and source["status"] == "parsed"
                and source["source_id"] in indexed_sources
                for source in records["sources"]
            ),
            "source_units": len(records["source_units"]),
            "chunks": len(records["chunks"]),
            "queries": 0,
            "anchors": 0,
        },
    }
    return manifest


def _render_review(
    records: dict[str, Any],
    *,
    omitted_topic_candidates: list[dict[str, Any]] = (),
    omission_reason: str = "omitted by the 24-source cap",
) -> bytes:
    indexed_source_ids = {chunk["source_id"] for chunk in records["chunks"]}
    selected_count = sum(
        row["duplicate_of"] is None
        and row["status"] == "parsed"
        and row["source_id"] in indexed_source_ids
        for row in records["sources"]
    )
    unique_count = sum(row["duplicate_of"] is None for row in records["sources"])
    lines = [
        "# Local knowledge evaluation review draft",
        "",
        "> This package is a local-only draft. Content-derived topic candidates are",
        "> unreviewed. Physical directory names are retained only as source-path",
        "> provenance and are never used as topic, virtual-path, or entity labels.",
        "",
        "## Content-derived topic candidates (unreviewed)",
        "",
        f"Selected {selected_count} of {unique_count} unique source documents "
        "for this draft; review the sample size and coverage manually.",
        "",
    ]
    selected_formats = sorted(
        {
            row["suffix"]
            for row in records["sources"]
            if row["duplicate_of"] is None
            and row["status"] == "parsed"
            and row["source_id"] in indexed_source_ids
        }
    )
    lines.append(
        "Selected usable source formats: "
        + (", ".join(selected_formats) if selected_formats else "none")
        + "."
    )
    lines.append("")
    candidates = records["topic_candidates"]
    if candidates:
        for item in candidates:
            locator = json.dumps(item["locator"], ensure_ascii=False, sort_keys=True)
            lines.append(
                f"- `{item['source_id']}` — {item['text']} "
                f"(provenance: `{item['relative_path']}`, locator: `{locator}`; "
                "verify manually)"
            )
    else:
        lines.append("- No content-derived candidate was extracted; review manually.")

    if omitted_topic_candidates:
        lines.extend(
            [
                "",
                "## Content-derived topic candidates outside the selected v1 sample",
                "",
                "These unreviewed source/topic pairs were "
                f"{omission_reason}; inspect them when checking format and topic "
                "coverage.",
                "",
            ]
        )
        for item in sorted(
            omitted_topic_candidates,
            key=lambda candidate: (
                candidate["source_id"],
                candidate["text"].casefold(),
                candidate["relative_path"],
            ),
        ):
            lines.append(
                f"- `{item['source_id']}` — {item['text']} "
                f"(provenance: `{item['relative_path']}`; {omission_reason}; "
                "verify manually)"
            )

    lines.extend(
        [
            "",
            "## Duplicate and excluded inputs",
            "",
        ]
    )
    excluded = records["excluded_inputs"]
    if excluded:
        lines.extend(
            f"- `{item['relative_path']}` — {item['reason']}" for item in excluded
        )
    else:
        lines.append("- None recorded.")

    quality = records["quality"]
    lines.extend(["", "## Extraction quality", ""])
    for name in (
        "empty_locators",
        "unusable_locators",
        "reader_diagnostics",
        "extraction_failures",
        "chunk_mapping_issues",
        "pages",
        "sheets",
    ):
        lines.append(f"- {name.replace('_', ' ')}: {len(quality[name])}")
    for failure in quality["extraction_failures"]:
        lines.append(
            f"- Extraction failure: `{failure['relative_path']}` "
            f"(`{failure['error_type']}`)"
        )

    lines.extend(["", "## Chunk previews", ""])
    chunks_by_source: dict[str, list[dict[str, Any]]] = {}
    for chunk in records["chunks"]:
        chunks_by_source.setdefault(chunk["source_id"], []).append(chunk)
    source_rows = {item["source_id"]: item for item in records["sources"]}
    if chunks_by_source:
        for source_id, chunks in chunks_by_source.items():
            row = source_rows[source_id]
            lines.append(f"### `{source_id}` — `{row['relative_path']}`")
            lines.append("")
            for chunk in chunks[:3]:
                text = chunk["text"].replace("\n", " ").strip()
                if len(text) > 500:
                    text = text[:497] + "..."
                lines.append(
                    f"- Chunk `{chunk['chunk_id']}`: {text or '(empty chunk)'}"
                )
            lines.append("")
    else:
        lines.append("No chunks were extracted.")

    lines.extend(
        [
            "",
            "## Questions, judgments, and evidence anchors",
            "",
            "No questions, relevance judgments, disallowed-source labels, or",
            "query-linked evidence anchors were generated. `judgments.jsonl` and",
            "`anchors.jsonl` are intentionally empty until a person authors and",
            "reviews them against the source content.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _select_v1_source_ids(records: dict[str, Any]) -> tuple[str, ...]:
    """Choose up to 24 usable documents by file format and text candidates.

    This is only a deterministic sampling proposal. Topic candidates remain
    unreviewed, and physical source paths are never used as topic labels or
    selection buckets.
    """
    indexed_source_ids = {chunk["source_id"] for chunk in records["chunks"]}
    usable = [
        row
        for row in records["sources"]
        if row["duplicate_of"] is None
        and row["status"] == "parsed"
        and row["source_id"] in indexed_source_ids
    ]
    usable_ids = {row["source_id"] for row in usable}
    if len(usable) < 20:
        raise ValueError(
            f"v1 sampling needs at least 20 usable unique documents; found {len(usable)}. "
            "Use --all-sources for a non-v1 draft."
        )
    if len(usable) <= 24:
        return tuple(sorted(row["source_id"] for row in usable))

    selected: set[str] = set()
    by_format: dict[str, list[dict[str, Any]]] = {}
    for row in usable:
        by_format.setdefault(row["suffix"], []).append(row)
    for suffix in sorted(by_format):
        candidate = min(by_format[suffix], key=lambda row: row["source_id"])
        selected.add(candidate["source_id"])

    content_topics: dict[str, set[str]] = {}
    for candidate in records["topic_candidates"]:
        text = candidate["text"].strip()
        if text and candidate["source_id"] in usable_ids:
            content_topics.setdefault(candidate["source_id"], set()).add(
                text.casefold()
            )
    for topic in sorted(
        {topic for values in content_topics.values() for topic in values}
    ):
        if len(selected) >= 24:
            break
        matching = sorted(
            source_id
            for source_id, topics in content_topics.items()
            if topic in topics and source_id not in selected
        )
        if matching:
            selected.add(matching[0])

    for row in sorted(usable, key=lambda item: item["source_id"]):
        if len(selected) >= 24:
            break
        selected.add(row["source_id"])
    return tuple(sorted(selected))


def _validate_explicit_v1_sample(
    records: dict[str, Any], selected_ids: set[str]
) -> None:
    """Require usable source count and full-corpus usable-format coverage."""
    source_rows = records["sources"]
    canonical_rows = [row for row in source_rows if row["duplicate_of"] is None]
    known_ids = {row["source_id"] for row in canonical_rows}
    unknown_ids = selected_ids - known_ids
    if unknown_ids:
        raise ValueError(
            "Unknown v1 sample source IDs: " + ", ".join(sorted(unknown_ids))
        )

    chunked_ids = {chunk["source_id"] for chunk in records["chunks"]}
    usable_rows = [
        row
        for row in canonical_rows
        if row["status"] == "parsed" and row["source_id"] in chunked_ids
    ]
    usable_ids = {row["source_id"] for row in usable_rows}
    selected_rows = [row for row in canonical_rows if row["source_id"] in selected_ids]
    selected_usable = [row for row in usable_rows if row["source_id"] in selected_ids]
    available_formats = {row["suffix"] for row in usable_rows}
    selected_formats = {row["suffix"] for row in selected_usable}
    missing_formats = sorted(available_formats - selected_formats)

    problems: list[str] = []
    if len(usable_ids & selected_ids) < 20:
        problems.append(
            f"selection yielded {len(usable_ids & selected_ids)} usable unique "
            "documents; v1 requires at least 20"
        )
    if missing_formats:
        problems.append(
            "selection lacks usable format coverage for "
            f"{', '.join(missing_formats)}; selected usable formats are "
            f"{', '.join(sorted(selected_formats)) or 'none'}, while the full corpus "
            "has usable formats "
            f"{', '.join(sorted(available_formats)) or 'none'}"
        )

    failure_by_id = {
        item["source_id"]: item for item in records["quality"]["extraction_failures"]
    }
    empty_locators_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in records["quality"]["empty_locators"]:
        empty_locators_by_id.setdefault(item["source_id"], []).append(item)
    mapping_issues_by_id: dict[str, list[dict[str, Any]]] = {}
    for item in records["quality"]["chunk_mapping_issues"]:
        mapping_issues_by_id.setdefault(item["source_id"], []).append(item)
    diagnostics: list[str] = []
    for row in sorted(selected_rows, key=lambda item: item["relative_path"]):
        if row["source_id"] in usable_ids:
            continue
        failure = failure_by_id.get(row["source_id"])
        if failure is not None:
            reason = failure.get("reason")
            details = failure["error_type"]
            if reason:
                details += f", {reason}"
        else:
            details_list = [
                f"empty extraction ({item['reason']})"
                for item in empty_locators_by_id.get(row["source_id"], [])
            ]
            details_list.extend(
                f"chunk mapping issue ({item['reason']}, {item['error_type']})"
                for item in mapping_issues_by_id.get(row["source_id"], [])
            )
            details = "; ".join(details_list) or "no chunk-backed content"
        diagnostics.append(f"{row['relative_path']} ({details})")
    if problems:
        message = "--sample-id v1 " + "; ".join(problems)
        if diagnostics:
            message += ". Unusable requested sources: " + "; ".join(diagnostics)
        raise ValueError(message)


def _filter_records_to_sources(
    records: dict[str, Any], selected_ids: set[str]
) -> dict[str, Any]:
    """Keep the full path inventory but index only explicitly selected sources."""
    filtered = copy.deepcopy(records)
    source_by_path = {row["relative_path"]: row for row in filtered["sources"]}
    for row in filtered["sources"]:
        if (
            row["duplicate_of"] is None
            and row["source_id"] not in selected_ids
            and row["status"] == "parsed"
        ):
            row["status"] = "not_selected"

    filtered["source_units"] = [
        row for row in filtered["source_units"] if row["source_id"] in selected_ids
    ]
    filtered["chunks"] = [
        row for row in filtered["chunks"] if row["source_id"] in selected_ids
    ]
    filtered["topic_candidates"] = [
        row for row in filtered["topic_candidates"] if row["source_id"] in selected_ids
    ]
    candidate_source_ids = {row["source_id"] for row in filtered["topic_candidates"]}
    filtered["topic_review_source_ids"] = [
        row["source_id"]
        for row in filtered["sources"]
        if row["duplicate_of"] is None
        and row["source_id"] in selected_ids
        and row["source_id"] not in candidate_source_ids
    ]

    excluded_by_path = {
        item["relative_path"]: dict(item)
        for item in filtered["excluded_inputs"]
        if item["source_id"] is not None
    }
    excluded = [
        item for item in filtered["excluded_inputs"] if item["source_id"] is None
    ]
    for row in filtered["sources"]:
        if row["duplicate_of"] is None:
            if row["source_id"] in selected_ids or row["status"] == "failed":
                continue
            reason = "not_selected"
        else:
            canonical = source_by_path[row["duplicate_of"]]
            reason = (
                "not_selected"
                if canonical["status"] == "not_selected"
                else "duplicate_bytes"
            )
        item = excluded_by_path.get(row["relative_path"], {})
        excluded.append(
            {
                **item,
                "relative_path": row["relative_path"],
                "source_id": row["source_id"],
                "duplicate_of": row["duplicate_of"],
                "reason": reason,
            }
        )
    filtered["excluded_inputs"] = sorted(
        excluded, key=lambda item: item["relative_path"]
    )
    return filtered


def _read_jsonl_rows(payload: bytes, label: str) -> list[Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} must be UTF-8 JSONL") from error
    rows = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line, object_pairs_hook=_reject_duplicate_keys))
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError(f"{label} line {line_number} is invalid JSON") from error
    return rows


def _read_regular_file(path: Path, label: str) -> bytes:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise ValueError(f"Required {label} is missing: {path}") from error
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError(f"{label} must be a regular non-symlink file")
    return path.read_bytes()


def _validate_snapshot_approval(snapshot_dir: Path) -> None:
    """Require the frozen approval sidecar to bind to this manifest."""
    manifest_bytes = _read_regular_file(
        snapshot_dir / "manifest.json", "snapshot manifest"
    )
    manifest = _decode_json(manifest_bytes, "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("review_status") != "approved":
        raise ValueError("run requires an approved snapshot")
    manifest_date = manifest.get("review_date")
    try:
        if (
            not isinstance(manifest_date, str)
            or date.fromisoformat(manifest_date).isoformat() != manifest_date
        ):
            raise ValueError
    except ValueError as error:
        raise ValueError(
            "approved snapshot manifest requires an ISO review_date"
        ) from error

    approval_bytes = _read_regular_file(
        snapshot_dir / "approval.json", "snapshot approval sidecar"
    )
    approval = _decode_json(approval_bytes, "approval.json")
    expected_fields = {
        "approved_by",
        "approved_at",
        "snapshot_manifest_sha256",
    }
    if not isinstance(approval, dict) or set(approval) != expected_fields:
        raise ValueError("snapshot approval sidecar has invalid schema fields")
    approved_by = approval.get("approved_by")
    if (
        not isinstance(approved_by, str)
        or not approved_by.strip()
        or approved_by != approved_by.strip()
    ):
        raise ValueError("snapshot approval sidecar requires approved_by")
    approved_at = approval.get("approved_at")
    try:
        if (
            not isinstance(approved_at, str)
            or date.fromisoformat(approved_at).isoformat() != approved_at
        ):
            raise ValueError
    except ValueError as error:
        raise ValueError(
            "snapshot approval sidecar requires an ISO approved_at"
        ) from error
    if approved_at != manifest_date:
        raise ValueError(
            "snapshot approval sidecar date does not match manifest review_date"
        )
    expected_hash = _sha256(manifest_bytes)
    if approval.get("snapshot_manifest_sha256") != expected_hash:
        raise ValueError("snapshot approval sidecar manifest hash mismatch")


def _reviewed_manifest_for_freeze(
    draft_dir: Path,
    *,
    version: str,
    approved_at: str,
) -> tuple[dict[str, Any], dict[str, bytes]]:
    manifest_bytes = _read_regular_file(draft_dir / "manifest.json", "draft manifest")
    manifest = _decode_json(manifest_bytes, "manifest.json")
    if not isinstance(manifest, dict) or manifest.get("review_status") != "draft":
        raise ValueError("freeze requires a draft snapshot manifest")
    payloads = {
        name: _read_regular_file(draft_dir / name, name)
        for name in ("records.json", "judgments.jsonl", "anchors.jsonl")
    }
    records = _decode_json(payloads["records.json"], "records.json")
    if not isinstance(records, dict):
        raise ValueError("records.json must contain a JSON object")
    judgments = _read_jsonl_rows(payloads["judgments.jsonl"], "judgments.jsonl")
    anchors = _read_jsonl_rows(payloads["anchors.jsonl"], "anchors.jsonl")
    if not judgments:
        raise ValueError("freeze requires person-authored, reviewed judgments")
    if not anchors:
        raise ValueError("freeze requires person-reviewed evidence anchors")

    source_root = _safe_relative_path(manifest.get("source_root"), "source_root")
    source_rows = records.get("sources")
    if not isinstance(source_rows, list):
        raise ValueError("records.sources must be a list")
    manifest = {
        "schema_version": 1,
        "snapshot_version": version,
        "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
        "payload_sha256": {
            name: _sha256(payload) for name, payload in payloads.items()
        },
        "review_status": "approved",
        "review_date": approved_at,
        "source_root": source_root,
        "source_provenance": [
            {
                "source_id": source["source_id"],
                "repository_path": f"{source_root}/{source['relative_path']}",
                "sha256": source["sha256"],
            }
            for source in source_rows
        ],
        "parser_configuration": records["parser_configuration"],
        "splitter_configuration": records["splitter_configuration"],
        "counts": {
            "source_paths": len(source_rows),
            "documents": sum(
                source["duplicate_of"] is None
                and source["status"] == "parsed"
                and source["source_id"]
                in {chunk["source_id"] for chunk in records["chunks"]}
                for source in source_rows
            ),
            "source_units": len(records["source_units"]),
            "chunks": len(records["chunks"]),
            "queries": len(judgments),
            "anchors": len(anchors),
        },
    }
    return manifest, payloads


def _full_commit_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a full immutable commit SHA")
    return value


def _safe_model_directory(value: Any, label: str) -> str:
    return _safe_relative_path(value, label)


def _manifest_candidates(models_root: Path) -> list[Path]:
    return sorted(
        path
        for path in models_root.rglob(MODEL_MANIFEST_NAME)
        if path.name == MODEL_MANIFEST_NAME
    )


def _model_asset_hashes(model_dir: Path) -> dict[str, str]:
    """Hash every regular inference asset except Hub download bookkeeping."""
    assets: dict[str, str] = {}
    for path in sorted(model_dir.rglob("*")):
        relative = path.relative_to(model_dir).as_posix()
        parts = PurePosixPath(relative).parts
        if parts[:2] == (".cache", "huggingface"):
            continue
        if path.is_symlink():
            raise ValueError(f"Model asset must not be a symlink: {relative}")
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError as error:
            raise ValueError(
                f"Model asset disappeared while hashing: {relative}"
            ) from error
        if stat.S_ISREG(mode):
            assets[relative] = _hash_file(path)
        elif not stat.S_ISDIR(mode):
            raise ValueError(f"Model asset must be a regular file: {relative}")
    return dict(sorted(assets.items()))


def _validate_model_manifest_shape(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != _MANIFEST_FIELDS:
        raise ValueError("model manifest has invalid schema fields")
    schema_version = value.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or schema_version != MODEL_MANIFEST_SCHEMA_VERSION
    ):
        raise ValueError(
            f"unsupported model manifest schema_version {schema_version!r}"
        )
    rows = value.get("models")
    if not isinstance(rows, list) or len(rows) != len(_MODEL_SPECS):
        raise ValueError(
            "model manifest must contain exactly the embedding and reranker roles"
        )

    expected = {role: model_id for role, model_id, _ in _MODEL_SPECS}
    parsed: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        label = f"model manifest models[{index}]"
        if not isinstance(row, dict) or set(row) != _MODEL_ROW_FIELDS:
            raise ValueError(f"{label} has invalid schema fields")
        role = row.get("role")
        if role not in expected:
            raise ValueError(f"{label} has an unknown role")
        if role in parsed:
            raise ValueError(f"model manifest contains duplicate role {role!r}")
        if row.get("model_id") != expected[role]:
            raise ValueError(f"{role} model_id must be {expected[role]!r}")
        _full_commit_sha(row.get("revision"), f"{role} revision")
        _safe_model_directory(row.get("directory"), f"{role} directory")
        if row.get("source") not in {"cached", "downloaded"}:
            raise ValueError(f"{role} source must be 'cached' or 'downloaded'")
        hashes = row.get("weights_sha256")
        if not isinstance(hashes, dict) or not hashes:
            raise ValueError(f"{role} weights_sha256 must be a non-empty object")
        if list(hashes) != sorted(hashes):
            raise ValueError(f"{role} weight filenames must be sorted")
        for filename, digest in hashes.items():
            if (
                not isinstance(filename, str)
                or not filename
                or Path(filename).name != filename
                or filename in {".", ".."}
            ):
                raise ValueError(f"{role} contains an unsafe weight filename")
            if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
                raise ValueError(f"{role} has an invalid weight SHA-256 hash")
        assets = row.get("assets_sha256")
        if not isinstance(assets, dict) or not assets:
            raise ValueError(f"{role} assets_sha256 must be a non-empty object")
        if list(assets) != sorted(assets):
            raise ValueError(f"{role} asset filenames must be sorted")
        for filename, digest in assets.items():
            _safe_relative_path(filename, f"{role} asset filename")
            if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
                raise ValueError(f"{role} has an invalid asset SHA-256 hash")
        parsed[role] = row
    if set(parsed) != set(expected):
        raise ValueError("model manifest must contain exactly one row per role")
    ordered_roles = [row["role"] for row in rows]
    if ordered_roles != ["embedding", "reranker"]:
        raise ValueError("model manifest roles must be ordered embedding, reranker")
    if parsed["embedding"]["directory"] == parsed["reranker"]["directory"]:
        raise ValueError("embedding and reranker directories must be distinct")
    return parsed


def _verify_model_directory(
    models_root: Path,
    relative_directory: str,
    expected_weight_hashes: dict[str, str],
    expected_asset_hashes: dict[str, str],
    role: str,
) -> Path:
    path = models_root.joinpath(*relative_directory.split("/"))
    resolved = _ensure_contained(path, models_root, f"{role} model directory")
    _reject_symlink_components(resolved, stop=models_root.resolve())
    if not resolved.is_dir():
        raise ValueError(f"{role} model directory is missing: {relative_directory}")
    _reject_model_tree_symlinks(models_root, resolved, role)
    _, actual_hash_rows = _validate_and_hash_model_dir(resolved)
    actual_hashes = dict(actual_hash_rows)
    for weight_path in _local_weight_files(resolved):
        if weight_path.is_symlink() or not weight_path.is_file():
            raise ValueError(f"{role} model weights must be regular files")
    if actual_hashes != expected_weight_hashes:
        raise ValueError(f"{role} model weight hash mismatch")
    actual_asset_hashes = _model_asset_hashes(resolved)
    if actual_asset_hashes != expected_asset_hashes:
        raise ValueError(f"{role} model asset filename or hash mismatch")
    return resolved


def _reject_model_tree_symlinks(models_root: Path, model_dir: Path, role: str) -> None:
    root = models_root.resolve()
    for path in model_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"{role} model asset must not be a symlink: {path.name}")
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise ValueError(f"{role} model asset resolves outside local models/")


def resolve_model_paths(
    local_root: Path,
    embedding_model_dir: Path | None,
    reranker_model_dir: Path | None,
) -> LocalModelPaths:
    """Verify one local model manifest and return provenance-bound model paths."""
    model_paths, _manifest_bytes = _resolve_model_paths_with_manifest(
        local_root,
        embedding_model_dir,
        reranker_model_dir,
    )
    return model_paths


def _resolve_model_paths_with_manifest(
    local_root: Path,
    embedding_model_dir: Path | None,
    reranker_model_dir: Path | None,
) -> tuple[LocalModelPaths, bytes]:
    """Return verified model paths and the exact bytes used to verify them."""
    root = Path(local_root).expanduser().resolve()
    models_root = root / "models"
    _reject_symlink_components(models_root, stop=root)
    if not models_root.is_dir():
        raise ValueError("local models/ directory is missing")
    candidates = _manifest_candidates(models_root)
    if not candidates:
        raise ValueError("local model manifest is missing")
    if len(candidates) != 1:
        raise ValueError("ambiguous model manifests; expected exactly one")
    manifest_path = candidates[0]
    if manifest_path != models_root / MODEL_MANIFEST_NAME:
        raise ValueError("model manifest must be models/model-manifest.json")
    manifest_bytes = _read_regular_file(manifest_path, "model manifest")
    parsed = _validate_model_manifest_shape(
        _decode_json(manifest_bytes, MODEL_MANIFEST_NAME)
    )

    supplied = {
        "embedding": embedding_model_dir,
        "reranker": reranker_model_dir,
    }
    resolved_paths: dict[str, Path] = {}
    for role, model_id, _default_directory in _MODEL_SPECS:
        row = parsed[role]
        resolved = _verify_model_directory(
            models_root,
            row["directory"],
            row["weights_sha256"],
            row["assets_sha256"],
            role,
        )
        supplied_path = supplied[role]
        if supplied_path is None:
            raise ValueError(f"run requires an explicit --{role}-model-dir")
        supplied_resolved = Path(supplied_path).expanduser().resolve(strict=False)
        if supplied_resolved != resolved:
            raise ValueError(
                f"--{role}-model-dir does not match the verified manifest directory"
            )
        if not supplied_resolved.is_relative_to(models_root.resolve()):
            raise ValueError(f"--{role}-model-dir must resolve beneath local models/")
        resolved_paths[role] = resolved

    embedding = parsed["embedding"]
    reranker = parsed["reranker"]
    return (
        LocalModelPaths(
            embedding_model_dir=resolved_paths["embedding"],
            reranker_model_dir=resolved_paths["reranker"],
            embedding_revision=embedding["revision"],
            embedding_weight_source=embedding["source"],
            reranker_revision=reranker["revision"],
            reranker_weight_source=reranker["source"],
        ),
        manifest_bytes,
    )


def _offline_hub_snapshot(model_id: str) -> Path | None:
    """Return a complete cached snapshot using Hugging Face's offline lookup."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise click.ClickException(
            "Model management requires the local-eval extra with huggingface_hub."
        ) from error
    try:
        snapshot = snapshot_download(
            repo_id=model_id,
            repo_type="model",
            revision="main",
            local_files_only=True,
        )
    except Exception as error:
        if type(error).__name__ in {
            "LocalEntryNotFoundError",
            "EntryNotFoundError",
            "RevisionNotFoundError",
        }:
            return None
        raise
    return Path(snapshot)


def _resolve_hub_revision(model_id: str) -> str:
    try:
        from huggingface_hub import HfApi
    except ImportError as error:
        raise click.ClickException(
            "Model management requires the local-eval extra with huggingface_hub."
        ) from error
    info = HfApi().model_info(model_id, revision="main")
    return _full_commit_sha(info.sha, f"resolved {model_id} revision")


def _download_hub_snapshot(model_id: str, revision: str, destination: Path) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except ImportError as error:
        raise click.ClickException(
            "Model management requires the local-eval extra with huggingface_hub."
        ) from error
    downloaded = snapshot_download(
        repo_id=model_id,
        repo_type="model",
        revision=revision,
        local_dir=str(destination),
        cache_dir=str(destination.parent / ".hf-cache"),
        local_files_only=False,
    )
    return Path(downloaded)


def _download_models_into(local_root: Path) -> Path:
    root = _local_root(local_root)
    models_root = _category_dir(root, "models")
    manifest_path = models_root / MODEL_MANIFEST_NAME
    _ensure_contained(manifest_path, root, "model manifest output")
    _reject_symlink_components(manifest_path, stop=root)
    if manifest_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing model manifest: {manifest_path}"
        )
    final_directories = [models_root / name for _, _, name in _MODEL_SPECS]
    if any(path.exists() for path in final_directories):
        raise FileExistsError("Refusing to overwrite existing local model directories")
    if _manifest_candidates(models_root):
        raise ValueError("Remove ambiguous model manifests before downloading models")

    staging = models_root / f".model-stage-{uuid.uuid4().hex}"
    staging.mkdir()
    rows: list[dict[str, Any]] = []
    published_directories: list[Path] = []
    try:
        for role, model_id, relative_directory in _MODEL_SPECS:
            staged_dir = staging / relative_directory
            cached_snapshot = _offline_hub_snapshot(model_id)
            if cached_snapshot is not None:
                cached_snapshot = Path(cached_snapshot)
                if not cached_snapshot.is_dir():
                    raise ValueError(
                        f"Hugging Face cache lookup returned no directory for {model_id}"
                    )
                revision = _full_commit_sha(
                    cached_snapshot.name, f"cached {model_id} revision"
                )
                shutil.copytree(cached_snapshot, staged_dir, symlinks=False)
                source = "cached"
            else:
                revision = _resolve_hub_revision(model_id)
                download_result = _download_hub_snapshot(model_id, revision, staged_dir)
                if download_result.resolve(strict=False) != staged_dir.resolve(
                    strict=False
                ):
                    raise ValueError(
                        f"Hugging Face download for {model_id} did not use the staged local directory"
                    )
                source = "downloaded"

            _reject_model_tree_symlinks(models_root, staged_dir, role)
            _, weight_rows = _validate_and_hash_model_dir(staged_dir)
            asset_hashes = _model_asset_hashes(staged_dir)
            rows.append(
                {
                    "role": role,
                    "model_id": model_id,
                    "revision": revision,
                    "directory": relative_directory,
                    "weights_sha256": dict(sorted(weight_rows)),
                    "assets_sha256": asset_hashes,
                    "source": source,
                }
            )

        for _, _, relative_directory in _MODEL_SPECS:
            final_directory = models_root / relative_directory
            os.rename(staging / relative_directory, final_directory)
            published_directories.append(final_directory)

        manifest = {
            "schema_version": MODEL_MANIFEST_SCHEMA_VERSION,
            "models": rows,
        }
        _atomic_write(manifest_path, _canonical_json(manifest))
    except Exception:
        for path in published_directories:
            if path.exists():
                shutil.rmtree(path)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return manifest_path


@click.group()
def main() -> None:
    """Prepare and run local knowledge evaluation without remote inference."""


@main.command("inventory")
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Root of explicitly selected source files to inventory.",
)
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for all generated output.",
)
def inventory_command(source_root: Path, local_root: Path) -> None:
    """Write a deterministic source inventory under local/draft/."""
    try:
        root = _local_root(local_root)
        draft_root = _category_dir(root, "draft")
        output = draft_root / "inventory.json"
        _ensure_contained(output, root, "inventory output")
        _reject_symlink_components(output, stop=root)
        payload = _canonical_json([row.__dict__ for row in scan_sources(source_root)])
        _atomic_write(output, payload)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Inventory written locally: {output}")


@main.command("prepare-review")
@click.option(
    "--source-root",
    type=click.Path(path_type=Path, exists=True, file_okay=False),
    required=True,
    help="Root of source files to parse locally.",
)
@click.option(
    "--source-root-label",
    type=str,
    default=None,
    help="Repository-relative provenance label for an external/temp source root.",
)
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for all generated output.",
)
@click.option("--version", "version_name", default="v1", show_default=True)
@click.option(
    "--sample-id",
    "sample_ids",
    multiple=True,
    help="Optional canonical source SHA-256 to include; may be repeated.",
)
@click.option(
    "--all-sources",
    is_flag=True,
    help="Prepare all sources as a non-v1 draft instead of sampling 20–24 documents.",
)
def prepare_review_command(
    source_root: Path,
    source_root_label: str | None,
    local_root: Path,
    version_name: str,
    sample_ids: tuple[str, ...],
    all_sources: bool,
) -> None:
    """Create an unreviewed, local-only package with no generated gold labels."""
    try:
        if _VERSION_RE.fullmatch(version_name) is None or version_name in {".", ".."}:
            raise ValueError("version must be a safe directory name")
        root = _local_root(local_root)
        draft_root = _category_dir(root, "draft")
        destination = draft_root / version_name
        _ensure_contained(destination, root, "review draft output")
        _reject_symlink_components(destination, stop=root)
        if destination.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing draft: {destination}"
            )
        if all_sources and sample_ids:
            raise ValueError("--all-sources cannot be combined with --sample-id")
        if all_sources and version_name == "v1":
            raise ValueError(
                "--all-sources is for a non-v1 draft; v1 requires sampling"
            )
        unique_sample_ids = tuple(sorted(set(sample_ids)))
        if (
            unique_sample_ids
            and version_name == "v1"
            and not 20 <= len(unique_sample_ids) <= 24
        ):
            raise ValueError("a v1 --sample-id selection must contain 20–24 unique IDs")
        label = _source_root_label(source_root_label, source_root)
        staging = draft_root / f".draft-stage-{uuid.uuid4().hex}"
        staging.mkdir()
        try:
            omitted_topic_candidates: list[dict[str, Any]] = []
            if unique_sample_ids and version_name == "v1":
                summary = build_local_draft(source_root, staging)
                records = _decode_json(summary.records_payload, "records.json")
                selected_ids = set(unique_sample_ids)
                _validate_explicit_v1_sample(records, selected_ids)
                omitted_topic_candidates = [
                    candidate
                    for candidate in records["topic_candidates"]
                    if candidate["source_id"] not in selected_ids
                ]
                records = _filter_records_to_sources(records, selected_ids)
                records_payload = _canonical_json(records)
            elif unique_sample_ids:
                summary = build_local_draft(
                    source_root,
                    staging,
                    sample_ids=unique_sample_ids,
                )
                records_payload = summary.records_payload
            elif all_sources or version_name != "v1":
                summary = build_local_draft(source_root, staging)
                records_payload = summary.records_payload
            else:
                summary = build_local_draft(source_root, staging)
                records = _decode_json(summary.records_payload, "records.json")
                selected_ids = set(_select_v1_source_ids(records))
                omitted_topic_candidates = [
                    candidate
                    for candidate in records["topic_candidates"]
                    if candidate["source_id"] not in selected_ids
                ]
                records = _filter_records_to_sources(records, selected_ids)
                records_payload = _canonical_json(records)
            records = _decode_json(records_payload, "records.json")
            (staging / "records.json").write_bytes(records_payload)
            (staging / "judgments.jsonl").write_bytes(b"")
            (staging / "anchors.jsonl").write_bytes(summary.anchors_payload)
            manifest = _write_draft_manifest(records, label, version_name)
            (staging / "manifest.json").write_bytes(_canonical_json(manifest))
            (staging / "REVIEW.md").write_bytes(
                _render_review(
                    records,
                    omitted_topic_candidates=omitted_topic_candidates,
                    omission_reason=(
                        "not selected for this v1 sample"
                        if unique_sample_ids and version_name == "v1"
                        else "omitted by the 24-source cap"
                    ),
                )
            )
            os.rename(staging, destination)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Review draft written locally: {destination}")


@main.command("freeze")
@click.option(
    "--draft-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Completed local/draft/<version> directory.",
)
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for all generated output.",
)
@click.option("--version", "version_name", default=None)
@click.option("--approved-by", required=True, type=str)
@click.option("--approved-at", required=True, type=str)
def freeze_command(
    draft_dir: Path,
    local_root: Path,
    version_name: str | None,
    approved_by: str,
    approved_at: str,
) -> None:
    """Freeze a completed draft only after explicit human approval."""
    try:
        root = _local_root(local_root)
        draft_root = _category_dir(root, "draft")
        draft_path = _ensure_contained(Path(draft_dir), draft_root, "draft snapshot")
        _reject_symlink_components(draft_path, stop=draft_root)
        if not draft_path.is_dir():
            raise ValueError("draft snapshot must be a directory beneath local/draft/")
        if not approved_by.strip() or approved_by != approved_by.strip():
            raise ValueError(
                "--approved-by must be a non-empty name without surrounding whitespace"
            )
        try:
            parsed_date = date.fromisoformat(approved_at)
        except ValueError as error:
            raise ValueError("--approved-at must be an ISO YYYY-MM-DD date") from error
        if parsed_date.isoformat() != approved_at:
            raise ValueError("--approved-at must be an ISO YYYY-MM-DD date")
        version = version_name or draft_path.name
        if _VERSION_RE.fullmatch(version) is None or version in {".", ".."}:
            raise ValueError("version must be a safe directory name")

        snapshots_root = _category_dir(root, "snapshots")
        destination = snapshots_root / version
        _ensure_contained(destination, root, "snapshot output")
        _reject_symlink_components(destination, stop=root)
        if destination.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing snapshot: {destination}"
            )
        manifest, payloads = _reviewed_manifest_for_freeze(
            draft_path,
            version=version,
            approved_at=approved_at,
        )

        staging_parent = snapshots_root / f".freeze-stage-{uuid.uuid4().hex}"
        staging_parent.mkdir()
        staging = staging_parent / version
        staging.mkdir()
        try:
            for name, payload in payloads.items():
                (staging / name).write_bytes(payload)
            snapshot_manifest = _canonical_json(manifest)
            (staging / "manifest.json").write_bytes(snapshot_manifest)
            (staging / "approval.json").write_bytes(
                _canonical_json(
                    {
                        "approved_by": approved_by,
                        "approved_at": approved_at,
                        "snapshot_manifest_sha256": _sha256(snapshot_manifest),
                    }
                )
            )
            load_local_snapshot(staging)
            os.rename(staging, destination)
        finally:
            if staging_parent.exists():
                shutil.rmtree(staging_parent)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Approved snapshot frozen at {destination} (approved by {approved_by})")


@main.command("download-models")
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for models/ and its manifest.",
)
def download_models_command(local_root: Path) -> None:
    """Copy complete cached models or download immutable local snapshots."""
    try:
        manifest_path = _download_models_into(local_root)
    except (OSError, ValueError, click.ClickException) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Verified local model manifest written atomically: {manifest_path}")


def _attach_verified_model_manifest(artifact_dir: Path, manifest_bytes: bytes) -> None:
    """Add the verified provenance manifest and bind it into the run sidecar."""
    manifest_path = artifact_dir / MODEL_MANIFEST_NAME
    sidecar_path = artifact_dir / "artifact-manifest.json"
    sidecar = _decode_json(
        _read_regular_file(sidecar_path, "run artifact-manifest.json"),
        "artifact-manifest.json",
    )
    if (
        not isinstance(sidecar, dict)
        or not isinstance(sidecar.get("artifacts"), list)
        or any(not isinstance(entry, dict) for entry in sidecar["artifacts"])
    ):
        raise ValueError("run artifact-manifest.json has an invalid schema")
    manifest_entries = [
        entry
        for entry in sidecar["artifacts"]
        if entry.get("path") == MODEL_MANIFEST_NAME
    ]
    expected_entry = {
        "path": MODEL_MANIFEST_NAME,
        "sha256": _sha256(manifest_bytes),
        "size_bytes": len(manifest_bytes),
        "kind": "verified_model_manifest",
    }
    if manifest_path.exists() or manifest_path.is_symlink():
        if _read_regular_file(manifest_path, "run model manifest") != manifest_bytes:
            raise ValueError("run output model manifest does not match verified input")
        if manifest_entries == [expected_entry]:
            return
        if manifest_entries:
            raise ValueError("run artifact-manifest.json has a conflicting model manifest")
    elif manifest_entries:
        raise ValueError("run artifact-manifest.json lists a missing model manifest")

    _atomic_write(manifest_path, manifest_bytes)
    sidecar["artifacts"].append(expected_entry)
    _atomic_write(sidecar_path, _canonical_json(sidecar))


@main.command("run")
@click.option(
    "--snapshot",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Approved snapshot under local/snapshots/.",
)
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for models/ and runs/.",
)
@click.option(
    "--embedding-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Explicit local BAAI/bge-m3 directory verified by the model manifest.",
)
@click.option(
    "--reranker-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Explicit local BAAI/bge-reranker-v2-m3 directory verified by the manifest.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path, file_okay=False),
    default=None,
    help="Optional destination beneath local/runs/; defaults to snapshot name.",
)
def run_command(
    snapshot: Path,
    local_root: Path,
    embedding_model_dir: Path | None,
    reranker_model_dir: Path | None,
    output_dir: Path | None,
) -> None:
    """Run the fixed local experiment with one verified model manifest."""
    try:
        root = _local_root(local_root)
        snapshots_root = _category_dir(root, "snapshots")
        snapshot_path = _ensure_contained(Path(snapshot), snapshots_root, "snapshot")
        _reject_symlink_components(snapshot_path, stop=snapshots_root)
        if not snapshot_path.is_dir():
            raise ValueError("snapshot must be a directory beneath local/snapshots/")
        try:
            reviewed_snapshot = load_local_snapshot(snapshot_path)
        except ValueError as error:
            if "review_status='approved'" in str(error):
                raise ValueError("run requires an approved snapshot") from error
            raise
        _validate_snapshot_approval(snapshot_path)
        model_paths, manifest_bytes = _resolve_model_paths_with_manifest(
            root,
            embedding_model_dir,
            reranker_model_dir,
        )
        _require_offline_inference_process()
        runs_root = _category_dir(root, "runs")
        if output_dir is None:
            artifact_dir = runs_root / snapshot_path.name
        else:
            supplied = Path(output_dir).expanduser()
            if not supplied.is_absolute():
                supplied = Path.cwd() / supplied
            artifact_dir = supplied
        artifact_dir = _ensure_contained(artifact_dir, runs_root, "run artifact output")
        _reject_symlink_components(artifact_dir, stop=runs_root)
        if artifact_dir.exists():
            raise FileExistsError(
                f"Run artifact destination already exists: {artifact_dir}"
            )
        artifact_dir.parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(artifact_dir, stop=runs_root)
        staging_root = Path(
            tempfile.mkdtemp(
                prefix=f".{artifact_dir.name}.staging-",
                dir=artifact_dir.parent,
            )
        )
        staged_artifacts = staging_root / "bundle"
        try:
            run_local_experiment(
                reviewed_snapshot,
                model_paths=model_paths,
                artifact_dir=staged_artifacts,
            )
            _attach_verified_model_manifest(staged_artifacts, manifest_bytes)
            if artifact_dir.exists():
                raise FileExistsError(
                    f"Run artifact destination appeared during run: {artifact_dir}"
                )
            os.rename(staged_artifacts, artifact_dir)
        finally:
            if staging_root.exists():
                shutil.rmtree(staging_root)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Local experiment artifacts written under {artifact_dir}")


def _combination_experiment(
    *,
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    artifact_dir: Path,
    conversation_fixture: Path | None,
    staging_dir: Path | None,
    resume: bool,
) -> None:
    try:
        root = _local_root(local_root)
        snapshots_root = _category_dir(root, "snapshots")
        snapshot_path = _ensure_contained(Path(snapshot), snapshots_root, "snapshot")
        _reject_symlink_components(snapshot_path, stop=snapshots_root)
        if not snapshot_path.is_dir():
            raise ValueError("snapshot must be a directory beneath local/snapshots/")
        try:
            reviewed_snapshot = load_local_snapshot(snapshot_path)
        except ValueError as error:
            if "review_status='approved'" in str(error):
                raise ValueError(
                    "combination-experiment requires an approved snapshot"
                ) from error
            raise
        _validate_snapshot_approval(snapshot_path)
        model_paths, manifest_bytes = _resolve_model_paths_with_manifest(
            root,
            embedding_model_dir,
            reranker_model_dir,
        )
        _require_offline_inference_process()

        fixture_path = None
        if conversation_fixture is not None:
            fixture_path = _ensure_contained(
                Path(conversation_fixture), root, "conversation fixture"
            )
            _reject_symlink_components(fixture_path, stop=root)
            if not fixture_path.is_file():
                raise ValueError(
                    "conversation fixture must be a regular file beneath local-root"
                )

        runs_root = _category_dir(root, "runs")
        supplied_artifact = Path(artifact_dir).expanduser()
        if not supplied_artifact.is_absolute():
            supplied_artifact = Path.cwd() / supplied_artifact
        destination = _ensure_contained(
            supplied_artifact, runs_root, "combination artifact output"
        )
        _reject_symlink_components(destination, stop=runs_root)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"Combination artifact destination already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(destination, stop=runs_root)
        if resume:
            if staging_dir is None:
                raise ValueError("Resume requires a staging directory")
            supplied_staging = Path(staging_dir).expanduser()
            if not supplied_staging.is_absolute():
                supplied_staging = Path.cwd() / supplied_staging
            selected_staging = _ensure_contained(
                supplied_staging, runs_root, "combination staging directory"
            )
            _reject_symlink_components(selected_staging, stop=runs_root)
            if not selected_staging.is_dir():
                raise ValueError("combination staging directory does not exist")
            if not selected_staging.name.startswith(
                f".{destination.name}.staging-"
            ):
                raise ValueError("combination staging directory name does not match output")
        else:
            if staging_dir is not None:
                raise ValueError("Fresh combination runs cannot select a staging directory")
            selected_staging = destination.parent / (
                f".{destination.name}.staging-{uuid.uuid4().hex}"
            )
        click.echo(f"Combination staging directory: {selected_staging}")
        run_combination_experiment(
            reviewed_snapshot,
            model_paths=model_paths,
            artifact_dir=destination,
            conversation_fixture=fixture_path,
            staging_dir=selected_staging,
            resume=resume,
            verified_model_manifest_bytes=manifest_bytes,
        )
        _attach_verified_model_manifest(destination, manifest_bytes)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Local combination artifacts written under {destination}")


def _supplemental_baseline_experiment(
    *,
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    reference_artifact_dir: Path,
    artifact_dir: Path,
) -> None:
    try:
        root = _local_root(local_root)
        snapshots_root = _category_dir(root, "snapshots")
        snapshot_path = _ensure_contained(Path(snapshot), snapshots_root, "snapshot")
        _reject_symlink_components(snapshot_path, stop=snapshots_root)
        if not snapshot_path.is_dir():
            raise ValueError("snapshot must be a directory beneath local/snapshots/")
        reviewed_snapshot = load_local_snapshot(snapshot_path)
        _validate_snapshot_approval(snapshot_path)
        _model_paths, manifest_bytes = _resolve_model_paths_with_manifest(
            root,
            embedding_model_dir,
            reranker_model_dir,
        )

        runs_root = _category_dir(root, "runs")
        supplied_reference = Path(reference_artifact_dir).expanduser()
        if not supplied_reference.is_absolute():
            supplied_reference = Path.cwd() / supplied_reference
        reference_path = _ensure_contained(
            supplied_reference, runs_root, "reference run"
        )
        _reject_symlink_components(reference_path, stop=runs_root)
        if not reference_path.is_dir():
            raise ValueError("reference run must be a directory beneath local/runs/")
        reference_report = _decode_json(
            _read_regular_file(reference_path / "report.json", "reference report"),
            "reference report",
        )

        supplied_output = Path(artifact_dir).expanduser()
        if not supplied_output.is_absolute():
            supplied_output = Path.cwd() / supplied_output
        destination = _ensure_contained(supplied_output, runs_root, "artifact output")
        _reject_symlink_components(destination, stop=runs_root)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"Supplemental baseline destination already exists: {destination}"
            )
        run_supplemental_baseline(
            reviewed_snapshot,
            reference_report=reference_report,
            reference_artifact_dir=reference_path,
            verified_model_manifest_sha256=_sha256(manifest_bytes),
            artifact_dir=destination,
        )
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Supplemental baseline artifacts written under {destination}")


@main.command("combination-experiment")
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for snapshots, models, fixtures, and runs.",
)
@click.option(
    "--snapshot",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Approved snapshot beneath local/snapshots/.",
)
@click.option(
    "--embedding-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-m3 directory verified by local/models/model-manifest.json.",
)
@click.option(
    "--reranker-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-reranker-v2-m3 directory verified by the model manifest.",
)
@click.option(
    "--artifact-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="New artifact destination beneath local/runs/; existing paths are rejected.",
)
@click.option(
    "--conversation-fixture",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Optional separately reviewed conversation fixture beneath local/.",
)
def combination_experiment_command(
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    artifact_dir: Path,
    conversation_fixture: Path | None,
) -> None:
    """Run the fixed local combination, ablation, and conversation evaluations."""
    _combination_experiment(
        local_root=local_root,
        snapshot=snapshot,
        embedding_model_dir=embedding_model_dir,
        reranker_model_dir=reranker_model_dir,
        artifact_dir=artifact_dir,
        conversation_fixture=conversation_fixture,
        staging_dir=None,
        resume=False,
    )


@main.command("supplemental-baseline")
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for snapshots, models, and runs.",
)
@click.option(
    "--snapshot",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Approved snapshot beneath local/snapshots/.",
)
@click.option(
    "--embedding-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-m3 directory verified by the local model manifest.",
)
@click.option(
    "--reranker-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-reranker-v2-m3 directory verified by the local model manifest.",
)
@click.option(
    "--reference-artifact-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Completed v3 combination run beneath local/runs/.",
)
@click.option(
    "--artifact-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="New supplemental output destination beneath local/runs/.",
)
def supplemental_baseline_command(
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    reference_artifact_dir: Path,
    artifact_dir: Path,
) -> None:
    """Replay the lexical-first hybrid baseline against frozen v3 vector results."""
    _supplemental_baseline_experiment(
        local_root=local_root,
        snapshot=snapshot,
        embedding_model_dir=embedding_model_dir,
        reranker_model_dir=reranker_model_dir,
        reference_artifact_dir=reference_artifact_dir,
        artifact_dir=artifact_dir,
    )


@main.command("resume-combination-experiment")
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for snapshots, models, fixtures, and runs.",
)
@click.option(
    "--snapshot",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="The same approved snapshot used to start the run.",
)
@click.option(
    "--embedding-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-m3 directory verified by local/models/model-manifest.json.",
)
@click.option(
    "--reranker-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Local BAAI/bge-reranker-v2-m3 directory verified by the model manifest.",
)
@click.option(
    "--artifact-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Final artifact destination beneath local/runs/; existing paths are rejected.",
)
@click.option(
    "--staging-dir",
    type=click.Path(path_type=Path, file_okay=False, exists=True),
    required=True,
    help="Exact hidden staging directory printed when the original run started.",
)
@click.option(
    "--conversation-fixture",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="The same optional reviewed conversation fixture used to start the run.",
)
def resume_combination_experiment_command(
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    artifact_dir: Path,
    staging_dir: Path,
    conversation_fixture: Path | None,
) -> None:
    """Resume a combination run only when its checkpoint inputs still match."""
    _combination_experiment(
        local_root=local_root,
        snapshot=snapshot,
        embedding_model_dir=embedding_model_dir,
        reranker_model_dir=reranker_model_dir,
        artifact_dir=artifact_dir,
        conversation_fixture=conversation_fixture,
        staging_dir=staging_dir,
        resume=True,
    )


def _repack_combination_experiment(
    *,
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    source_staging_dir: Path,
    artifact_dir: Path,
) -> None:
    try:
        root = _local_root(local_root)
        snapshots_root = _category_dir(root, "snapshots")
        snapshot_path = _ensure_contained(Path(snapshot), snapshots_root, "snapshot")
        _reject_symlink_components(snapshot_path, stop=snapshots_root)
        if not snapshot_path.is_dir():
            raise ValueError("snapshot must be a directory beneath local/snapshots/")
        reviewed_snapshot = load_local_snapshot(snapshot_path)
        _validate_snapshot_approval(snapshot_path)
        model_paths, manifest_bytes = _resolve_model_paths_with_manifest(
            root,
            embedding_model_dir,
            reranker_model_dir,
        )
        _require_offline_inference_process()

        runs_root = _category_dir(root, "runs")
        source = _ensure_contained(
            Path(source_staging_dir), runs_root, "repack source staging directory"
        )
        _reject_symlink_components(source, stop=runs_root)
        if not source.is_dir():
            raise ValueError("repack source must be a staging directory beneath local/runs/")
        supplied_artifact = Path(artifact_dir).expanduser()
        if not supplied_artifact.is_absolute():
            supplied_artifact = Path.cwd() / supplied_artifact
        destination = _ensure_contained(
            supplied_artifact, runs_root, "combination repack output"
        )
        _reject_symlink_components(destination, stop=runs_root)
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"Combination repack destination already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(destination, stop=runs_root)
        click.echo(f"Combination repack source: {source}")
        repack_completed_combination_experiment(
            reviewed_snapshot,
            model_paths=model_paths,
            source_staging_dir=source,
            artifact_dir=destination,
            verified_model_manifest_bytes=manifest_bytes,
        )
        _attach_verified_model_manifest(destination, manifest_bytes)
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Local combination artifacts written under {destination}")


@main.command("repack-combination-experiment")
@click.option(
    "--local-root",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="Selected ignored local/ root for snapshots, models, fixtures, and runs.",
)
@click.option(
    "--snapshot",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="The approved snapshot used by the source run.",
)
@click.option(
    "--embedding-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="The locally verified BAAI/bge-m3 directory used by the source run.",
)
@click.option(
    "--reranker-model-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="The locally verified reranker directory used by the source run.",
)
@click.option(
    "--source-staging-dir",
    type=click.Path(path_type=Path, file_okay=False, exists=True),
    required=True,
    help="Complete hidden checkpointed run whose fingerprints and trace hashes will be verified.",
)
@click.option(
    "--artifact-dir",
    type=click.Path(path_type=Path, file_okay=False),
    required=True,
    help="New artifact destination beneath local/runs/.",
)
def repack_combination_experiment_command(
    local_root: Path,
    snapshot: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    source_staging_dir: Path,
    artifact_dir: Path,
) -> None:
    """Repack authenticated retrieval traces with the current budget policy."""
    _repack_combination_experiment(
        local_root=local_root,
        snapshot=snapshot,
        embedding_model_dir=embedding_model_dir,
        reranker_model_dir=reranker_model_dir,
        source_staging_dir=source_staging_dir,
        artifact_dir=artifact_dir,
    )


if __name__ == "__main__":
    main()
