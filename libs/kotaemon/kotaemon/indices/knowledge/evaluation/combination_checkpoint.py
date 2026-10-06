"""Atomic, fingerprint-bound checkpoints for local combination runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


_CHECKPOINT_NAME = "run-checkpoint.json"
_FINGERPRINT_NAMES = ("snapshot", "gold", "model", "model_manifest", "config")
_ARM_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(Path(path).expanduser()))


def _reject_symlink_components(path: Path) -> None:
    current = _absolute(path)
    while True:
        try:
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ValueError("Resume staging path contains a symlink")
        except FileNotFoundError:
            pass
        if current.parent == current:
            return
        current = current.parent


def _regular_file(path: Path, label: str) -> bytes:
    _reject_symlink_components(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise ValueError(f"Resume checkpoint is missing {label}") from error
    if not stat.S_ISREG(mode):
        raise ValueError(f"Resume checkpoint {label} is not a regular file")
    return path.read_bytes()


def _atomic_write(path: Path, payload: bytes) -> None:
    _reject_symlink_components(path.parent)
    if path.exists() or path.is_symlink():
        _reject_symlink_components(path)
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError("Resume checkpoint output is not a regular file")
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


def _validate_fingerprints(value: Any) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != set(_FINGERPRINT_NAMES):
        raise ValueError("Resume checkpoint fingerprints have an invalid schema")
    result = {}
    for name in _FINGERPRINT_NAMES:
        digest = value[name]
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise ValueError("Resume checkpoint contains an invalid fingerprint")
        result[name] = digest
    return result


def _validate_case_ids(value: Any) -> tuple[str, ...]:
    if (
        isinstance(value, (str, bytes))
        or not isinstance(value, Sequence)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ValueError("Resume checkpoint has an invalid query ID list")
    case_ids = tuple(value)
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Resume checkpoint contains duplicate query IDs")
    return case_ids


def _validate_arm_fingerprints(
    value: Any, *, allow_empty: bool = False
) -> dict[str, str]:
    if not isinstance(value, Mapping) or (not value and not allow_empty):
        raise ValueError("Resume checkpoint has an invalid arm configuration list")
    result = {}
    for arm, digest in value.items():
        if not isinstance(arm, str) or _ARM_RE.fullmatch(arm) is None:
            raise ValueError("Resume checkpoint contains an invalid arm name")
        if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
            raise ValueError("Resume checkpoint contains an invalid arm fingerprint")
        result[arm] = digest
    return result


class RunCheckpoint:
    """Persist and validate one combination run's private query outputs."""

    def __init__(self, root: Path, data: dict[str, Any]):
        self.root = root
        self._data = data

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        run_id: str,
        fingerprints: Mapping[str, str],
        case_ids: Sequence[str],
        arm_config_fingerprints: Mapping[str, str],
    ) -> "RunCheckpoint":
        path = _absolute(root)
        _reject_symlink_components(path)
        if path.exists():
            if not path.is_dir():
                raise ValueError("Resume staging path is not a directory")
            if any(path.iterdir()):
                raise FileExistsError("Resume staging directory is not empty")
        else:
            path.mkdir(parents=True)
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("Resume checkpoint requires a run ID")
        checked_fingerprints = _validate_fingerprints(fingerprints)
        checked_case_ids = _validate_case_ids(case_ids)
        checked_arms = _validate_arm_fingerprints(arm_config_fingerprints)
        data = {
            "schema_version": 1,
            "status": "running",
            "run_id": run_id,
            "fingerprints": checked_fingerprints,
            "case_ids": list(checked_case_ids),
            "arm_config_fingerprints": checked_arms,
            "effective_arm_config_fingerprints": {},
            "completed": [],
            "pending": None,
        }
        state = cls(path, data)
        state._save()
        return state

    @classmethod
    def resume(
        cls,
        root: str | Path,
        *,
        expected_fingerprints: Mapping[str, str],
        expected_case_ids: Sequence[str],
        expected_arm_config_fingerprints: Mapping[str, str],
    ) -> "RunCheckpoint":
        path = _absolute(root)
        _reject_symlink_components(path)
        if not path.is_dir():
            raise ValueError("Resume staging directory does not exist")
        checkpoint_path = path / _CHECKPOINT_NAME
        payload = _regular_file(checkpoint_path, "control file")
        try:
            data = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Resume checkpoint control file is invalid") from error
        if not isinstance(data, dict) or set(data) != {
            "schema_version",
            "status",
            "run_id",
            "fingerprints",
            "case_ids",
            "arm_config_fingerprints",
            "effective_arm_config_fingerprints",
            "completed",
            "pending",
        }:
            raise ValueError("Resume checkpoint control file has an invalid schema")
        if data.get("schema_version") != 1 or data.get("status") not in {
            "running",
            "complete",
        }:
            raise ValueError("Resume checkpoint control file has an unsupported version")
        if not isinstance(data.get("run_id"), str) or not data["run_id"]:
            raise ValueError("Resume checkpoint control file has an invalid run ID")

        actual_fingerprints = _validate_fingerprints(data.get("fingerprints"))
        expected = _validate_fingerprints(expected_fingerprints)
        if actual_fingerprints != expected:
            raise ValueError("Resume checkpoint fingerprint mismatch")
        actual_case_ids = _validate_case_ids(data.get("case_ids"))
        expected_cases = _validate_case_ids(expected_case_ids)
        if actual_case_ids != expected_cases:
            raise ValueError("Resume checkpoint query IDs do not match the snapshot")
        actual_arms = _validate_arm_fingerprints(
            data.get("arm_config_fingerprints")
        )
        expected_arms = _validate_arm_fingerprints(expected_arm_config_fingerprints)
        if actual_arms != expected_arms:
            raise ValueError("Resume checkpoint arm configuration fingerprint mismatch")
        effective_arms = _validate_arm_fingerprints(
            data.get("effective_arm_config_fingerprints"), allow_empty=True
        )
        if not set(effective_arms).issubset(actual_arms):
            raise ValueError("Resume checkpoint contains an unexpected effective arm")
        state = cls(path, data)
        state._validate_files_and_pending()
        return state

    @property
    def run_id(self) -> str:
        return self._data["run_id"]

    @property
    def fingerprints(self) -> Mapping[str, str]:
        return dict(self._data["fingerprints"])

    @property
    def case_ids(self) -> tuple[str, ...]:
        return tuple(self._data["case_ids"])

    @property
    def arm_names(self) -> tuple[str, ...]:
        return tuple(self._data["arm_config_fingerprints"])

    @property
    def effective_arm_config_fingerprints(self) -> Mapping[str, str]:
        return dict(self._data["effective_arm_config_fingerprints"])

    @property
    def pending(self) -> Mapping[str, Any] | None:
        value = self._data["pending"]
        return None if value is None else dict(value)

    @property
    def completed_keys(self) -> frozenset[tuple[str, int]]:
        return frozenset(
            (record["arm"], record["query_index"])
            for record in self._data["completed"]
        )

    @property
    def completed_records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(dict(record) for record in self._data["completed"])

    @property
    def is_complete(self) -> bool:
        return self._data["status"] == "complete"

    def artifact_entries(self) -> tuple[dict[str, Any], ...]:
        """Return digest entries for all persisted checkpoint outputs."""
        entries = []
        for record in self._data["completed"]:
            arm = record["arm"]
            index = record["query_index"]
            trace_path, summary_path = self._query_paths(arm, index)
            entries.extend(
                (
                    {
                        "path": trace_path.relative_to(self.root).as_posix(),
                        "sha256": record["trace_sha256"],
                        "size_bytes": record["trace_size_bytes"],
                        "kind": "private_query_trace",
                    },
                    {
                        "path": summary_path.relative_to(self.root).as_posix(),
                        "sha256": record["summary_sha256"],
                        "size_bytes": record["summary_size_bytes"],
                        "kind": "private_resume_query_summary",
                    },
                )
            )
        checkpoint_bytes = _regular_file(
            self.root / _CHECKPOINT_NAME, "control file"
        )
        entries.append(
            {
                "path": _CHECKPOINT_NAME,
                "sha256": _sha256(checkpoint_bytes),
                "size_bytes": len(checkpoint_bytes),
                "kind": "run_checkpoint",
            }
        )
        return tuple(entries)

    def _query_paths(self, arm: str, query_index: int) -> tuple[Path, Path]:
        return (
            self.root / "traces" / arm / f"query-{query_index:04d}.json",
            self.root
            / ".resume"
            / "rows"
            / arm
            / f"query-{query_index:04d}.json",
        )

    def _validate_key(self, arm: Any, query_index: Any, case_id: Any) -> None:
        if arm not in self._data["arm_config_fingerprints"]:
            raise ValueError("Resume checkpoint contains an unexpected arm")
        if (
            isinstance(query_index, bool)
            or not isinstance(query_index, int)
            or not 0 <= query_index < len(self._data["case_ids"])
        ):
            raise ValueError("Resume checkpoint query index is out of range")
        if case_id != self._data["case_ids"][query_index]:
            raise ValueError("Resume checkpoint arm/query ID binding is invalid")

    def _save(self) -> None:
        _atomic_write(
            self.root / _CHECKPOINT_NAME,
            _canonical_json(self._data) + b"\n",
        )

    def bind_arm_config(self, arm: str, fingerprint: str) -> None:
        """Bind one arm to its runtime-derived configuration before query reuse."""
        if arm not in self._data["arm_config_fingerprints"]:
            raise ValueError("Resume checkpoint contains an unexpected arm")
        if not isinstance(fingerprint, str) or _DIGEST_RE.fullmatch(fingerprint) is None:
            raise ValueError("Resume checkpoint contains an invalid effective arm configuration fingerprint")
        effective = self._data["effective_arm_config_fingerprints"]
        previous = effective.get(arm)
        if previous is not None and previous != fingerprint:
            raise ValueError("Resume checkpoint effective arm configuration fingerprint mismatch")
        if previous is None:
            effective[arm] = fingerprint
            self._save()

    def begin(self, arm: str, query_index: int, case_id: str) -> None:
        self._validate_key(arm, query_index, case_id)
        if arm not in self._data["effective_arm_config_fingerprints"]:
            raise ValueError("Resume checkpoint arm configuration is not bound")
        key = (arm, query_index)
        if key in self.completed_keys or self._data["pending"] is not None:
            raise ValueError("Resume checkpoint already has this query in progress")
        self._data["pending"] = {
            "arm": arm,
            "query_index": query_index,
            "case_id": case_id,
        }
        self._save()

    def complete(
        self,
        arm: str,
        query_index: int,
        case_id: str,
        *,
        trace: Mapping[str, Any],
        summary: Mapping[str, Any],
    ) -> None:
        self._validate_key(arm, query_index, case_id)
        pending = self._data["pending"]
        if pending != {
            "arm": arm,
            "query_index": query_index,
            "case_id": case_id,
        }:
            raise ValueError("Resume checkpoint query was not marked in progress")
        if not isinstance(trace, Mapping) or not isinstance(summary, Mapping):
            raise ValueError("Resume checkpoint query outputs must be mappings")
        if summary.get("case_id") != case_id:
            raise ValueError("Resume checkpoint summary has the wrong query ID")
        trace_path, summary_path = self._query_paths(arm, query_index)
        trace_bytes = _canonical_json(trace) + b"\n"
        summary_bytes = _canonical_json(summary) + b"\n"
        _atomic_write(trace_path, trace_bytes)
        _atomic_write(summary_path, summary_bytes)
        self._data["completed"].append(
            {
                "arm": arm,
                "query_index": query_index,
                "case_id": case_id,
                "trace_sha256": _sha256(trace_bytes),
                "trace_size_bytes": len(trace_bytes),
                "summary_sha256": _sha256(summary_bytes),
                "summary_size_bytes": len(summary_bytes),
            }
        )
        self._data["pending"] = None
        self._save()

    def read(self, arm: str, query_index: int) -> tuple[dict[str, Any], dict[str, Any]]:
        record = next(
            (
                item
                for item in self._data["completed"]
                if item["arm"] == arm and item["query_index"] == query_index
            ),
            None,
        )
        if record is None:
            raise ValueError("Resume checkpoint query is incomplete")
        trace_path, summary_path = self._query_paths(arm, query_index)
        trace_bytes = _regular_file(trace_path, "query trace")
        summary_bytes = _regular_file(summary_path, "query summary")
        if (
            len(trace_bytes) != record["trace_size_bytes"]
            or _sha256(trace_bytes) != record["trace_sha256"]
            or len(summary_bytes) != record["summary_size_bytes"]
            or _sha256(summary_bytes) != record["summary_sha256"]
        ):
            raise ValueError("Resume checkpoint artifact digest mismatch")
        try:
            trace = json.loads(trace_bytes)
            summary = json.loads(summary_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Resume checkpoint query artifact is invalid") from error
        if (
            not isinstance(trace, dict)
            or not isinstance(summary, dict)
            or summary.get("case_id") != record["case_id"]
        ):
            raise ValueError("Resume checkpoint query artifact has an invalid schema")
        return trace, summary

    def finish(self) -> None:
        expected = {
            (arm, index)
            for arm in self.arm_names
            for index in range(len(self.case_ids))
        }
        if (
            self._data["pending"] is not None
            or self.completed_keys != expected
            or set(self._data["effective_arm_config_fingerprints"])
            != set(self.arm_names)
        ):
            raise ValueError("Resume checkpoint does not contain every query trace")
        self._data["status"] = "complete"
        self._save()

    def _validate_files_and_pending(self) -> None:
        completed = self._data.get("completed")
        if not isinstance(completed, list):
            raise ValueError("Resume checkpoint completed-query list is invalid")
        seen: set[tuple[str, int]] = set()
        expected_paths = {Path(_CHECKPOINT_NAME)}
        for record in completed:
            if not isinstance(record, dict) or set(record) != {
                "arm",
                "query_index",
                "case_id",
                "trace_sha256",
                "trace_size_bytes",
                "summary_sha256",
                "summary_size_bytes",
            }:
                raise ValueError("Resume checkpoint contains an invalid query record")
            arm = record["arm"]
            query_index = record["query_index"]
            case_id = record["case_id"]
            self._validate_key(arm, query_index, case_id)
            key = (arm, query_index)
            if key in seen:
                raise ValueError("Resume checkpoint contains duplicate query traces")
            if arm not in self._data["effective_arm_config_fingerprints"]:
                raise ValueError("Resume checkpoint query arm configuration is not bound")
            seen.add(key)
            for name in ("trace_sha256", "summary_sha256"):
                if (
                    not isinstance(record[name], str)
                    or _DIGEST_RE.fullmatch(record[name]) is None
                ):
                    raise ValueError("Resume checkpoint contains an invalid artifact digest")
            for name in ("trace_size_bytes", "summary_size_bytes"):
                if (
                    isinstance(record[name], bool)
                    or not isinstance(record[name], int)
                    or record[name] <= 0
                ):
                    raise ValueError("Resume checkpoint contains an invalid artifact size")
            trace_path, summary_path = self._query_paths(arm, query_index)
            for artifact_path, label in (
                (trace_path, "query trace"),
                (summary_path, "query summary"),
            ):
                expected_paths.add(artifact_path.relative_to(self.root))
                payload = _regular_file(artifact_path, label)
                digest_key = "trace_sha256" if label == "query trace" else "summary_sha256"
                size_key = "trace_size_bytes" if label == "query trace" else "summary_size_bytes"
                if len(payload) != record[size_key] or _sha256(payload) != record[digest_key]:
                    raise ValueError("Resume checkpoint artifact digest mismatch")

        pending = self._data.get("pending")
        pending_key: tuple[str, int] | None = None
        if pending is not None:
            if not isinstance(pending, dict) or set(pending) != {
                "arm",
                "query_index",
                "case_id",
            }:
                raise ValueError("Resume checkpoint pending-query record is invalid")
            self._validate_key(
                pending.get("arm"),
                pending.get("query_index"),
                pending.get("case_id"),
            )
            if pending["arm"] not in self._data["effective_arm_config_fingerprints"]:
                raise ValueError("Resume checkpoint pending arm configuration is not bound")
            pending_key = (pending["arm"], pending["query_index"])
            if pending_key in seen:
                raise ValueError("Resume checkpoint query is both pending and complete")
            pending_paths = self._query_paths(*pending_key)
            for artifact_path in pending_paths:
                expected_paths.add(artifact_path.relative_to(self.root))
                if artifact_path.exists() or artifact_path.is_symlink():
                    _regular_file(artifact_path, "pending query artifact")

        if self._data["status"] == "complete":
            expected = {
                (arm, index)
                for arm in self.arm_names
                for index in range(len(self.case_ids))
            }
            if (
                pending is not None
                or seen != expected
                or set(self._data["effective_arm_config_fingerprints"])
                != set(self.arm_names)
            ):
                raise ValueError("Completed resume checkpoint is incomplete")

        self._reject_unexpected_files(expected_paths)

        if pending_key is not None:
            for artifact_path in self._query_paths(*pending_key):
                if artifact_path.exists():
                    artifact_path.unlink()
            self._data["pending"] = None
            self._save()

    def _reject_unexpected_files(self, expected_paths: set[Path]) -> None:
        expected_paths = {
            *expected_paths,
            Path("report.json"),
            Path("artifact-manifest.json"),
            Path("model-manifest.json"),
            Path("conversation/final-config.jsonl"),
            *(Path("generation-inputs") / f"{arm}.jsonl" for arm in self.arm_names),
        }
        actual_files: set[Path] = set()
        actual_directories: set[Path] = set()
        temporary_files: list[Path] = []
        expected_parents: set[Path] = set()
        for relative in expected_paths:
            parent = relative.parent
            while parent != Path("."):
                expected_parents.add(parent)
                parent = parent.parent

        for current, directories, files in os.walk(self.root, followlinks=False):
            current_path = Path(current)
            for name in directories:
                candidate = current_path / name
                if candidate.is_symlink():
                    raise ValueError("Resume staging tree contains a symlink")
                actual_directories.add(candidate.relative_to(self.root))
            for name in files:
                candidate = current_path / name
                if candidate.is_symlink():
                    raise ValueError("Resume staging tree contains a symlink")
                relative = candidate.relative_to(self.root)
                if relative in expected_paths:
                    actual_files.add(relative)
                    continue
                target_parent = relative.parent
                temp_matches = (
                    relative.name.startswith(".")
                    and relative.name.endswith(".tmp")
                    and any(
                        relative.name.startswith(f".{known.name}.")
                        for known in expected_paths
                        if known.parent == target_parent
                    )
                )
                if temp_matches and stat.S_ISREG(candidate.lstat().st_mode):
                    temporary_files.append(candidate)
                    continue
                raise ValueError("Resume staging tree contains unexpected artifacts")
        if not actual_files.issubset(expected_paths) or not actual_directories.issubset(
            expected_parents
        ):
            raise ValueError("Resume staging tree contains unexpected artifacts")
        for path in temporary_files:
            path.unlink()
