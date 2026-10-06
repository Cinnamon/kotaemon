"""Strict reviewed conversation fixture schema and snapshot validation."""

from __future__ import annotations

import json
import math
import re
import stat
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .combination_artifacts import _sha256
from .local_snapshot import LocalSnapshot

CONVERSATION_FIXTURE_VERSION = 1

CONVERSATION_FIXTURE_FIELDS = {"schema_version", "reviewed", "cases"}

CONVERSATION_CASE_FIELDS = {"case_id", "turns"}

CONVERSATION_TURN_FIELDS = {
    "turn_id",
    "question",
    "allowed_source_ids",
    "expected_relevant_source_ids",
    "expected_anchors",
    "topic_switch",
    "no_answer",
    "path",
    "source_types",
    "filters",
}

CONVERSATION_ANCHOR_FIELDS = {
    "id",
    "source_id",
    "unit_id",
    "locator",
    "char_start",
    "char_end",
    "evidence_sha256",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_LABEL_KEYS = {
    "answer",
    "answer_support",
    "citation_precision",
    "disallowed_source_ids",
    "expected_anchors",
    "expected_relevant_source_ids",
    "gold",
    "judgment",
    "label",
    "no_answer",
    "relevant_ids",
    "topic_switch",
}


@dataclass(frozen=True)
class ConversationAnchor:
    id: str
    query_id: str
    source_id: str
    unit_id: str
    locator: Mapping[str, Any]
    char_start: int
    char_end: int
    evidence_sha256: str


@dataclass(frozen=True)
class ConversationTurn:
    turn_id: str
    question: str
    allowed_source_ids: tuple[str, ...] | None
    expected_relevant_source_ids: tuple[str, ...]
    expected_anchors: tuple[ConversationAnchor, ...]
    topic_switch: bool
    no_answer: bool
    path: str | None
    source_types: tuple[str, ...] | None
    filters: Mapping[str, str] | None


@dataclass(frozen=True)
class ConversationCase:
    case_id: str
    turns: tuple[ConversationTurn, ...]


@dataclass(frozen=True)
class ConversationFixture:
    schema_version: int
    reviewed: bool
    cases: tuple[ConversationCase, ...]
    digest: str
    source_name: str


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Conversation fixture contains duplicate field {key!r}")
        result[key] = value
    return result


def _read_fixture(path: Path) -> tuple[dict[str, Any], str]:
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Conversation fixture must not be a symlink")
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        raise ValueError("Conversation fixture does not exist") from error
    if not stat.S_ISREG(mode):
        raise ValueError("Conversation fixture must be a regular file")
    payload = path.read_bytes()
    digest = _sha256(payload)
    try:
        value = json.loads(
            payload.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Conversation fixture must be UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Conversation fixture must be a JSON object")
    return value, digest


def _exact_fields(value: Mapping[str, Any], fields: set[str], label: str) -> None:
    missing = fields - set(value)
    unknown = set(value) - fields
    if missing:
        raise ValueError(f"{label} is missing field(s): {sorted(missing)}")
    if unknown:
        raise ValueError(
            f"{label} has unknown or label-leaking field(s): {sorted(unknown)}"
        )


def _string_list(value: Any, label: str, *, allow_none: bool = False):
    if value is None and allow_none:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a list of non-empty strings")
    normalized = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label} must contain non-empty trimmed strings")
        normalized.append(item)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} contains duplicate IDs")
    return tuple(normalized)


def _valid_span(start: Any, end: Any, label: str) -> None:
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
    ):
        raise ValueError(f"{label} must be a non-empty half-open character span")


