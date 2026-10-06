"""Generated-fixture tests for immutable local snapshot validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from kotaemon.indices.knowledge.evaluation.local_snapshot import load_local_snapshot


SOURCE_BYTES = b"generated source bytes; never read a real local source"
SOURCE_ID = hashlib.sha256(SOURCE_BYTES).hexdigest()
SOURCE_ROOT = "libs/kotaemon/tests/fixtures/knowledge_eval/local/sources"
NORMALIZED_TEXT = "Start. This is the cited passage. End."
LOCATOR = {"page_label": "1"}


def _json_bytes(value):
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )


def _jsonl_bytes(rows):
    return b"".join(_json_bytes(row) for row in rows)


def _source_record():
    return {
        "source_id": SOURCE_ID,
        "relative_path": "notes.md",
        "sha256": SOURCE_ID,
        "suffix": ".md",
        "byte_size": len(SOURCE_BYTES),
        "duplicate_of": None,
        "selected_reader": "TxtReader",
        "reader_attempts": ["TxtReader"],
        "reader_fallback_used": False,
        "reader_granularity": "document",
        "status": "parsed",
    }


def _unit_record():
    return {
        "unit_id": "unit-1",
        "source_id": SOURCE_ID,
        "relative_path": "notes.md",
        "unit_ordinal": 0,
        "locator": dict(LOCATOR),
        "text": NORMALIZED_TEXT,
        "normalized_text": NORMALIZED_TEXT,
    }


def _chunk_record():
    return {
        "chunk_id": "chunk-1",
        "source_id": SOURCE_ID,
        "relative_path": "notes.md",
        "unit_id": "unit-1",
        "unit_ordinal": 0,
        "chunk_ordinal": 0,
        "locator": dict(LOCATOR),
        "text": NORMALIZED_TEXT,
        "char_start": 0,
        "char_end": len(NORMALIZED_TEXT),
    }


def _empty_quality():
    return {
        "empty_locators": [],
        "unusable_locators": [],
        "reader_diagnostics": [],
        "extraction_failures": [],
        "chunk_mapping_issues": [],
        "pages": [],
        "sheets": [],
    }


def _judgment(case_id="q-1", relevant_ids=None, **overrides):
    row = {
        "schema_version": 1,
        "id": case_id,
        "query": "What does the generated note say?",
        "judgment_level": "source",
        "relevant_ids": [SOURCE_ID] if relevant_ids is None else relevant_ids,
        "disallowed_source_ids": [],
        "allowed_source_ids": [SOURCE_ID],
        "path": None,
        "source_types": None,
        "filters": None,
        "case_kind": "named",
    }
    row.update(overrides)
    return row


def _anchor(**overrides):
    start = NORMALIZED_TEXT.index("This")
    end = NORMALIZED_TEXT.index(" passage.")
    row = {
        "schema_version": 1,
        "id": "anchor-1",
        "query_id": "q-1",
        "source_id": SOURCE_ID,
        "source_sha256": SOURCE_ID,
        "unit_id": "unit-1",
        "locator": dict(LOCATOR),
        "char_start": start,
        "char_end": end,
        "evidence_sha256": hashlib.sha256(
            NORMALIZED_TEXT[start:end].encode("utf-8")
        ).hexdigest(),
    }
    row.update(overrides)
    return row


def _records(sources=None, units=None, chunks=None):
    return {
        "schema_version": 1,
        "parser_configuration": {".md": "TxtReader"},
        "splitter_configuration": {
            "version": "main-token-only-v1",
            "name": "TokenSplitter",
            "chunk_size": 1024,
            "chunk_overlap": 256,
            "separator": "\n\n",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
        "sources": [_source_record()] if sources is None else sources,
        "source_units": [_unit_record()] if units is None else units,
        "chunks": [_chunk_record()] if chunks is None else chunks,
        "topic_candidates": [],
        "topic_review_source_ids": [],
        "quality": _empty_quality(),
        "excluded_inputs": [],
    }


def _topic_candidate(**overrides):
    candidate = {
        "candidate_id": "topic-1",
        "source_id": SOURCE_ID,
        "relative_path": "notes.md",
        "unit_id": "unit-1",
        "text": "Evidence heading",
        "locator": dict(LOCATOR),
        "needs_review": True,
    }
    candidate.update(overrides)
    return candidate


def _load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_manifest(root, manifest):
    (root / "manifest.json").write_bytes(_json_bytes(manifest))


def _refresh_manifest(root):
    """Rebind manifest metadata after a semantic payload mutation."""
    records = json.loads((root / "records.json").read_bytes())
    judgments = _load_jsonl(root / "judgments.jsonl")
    anchors = _load_jsonl(root / "anchors.jsonl")
    indexed_source_ids = {chunk["source_id"] for chunk in records["chunks"]}
    manifest = json.loads((root / "manifest.json").read_bytes())
    manifest["payload_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("records.json", "judgments.jsonl", "anchors.jsonl")
    }
    manifest["source_provenance"] = [
        {
            "source_id": source["source_id"],
            "repository_path": f'{manifest["source_root"]}/{source["relative_path"]}',
            "sha256": source["sha256"],
        }
        for source in records["sources"]
    ]
    manifest["parser_configuration"] = records["parser_configuration"]
    manifest["splitter_configuration"] = records["splitter_configuration"]
    manifest["counts"] = {
        "source_paths": len(records["sources"]),
        "documents": sum(
            source["duplicate_of"] is None
            and source["status"] == "parsed"
            and source["source_id"] in indexed_source_ids
            for source in records["sources"]
        ),
        "source_units": len(records["source_units"]),
        "chunks": len(records["chunks"]),
        "queries": len(judgments),
        "anchors": len(anchors),
    }
    _write_manifest(root, manifest)


def _replace_payload(root, name, payload):
    (root / name).write_bytes(payload)
    _refresh_manifest(root)


def _set_records(root, records):
    _replace_payload(root, "records.json", _json_bytes(records))


def _set_judgments(root, judgments):
    _replace_payload(root, "judgments.jsonl", _jsonl_bytes(judgments))


def _set_anchors(root, anchors):
    _replace_payload(root, "anchors.jsonl", _jsonl_bytes(anchors))


def _other_source():
    source_bytes = b"another generated source, never a real local source"
    source_id = hashlib.sha256(source_bytes).hexdigest()
    source = {
        "source_id": source_id,
        "relative_path": "other.md",
        "sha256": source_id,
        "suffix": ".md",
        "byte_size": len(source_bytes),
        "duplicate_of": None,
        "selected_reader": "TxtReader",
        "reader_attempts": ["TxtReader"],
        "reader_fallback_used": False,
        "reader_granularity": "document",
        "status": "parsed",
    }
    text = "An unrelated source unit."
    unit = {
        "unit_id": "unit-2",
        "source_id": source_id,
        "relative_path": "other.md",
        "unit_ordinal": 0,
        "locator": {"page_label": "2"},
        "text": text,
        "normalized_text": text,
    }
    chunk = {
        "chunk_id": "chunk-2",
        "source_id": source_id,
        "relative_path": "other.md",
        "unit_id": "unit-2",
        "unit_ordinal": 0,
        "chunk_ordinal": 0,
        "locator": {"page_label": "2"},
        "text": text,
        "char_start": 0,
        "char_end": len(text),
    }
    return source, unit, chunk


@pytest.fixture
def reviewed_snapshot(tmp_path):
    root = tmp_path / "reviewed-v1"
    root.mkdir()
    records = _records()
    judgments = [_judgment()]
    anchors = [_anchor()]
    payloads = {
        "records.json": _json_bytes(records),
        "judgments.jsonl": _jsonl_bytes(judgments),
        "anchors.jsonl": _jsonl_bytes(anchors),
    }
    for name, payload in payloads.items():
        (root / name).write_bytes(payload)
    manifest = {
        "schema_version": 1,
        "snapshot_version": root.name,
        "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
        "payload_sha256": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in payloads.items()
        },
        "review_status": "approved",
        "review_date": "2026-10-03",
        "source_root": SOURCE_ROOT,
        "source_provenance": [
            {
                "source_id": SOURCE_ID,
                "repository_path": f"{SOURCE_ROOT}/notes.md",
                "sha256": SOURCE_ID,
            }
        ],
        "parser_configuration": records["parser_configuration"],
        "splitter_configuration": records["splitter_configuration"],
        "counts": {
            "source_paths": 1,
            "documents": 1,
            "source_units": 1,
            "chunks": 1,
            "queries": 1,
            "anchors": 1,
        },
    }
    _write_manifest(root, manifest)
    return root


def test_load_local_snapshot_returns_verified_source_level_snapshot(reviewed_snapshot):
    snapshot = load_local_snapshot(reviewed_snapshot)

    assert snapshot.root == reviewed_snapshot
    assert [source["source_id"] for source in snapshot.sources] == [SOURCE_ID]
    assert snapshot.judgments.schema_version == 1
    assert [case.case_id for case in snapshot.judgments.cases] == ["q-1"]
    assert [anchor.id for anchor in snapshot.anchors] == ["anchor-1"]
    assert (
        snapshot.fingerprint
        == hashlib.sha256(
            (reviewed_snapshot / "manifest.json").read_bytes()
        ).hexdigest()
    )


def test_load_local_snapshot_rejects_missing_payload(reviewed_snapshot):
    (reviewed_snapshot / "anchors.jsonl").unlink()

    with pytest.raises(ValueError, match="anchors.jsonl.*missing"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_changed_payload_bytes(reviewed_snapshot):
    path = reviewed_snapshot / "anchors.jsonl"
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="anchors.jsonl.*hash"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_requires_approval_by_default(reviewed_snapshot):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    manifest["review_status"] = "draft"
    manifest["review_date"] = None
    _write_manifest(reviewed_snapshot, manifest)

    with pytest.raises(ValueError, match="approved"):
        load_local_snapshot(reviewed_snapshot)


def test_unreviewed_snapshot_can_be_inspected_without_approval(reviewed_snapshot):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    manifest["review_status"] = "draft"
    manifest["review_date"] = None
    _write_manifest(reviewed_snapshot, manifest)

    snapshot = load_local_snapshot(reviewed_snapshot, require_reviewed=False)

    assert snapshot.judgments.cases[0].case_id == "q-1"


def test_returned_judgment_filters_are_immutable(reviewed_snapshot):
    _set_judgments(
        reviewed_snapshot,
        [_judgment(filters={"topic": "generated"})],
    )

    snapshot = load_local_snapshot(reviewed_snapshot)

    with pytest.raises(TypeError):
        snapshot.judgments.cases[0].filters["topic"] = "changed"


def test_topic_review_source_ids_reject_unknown_source(reviewed_snapshot):
    records = _records()
    records["topic_review_source_ids"] = ["f" * 64]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="topic_review_source_ids.*unknown"):
        load_local_snapshot(reviewed_snapshot)


def test_topic_review_source_ids_reject_duplicate_ids(reviewed_snapshot):
    records = _records()
    records["topic_review_source_ids"] = [SOURCE_ID, SOURCE_ID]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="topic_review_source_ids.*duplicate"):
        load_local_snapshot(reviewed_snapshot)


def test_topic_review_source_ids_reject_malformed_digest(reviewed_snapshot):
    records = _records()
    records["topic_review_source_ids"] = ["not-a-hash"]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="SHA-256 digest for topic_review_source_ids"):
        load_local_snapshot(reviewed_snapshot)


def test_topic_review_source_ids_must_be_selected_canonical_sources(reviewed_snapshot):
    records = _records()
    other_source, _, _ = _other_source()
    other_source["status"] = "not_selected"
    duplicate = dict(other_source)
    duplicate.update(
        relative_path="zz-other.md",
        duplicate_of="other.md",
        status="duplicate_bytes",
        selected_reader=None,
        reader_attempts=[],
        reader_granularity=None,
    )
    records["sources"].extend([other_source, duplicate])
    records["topic_review_source_ids"] = [other_source["source_id"]]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="topic_review_source_ids.*selected canonical"):
        load_local_snapshot(reviewed_snapshot)


def test_topic_review_source_ids_allow_selected_failed_source(reviewed_snapshot):
    records = _records()
    other_source, _, _ = _other_source()
    other_source["status"] = "failed"
    records["sources"].append(other_source)
    records["topic_review_source_ids"] = [other_source["source_id"]]
    _set_records(reviewed_snapshot, records)

    snapshot = load_local_snapshot(reviewed_snapshot)

    assert snapshot.records["topic_review_source_ids"] == (other_source["source_id"],)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"source_id": "f" * 64}, "unknown Source ID"),
        ({"unit_id": "unknown-unit"}, "unknown source unit"),
        ({"relative_path": "other.md"}, "path does not match"),
        ({"locator": {"page_label": "2"}}, "locator does not match"),
    ],
)
def test_topic_candidates_must_resolve_to_source_units(
    reviewed_snapshot, mutation, message
):
    records = _records()
    records["topic_candidates"] = [_topic_candidate(**mutation)]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


def test_topic_candidates_allow_a_heading_locator_with_unit_provenance(
    reviewed_snapshot,
):
    records = _records()
    records["topic_candidates"] = [
        _topic_candidate(locator={**LOCATOR, "heading_line": 3})
    ]
    _set_records(reviewed_snapshot, records)

    snapshot = load_local_snapshot(reviewed_snapshot)

    assert snapshot.records["topic_candidates"][0]["locator"]["heading_line"] == 3


def test_quality_source_provenance_must_resolve_to_a_source_record(reviewed_snapshot):
    records = _records()
    records["quality"]["extraction_failures"] = [
        {
            "relative_path": "notes.md",
            "source_id": "f" * 64,
            "error_type": "SyntheticError",
            "reason": "reader_failed",
        }
    ]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="quality.*Source ID"):
        load_local_snapshot(reviewed_snapshot)


def test_excluded_input_source_provenance_must_resolve_to_a_source_record(
    reviewed_snapshot,
):
    records = _records()
    records["excluded_inputs"] = [
        {
            "relative_path": "ghost.md",
            "source_id": "f" * 64,
            "reason": "not_selected",
            "duplicate_of": None,
        }
    ]
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="excluded_inputs.*source path"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("missing", "exactly"),
        ("extra", "exactly"),
        ("malformed", "SHA-256"),
    ],
)
def test_load_local_snapshot_validates_exact_payload_hash_map(
    reviewed_snapshot, mutation, message
):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    if mutation == "missing":
        del manifest["payload_sha256"]["anchors.jsonl"]
    elif mutation == "extra":
        manifest["payload_sha256"]["unexpected.json"] = "0" * 64
    else:
        manifest["payload_sha256"]["anchors.jsonl"] = "z" * 64
    _write_manifest(reviewed_snapshot, manifest)

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_chunk_level_judgments(reviewed_snapshot):
    _set_judgments(
        reviewed_snapshot,
        [_judgment(judgment_level="chunk", relevant_ids=["chunk-1"])],
    )

    with pytest.raises(ValueError, match="source-level"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_mixed_judgment_levels(reviewed_snapshot):
    _set_judgments(
        reviewed_snapshot,
        [
            _judgment(),
            _judgment("q-2", judgment_level="chunk", relevant_ids=["chunk-1"]),
        ],
    )

    with pytest.raises(ValueError, match="mixed judgment levels"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "field, ids, label",
    [
        ("relevant_ids", ["unknown-source"], "Unknown Source ID"),
        ("allowed_source_ids", ["unknown-source"], "Unknown allowed Source ID"),
        (
            "disallowed_source_ids",
            ["unknown-source"],
            "Unknown disallowed Source ID",
        ),
    ],
)
def test_load_local_snapshot_rejects_unknown_judgment_source_ids(
    reviewed_snapshot, field, ids, label
):
    _set_judgments(reviewed_snapshot, [_judgment(**{field: ids})])

    with pytest.raises(ValueError, match=label):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_resolves_judgments_only_against_selected_sources(
    reviewed_snapshot,
):
    records = _records()
    other_source, _, _ = _other_source()
    other_source["status"] = "not_selected"
    records["sources"].append(other_source)
    _set_records(reviewed_snapshot, records)
    _set_judgments(
        reviewed_snapshot,
        [
            _judgment(
                relevant_ids=[other_source["source_id"]],
                allowed_source_ids=[other_source["source_id"]],
            )
        ],
    )

    with pytest.raises(ValueError, match="Unknown Source ID"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize("status", ["failed", "not_selected"])
def test_load_local_snapshot_rejects_judgments_for_nonparsed_sources(
    reviewed_snapshot, status
):
    records = _records()
    records["sources"][0]["status"] = status
    records["source_units"] = []
    records["chunks"] = []
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="Unknown Source ID"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_judgments_for_source_without_chunks(
    reviewed_snapshot,
):
    records = _records(chunks=[])
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="Unknown Source ID"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_relevant_disallowed_overlap(reviewed_snapshot):
    _set_judgments(
        reviewed_snapshot,
        [_judgment(disallowed_source_ids=[SOURCE_ID])],
    )

    with pytest.raises(ValueError, match="both relevant and disallowed"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_inconsistent_allowed_scope(reviewed_snapshot):
    _set_judgments(reviewed_snapshot, [_judgment(allowed_source_ids=[])])

    with pytest.raises(ValueError, match="not in allowed"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_allowed_disallowed_overlap(reviewed_snapshot):
    records = _records()
    other_source, other_unit, other_chunk = _other_source()
    records["sources"].append(other_source)
    records["source_units"].append(other_unit)
    records["chunks"].append(other_chunk)
    _set_records(reviewed_snapshot, records)
    _set_judgments(
        reviewed_snapshot,
        [
            _judgment(
                relevant_ids=[other_source["source_id"]],
                allowed_source_ids=[SOURCE_ID],
                disallowed_source_ids=[SOURCE_ID],
            )
        ],
    )

    with pytest.raises(ValueError, match="both allowed and disallowed"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"query_id": "unknown-query"}, "Unknown query"),
        ({"source_id": "f" * 64, "source_sha256": "f" * 64}, "Unknown Source ID"),
        ({"unit_id": "unknown-unit"}, "Unknown source unit"),
    ],
)
def test_load_local_snapshot_rejects_unknown_anchor_relations(
    reviewed_snapshot, mutation, message
):
    _set_anchors(reviewed_snapshot, [_anchor(**mutation)])

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_requires_anchor_for_every_relevant_pair(reviewed_snapshot):
    _set_anchors(reviewed_snapshot, [])

    with pytest.raises(ValueError, match="missing evidence anchor"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_anchor_for_irrelevant_source(reviewed_snapshot):
    records = _records()
    other_source, other_unit, other_chunk = _other_source()
    records["sources"].append(other_source)
    records["source_units"].append(other_unit)
    records["chunks"].append(other_chunk)
    _set_records(reviewed_snapshot, records)
    _set_anchors(
        reviewed_snapshot,
        [
            _anchor(
                source_id=other_source["source_id"],
                source_sha256=other_source["sha256"],
                unit_id=other_unit["unit_id"],
                locator=other_unit["locator"],
                char_start=0,
                char_end=2,
                evidence_sha256=hashlib.sha256(b"An").hexdigest(),
            )
        ],
    )

    with pytest.raises(ValueError, match="not relevant to query"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_duplicate_anchor_ids(reviewed_snapshot):
    _set_anchors(reviewed_snapshot, [_anchor(), _anchor()])

    with pytest.raises(ValueError, match="duplicate anchor ID"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ({"char_start": 10, "char_end": 10}, "non-empty evidence span"),
        (
            {
                "char_start": len(NORMALIZED_TEXT) + 1,
                "char_end": len(NORMALIZED_TEXT) + 2,
            },
            "outside normalized source unit",
        ),
        ({"evidence_sha256": "0" * 64}, "evidence SHA-256 mismatch"),
        ({"locator": {"page_label": "99"}}, "locator does not match"),
        ({"source_sha256": "0" * 64}, "source SHA-256 mismatch"),
    ],
)
def test_load_local_snapshot_validates_anchor_span_and_provenance(
    reviewed_snapshot, mutation, message
):
    _set_anchors(reviewed_snapshot, [_anchor(**mutation)])

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "relative_path, message",
    [
        ("../notes.md", "parent traversal"),
        ("folder\\notes.md", "backslash"),
        ("/absolute/notes.md", "relative"),
    ],
)
def test_load_local_snapshot_rejects_unsafe_source_paths(
    reviewed_snapshot, relative_path, message
):
    records = _records()
    records["sources"][0]["relative_path"] = relative_path
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_source_id_that_does_not_match_digest(
    reviewed_snapshot,
):
    records = _records()
    records["sources"][0]["source_id"] = "f" * 64
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="source_id.*SHA-256"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_malformed_source_digest(reviewed_snapshot):
    records = _records()
    records["sources"][0]["sha256"] = "z" * 64
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="invalid SHA-256"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_duplicate_canonical_source_ids(reviewed_snapshot):
    records = _records()
    duplicate = _source_record()
    duplicate["relative_path"] = "other.md"
    records["sources"].append(duplicate)
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="duplicate canonical source ID"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_mismatched_duplicate_provenance(reviewed_snapshot):
    records = _records()
    duplicate = _source_record()
    duplicate["relative_path"] = "zz-copy.md"
    duplicate["duplicate_of"] = "missing.md"
    duplicate["status"] = "duplicate_bytes"
    records["sources"].append(duplicate)
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="duplicate_of.*canonical source path"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_accepts_consistent_duplicate_byte_provenance(
    reviewed_snapshot,
):
    records = _records()
    duplicate = _source_record()
    duplicate.update(
        relative_path="zz-copy.pdf",
        suffix=".pdf",
        duplicate_of="notes.md",
        selected_reader=None,
        reader_attempts=[],
        reader_granularity=None,
        status="duplicate_bytes",
    )
    records["sources"].append(duplicate)
    _set_records(reviewed_snapshot, records)

    snapshot = load_local_snapshot(reviewed_snapshot)

    assert len(snapshot.sources) == 2
    assert len(snapshot.canonical_sources) == 1
    assert len(snapshot.selected_sources) == 1


def test_load_local_snapshot_rejects_unit_source_path_mismatch(reviewed_snapshot):
    records = _records()
    records["source_units"][0]["relative_path"] = "other.md"
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="source unit path does not match"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_chunk_offset_or_source_mismatch(reviewed_snapshot):
    records = _records()
    records["chunks"][0]["char_end"] -= 1
    _set_records(reviewed_snapshot, records)

    with pytest.raises(ValueError, match="chunk text does not match source unit span"):
        load_local_snapshot(reviewed_snapshot)


@pytest.mark.parametrize(
    "payload", ["records.json", "judgments.jsonl", "anchors.jsonl", "manifest.json"]
)
def test_load_local_snapshot_rejects_symlink_payload(
    reviewed_snapshot, tmp_path, payload
):
    path = reviewed_snapshot / payload
    target = tmp_path / f"copy-{payload}"
    target.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_symlink_root(reviewed_snapshot, tmp_path):
    link = tmp_path / "snapshot-link"
    link.symlink_to(reviewed_snapshot, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        load_local_snapshot(link)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("schema_version", 2, "manifest schema_version"),
        ("snapshot_version", "another-version", "snapshot_version"),
        (
            "schema_versions",
            {"records": 1, "judgments": 1},
            "schema_versions",
        ),
        ("review_status", "pending", "review_status"),
        ("source_root", "/private/data", "repository-relative"),
    ],
)
def test_load_local_snapshot_rejects_invalid_manifest_contract(
    reviewed_snapshot, field, value, message
):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    manifest[field] = value
    _write_manifest(reviewed_snapshot, manifest)

    with pytest.raises(ValueError, match=message):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_repository_path_that_does_not_map_to_source_root(
    reviewed_snapshot,
):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    manifest["source_provenance"][0]["repository_path"] = "../private/notes.md"
    _write_manifest(reviewed_snapshot, manifest)

    with pytest.raises(ValueError, match="repository-relative source path"):
        load_local_snapshot(reviewed_snapshot)


def test_load_local_snapshot_rejects_manifest_count_mismatch(reviewed_snapshot):
    manifest = json.loads((reviewed_snapshot / "manifest.json").read_bytes())
    manifest["counts"]["chunks"] = 0
    _write_manifest(reviewed_snapshot, manifest)

    with pytest.raises(ValueError, match="chunk count"):
        load_local_snapshot(reviewed_snapshot)