def _parse_conversation_anchor(value: Any, turn_id: str) -> ConversationAnchor:
    if not isinstance(value, Mapping):
        raise ValueError(f"Conversation turn {turn_id!r} anchors must be objects")
    _exact_fields(value, CONVERSATION_ANCHOR_FIELDS, "conversation anchor")
    for key in ("id", "source_id", "unit_id"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise ValueError(f"Conversation anchor {key} must be non-empty")
    locator = value["locator"]
    if not isinstance(locator, Mapping) or not locator:
        raise ValueError("Conversation anchor locator must be a non-empty object")
    _valid_span(value["char_start"], value["char_end"], "Conversation anchor span")
    digest = value["evidence_sha256"]
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise ValueError(
            "Conversation anchor evidence_sha256 must be lowercase SHA-256"
        )
    return ConversationAnchor(
        id=value["id"],
        query_id=turn_id,
        source_id=value["source_id"],
        unit_id=value["unit_id"],
        locator=dict(locator),
        char_start=value["char_start"],
        char_end=value["char_end"],
        evidence_sha256=digest,
    )


def load_conversation_fixture(path: str | Path) -> ConversationFixture:
    """Load a separately reviewed, immutable-ID conversation fixture (schema v1)."""
    source_path = Path(path)
    value, digest = _read_fixture(source_path)
    _exact_fields(value, CONVERSATION_FIXTURE_FIELDS, "conversation fixture")
    if (
        isinstance(value["schema_version"], bool)
        or value["schema_version"] != CONVERSATION_FIXTURE_VERSION
    ):
        raise ValueError("Conversation fixture schema_version must be 1")
    if value["reviewed"] is not True:
        raise ValueError("Conversation fixture must be explicitly reviewed")
    raw_cases = value["cases"]
    if (
        isinstance(raw_cases, (str, bytes))
        or not isinstance(raw_cases, Sequence)
        or not raw_cases
    ):
        raise ValueError("Conversation fixture cases must be a non-empty list")

    cases = []
    seen_case_ids: set[str] = set()
    seen_turn_ids: set[str] = set()
    seen_anchor_ids: set[str] = set()
    for case_index, raw_case in enumerate(raw_cases, 1):
        if not isinstance(raw_case, Mapping):
            raise ValueError(f"Conversation case {case_index} must be an object")
        _exact_fields(raw_case, CONVERSATION_CASE_FIELDS, "conversation case")
        case_id = raw_case["case_id"]
        if (
            not isinstance(case_id, str)
            or not case_id.strip()
            or case_id != case_id.strip()
        ):
            raise ValueError("Conversation case IDs must be non-empty and trimmed")
        if case_id in seen_case_ids:
            raise ValueError(
                f"Conversation fixture contains duplicate case ID {case_id!r}"
            )
        seen_case_ids.add(case_id)
        raw_turns = raw_case["turns"]
        if (
            isinstance(raw_turns, (str, bytes))
            or not isinstance(raw_turns, Sequence)
            or not raw_turns
        ):
            raise ValueError(f"Conversation case {case_id!r} needs at least one turn")
        turns = []
        for turn_index, raw_turn in enumerate(raw_turns, 1):
            if not isinstance(raw_turn, Mapping):
                raise ValueError(f"Conversation turn {turn_index} must be an object")
            _exact_fields(raw_turn, CONVERSATION_TURN_FIELDS, "conversation turn")
            turn_id = raw_turn["turn_id"]
            question = raw_turn["question"]
            if (
                not isinstance(turn_id, str)
                or not turn_id.strip()
                or turn_id != turn_id.strip()
                or turn_id in seen_turn_ids
            ):
                raise ValueError(
                    "Conversation turn IDs must be globally unique non-empty strings"
                )
            if (
                not isinstance(question, str)
                or not question.strip()
                or question != question.strip()
            ):
                raise ValueError(
                    f"Conversation turn {turn_id!r} question must be non-empty"
                )
            seen_turn_ids.add(turn_id)
            allowed_ids = _string_list(
                raw_turn["allowed_source_ids"],
                f"turn {turn_id!r} allowed_source_ids",
                allow_none=True,
            )
            relevant_ids = _string_list(
                raw_turn["expected_relevant_source_ids"],
                f"turn {turn_id!r} expected_relevant_source_ids",
            )
            if not isinstance(raw_turn["topic_switch"], bool) or not isinstance(
                raw_turn["no_answer"], bool
            ):
                raise ValueError(
                    f"Conversation turn {turn_id!r} labels must be booleans"
                )
            if turn_index == 1 and raw_turn["topic_switch"]:
                raise ValueError(
                    "The first turn in a conversation cannot be a topic switch"
                )
            if raw_turn["no_answer"] != (len(relevant_ids) == 0):
                raise ValueError(
                    f"Conversation turn {turn_id!r} no_answer must agree with its expected source labels"
                )
            raw_anchors = raw_turn["expected_anchors"]
            if isinstance(raw_anchors, (str, bytes)) or not isinstance(
                raw_anchors, Sequence
            ):
                raise ValueError(
                    f"Conversation turn {turn_id!r} expected_anchors must be a list"
                )
            anchors = tuple(
                _parse_conversation_anchor(anchor, turn_id) for anchor in raw_anchors
            )
            for anchor in anchors:
                if anchor.id in seen_anchor_ids:
                    raise ValueError(
                        f"Conversation fixture contains duplicate anchor ID {anchor.id!r}"
                    )
                seen_anchor_ids.add(anchor.id)
                if anchor.source_id not in relevant_ids:
                    raise ValueError(
                        "Conversation anchor source must be expected relevant"
                    )
            if raw_turn["no_answer"] and anchors:
                raise ValueError("No-answer turns cannot declare evidence anchors")

            path_value = raw_turn["path"]
            if path_value is not None:
                if not isinstance(path_value, str):
                    raise ValueError(
                        f"Conversation turn {turn_id!r} path must be a string or null"
                    )
                from kotaemon.indices.knowledge.planning.query_planner import (
                    normalize_logical_path,
                )

                path_value = normalize_logical_path(path_value)
            source_types = raw_turn["source_types"]
            if source_types is not None:
                source_types = _string_list(
                    source_types, f"turn {turn_id!r} source_types"
                )
                from kotaemon.indices.knowledge.schema import SUPPORTED_SOURCE_TYPES

                unsupported = set(source_types) - set(SUPPORTED_SOURCE_TYPES)
                if unsupported:
                    raise ValueError(
                        f"Conversation turn has unsupported source types: {sorted(unsupported)}"
                    )
            filters = raw_turn["filters"]
            if filters is not None:
                if not isinstance(filters, Mapping):
                    raise ValueError(
                        f"Conversation turn {turn_id!r} filters must be an object or null"
                    )
                if set(filters) & _LABEL_KEYS:
                    raise ValueError(
                        "Conversation filters cannot contain judgment-label fields"
                    )
                normalized_filters = {}
                for key, item in filters.items():
                    if (
                        not isinstance(key, str)
                        or not key.strip()
                        or key != key.strip()
                    ):
                        raise ValueError(
                            "Conversation filter keys must be non-empty trimmed strings"
                        )
                    if (
                        not isinstance(item, (str, int, float, bool))
                        or isinstance(item, float)
                        and not math.isfinite(item)
                    ):
                        raise ValueError(
                            "Conversation filter values must be finite scalar values"
                        )
                    normalized_filters[key] = str(item).strip()
                    if not normalized_filters[key]:
                        raise ValueError("Conversation filter values must not be empty")
                filters = normalized_filters
            turns.append(
                ConversationTurn(
                    turn_id=turn_id,
                    question=question,
                    allowed_source_ids=allowed_ids,
                    expected_relevant_source_ids=relevant_ids,
                    expected_anchors=anchors,
                    topic_switch=raw_turn["topic_switch"],
                    no_answer=raw_turn["no_answer"],
                    path=path_value,
                    source_types=source_types,
                    filters=filters,
                )
            )
        cases.append(ConversationCase(case_id=case_id, turns=tuple(turns)))
    return ConversationFixture(
        schema_version=CONVERSATION_FIXTURE_VERSION,
        reviewed=True,
        cases=tuple(cases),
        digest=digest,
        source_name=source_path.name,
    )


def validate_conversation_fixture_sources(
    fixture: ConversationFixture,
    *,
    known_source_ids: set[str] | frozenset[str],
) -> None:
    """Reject source references absent from the immutable snapshot."""
    if not isinstance(fixture, ConversationFixture) or not fixture.reviewed:
        raise ValueError(
            "Conversation fixture must be reviewed before source validation"
        )
    unknown_sources = set()
    for case in fixture.cases:
        for turn in case.turns:
            ids = set(turn.expected_relevant_source_ids)
            if turn.allowed_source_ids is not None:
                ids.update(turn.allowed_source_ids)
                if not set(turn.expected_relevant_source_ids).issubset(
                    set(turn.allowed_source_ids)
                ):
                    raise ValueError(
                        f"Conversation turn {turn.turn_id!r} has relevant sources outside its caller allowlist"
                    )
            ids.update(anchor.source_id for anchor in turn.expected_anchors)
            unknown_sources.update(ids - set(known_source_ids))
    if unknown_sources:
        raise ValueError(
            f"Conversation fixture references unknown source IDs: {sorted(unknown_sources)}"
        )


def _validate_conversation_fixture_snapshot(
    fixture: ConversationFixture, snapshot: LocalSnapshot
) -> None:
    source_ids = {source["source_id"] for source in snapshot.selected_sources}
    validate_conversation_fixture_sources(fixture, known_source_ids=source_ids)
    units = {unit["unit_id"]: unit for unit in snapshot.records["source_units"]}
    source_by_id = {source["source_id"]: source for source in snapshot.selected_sources}
    for case in fixture.cases:
        for turn in case.turns:
            _validate_snapshot_constraints(
                SimpleCase(
                    case_id=turn.turn_id,
                    query=turn.question,
                    path=turn.path,
                    source_types=turn.source_types,
                    filters=turn.filters,
                ),
                snapshot,
            )
            for anchor in turn.expected_anchors:
                unit = units.get(anchor.unit_id)
                if (
                    unit is None
                    or unit["source_id"] != anchor.source_id
                    or anchor.source_id not in source_by_id
                    or unit["locator"] != dict(anchor.locator)
                ):
                    raise ValueError(
                        "Conversation anchor does not match reviewed snapshot provenance"
                    )
                text = unit["normalized_text"]
                if anchor.char_end > len(text):
                    raise ValueError(
                        "Conversation anchor extends beyond its reviewed source unit"
                    )
                actual = _sha256(
                    text[anchor.char_start : anchor.char_end].encode("utf-8")
                )
                if actual != anchor.evidence_sha256:
                    raise ValueError(
                        "Conversation anchor digest does not match reviewed source text"
                    )


@dataclass(frozen=True)
class SimpleCase:
    case_id: str
    query: str
    path: str | None
    source_types: tuple[str, ...] | None
    filters: Mapping[str, Any] | None
    allowed_source_ids: tuple[str, ...] | None = None


def _validate_snapshot_constraints(case: Any, snapshot: LocalSnapshot) -> None:
    if case.path not in (None, "/"):
        raise ValueError(
            f"Query {case.case_id!r} requests a logical path absent from the approved snapshot metadata"
        )
    if case.filters:
        raise ValueError(
            f"Query {case.case_id!r} requests metadata filters absent from the approved snapshot metadata"
        )
    if case.source_types is not None:
        for source_type in case.source_types:
            if source_type not in {
                "markdown",
                "pdf",
                "excel",
                "other",
                "ppt",
                "faq",
                "code",
                "wiki",
            }:
                raise ValueError(
                    f"Query {case.case_id!r} requests an unsupported source type"
                )


def _reject_label_leaking_source_metadata(snapshot: LocalSnapshot) -> None:
    for table_name in ("sources", "source_units", "chunks"):
        rows = snapshot.records.get(table_name, ())
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError(f"Snapshot {table_name} contains malformed metadata")
            leaking = set(row) & _LABEL_KEYS
            if leaking:
                raise ValueError(
                    f"Snapshot {table_name} contains label-leaking metadata fields: {sorted(leaking)}"
                )
