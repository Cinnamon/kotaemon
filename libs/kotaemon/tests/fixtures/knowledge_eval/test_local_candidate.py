"""Synthetic contract tests for the private local-candidate builder."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent))
local_candidate = importlib.import_module("local_candidate")

QUERY_TYPES = (
    ["direct_lookup"] * 16
    + ["procedure_condition"] * 14
    + ["comparison_synthesis"] * 12
    + ["exception_scope"] * 8
    + ["multi_hop"] * 4
)
TOPICS = ["Climate", "LLM", "Rice", "Environmental-health"]
EXPECTED_COUNTS = {"documents": 22, "queries": 80, "new_queries": 54}


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _jsonl_bytes(rows):
    return b"".join(_json_bytes(row) for row in rows)


def _write_jsonl(path, rows):
    path.write_bytes(_jsonl_bytes(rows))


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _refresh_v1_manifest(case):
    payload_names = ("records.json", "judgments.jsonl", "anchors.jsonl")
    manifest = {
        "snapshot_version": "v1",
        "review_status": "approved",
        "source_root": case["source_root"],
        "payload_sha256": {
            name: hashlib.sha256((case["v1_dir"] / name).read_bytes()).hexdigest()
            for name in payload_names
        },
    }
    case["manifest_bytes"] = _json_bytes(manifest)
    (case["v1_dir"] / "manifest.json").write_bytes(case["manifest_bytes"])


def _anchor(query_id, source_id, unit, anchor_id):
    start = 0
    end = min(12, len(unit["normalized_text"]))
    return {
        "schema_version": 1,
        "id": anchor_id,
        "query_id": query_id,
        "source_id": source_id,
        "source_sha256": source_id,
        "unit_id": unit["unit_id"],
        "locator": unit["locator"],
        "char_start": start,
        "char_end": end,
        "evidence_sha256": hashlib.sha256(
            unit["normalized_text"][start:end].encode("utf-8")
        ).hexdigest(),
    }


def _new_additions(source_ids):
    rows = []
    for index, query_type in enumerate(QUERY_TYPES):
        query_number = 27 + index
        query_id = f"q-{query_number:03d}"
        first_source = index % len(source_ids)
        relevant_indices = [first_source]
        if index < 16:
            relevant_indices.append((first_source + 1) % len(source_ids))
        relevant_ids = [source_ids[source_index] for source_index in relevant_indices]
        scope_indices = list(relevant_indices)
        extra_scope = (first_source + 3) % len(source_ids)
        if extra_scope not in scope_indices:
            scope_indices.append(extra_scope)
        scope_source_ids = [source_ids[source_index] for source_index in scope_indices]
        rows.append(
            {
                "id": query_id,
                "query": f"Synthetic addition question {query_number}?",
                "topic": TOPICS[index % len(TOPICS)],
                "query_type": query_type,
                "relevant_ids": relevant_ids,
                "scope_source_ids": scope_source_ids,
                "anchors": [
                    {
                        "source_id": source_ids[source_index],
                        "unit_id": f"unit-{source_index:02d}",
                        "char_start": 0,
                        "char_end": 12,
                    }
                    for source_index in relevant_indices
                ],
            }
        )
    return rows


def _make_case(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    source_ids = [
        hashlib.sha256(f"synthetic-source-{index:02d}".encode()).hexdigest()
        for index in range(22)
    ]
    sources = []
    source_units = []
    chunks = []
    units_by_source = {}
    for index, source_id in enumerate(source_ids):
        relative_path = f"source-{index:02d}.md"
        normalized_text = f"Synthetic normalized content for source {index:02d}."
        unit = {
            "unit_id": f"unit-{index:02d}",
            "source_id": source_id,
            "relative_path": relative_path,
            "unit_ordinal": 0,
            "locator": {"page_label": str(index + 1)},
            "text": normalized_text,
            "normalized_text": normalized_text,
        }
        units_by_source[source_id] = unit
        source_units.append(unit)
        chunks.append(
            {
                "chunk_id": f"chunk-{index:02d}",
                "source_id": source_id,
                "relative_path": relative_path,
                "unit_id": unit["unit_id"],
                "unit_ordinal": 0,
                "chunk_ordinal": 0,
                "locator": unit["locator"],
                "text": normalized_text,
                "char_start": 0,
                "char_end": len(normalized_text),
            }
        )
        source_bytes = f"synthetic-source-{index:02d}".encode()
        sources.append(
            {
                "source_id": source_id,
                "relative_path": relative_path,
                "sha256": source_id,
                "suffix": ".md",
                "byte_size": len(source_bytes),
                "duplicate_of": None,
                "selected_reader": "markdown",
                "reader_attempts": ["markdown"],
                "reader_fallback_used": False,
                "reader_granularity": "unit",
                "status": "parsed",
            }
        )

    records = {
        "schema_version": 1,
        "parser_configuration": {"name": "synthetic-parser"},
        "splitter_configuration": {"name": "synthetic-splitter"},
        "quality": {"synthetic": True},
        "sources": sources,
        "source_units": source_units,
        "chunks": chunks,
        "topic_candidates": [],
        "topic_review_source_ids": [],
        "excluded_inputs": [],
    }
    records_bytes = _json_bytes(records)
    (v1_dir / "records.json").write_bytes(records_bytes)

    v1_judgments = []
    v1_anchors = []
    for index in range(26):
        query_id = f"q-{index + 1:03d}"
        source_indices = [index % 22]
        if index < 18:
            source_indices.append((index + 1) % 22)
        relevant_ids = [source_ids[source_index] for source_index in source_indices]
        v1_judgments.append(
            {
                "schema_version": 1,
                "id": query_id,
                "query": f"Synthetic legacy question {index + 1}?",
                "judgment_level": "source",
                "relevant_ids": relevant_ids,
                "disallowed_source_ids": [],
            }
        )
        for source_index, source_id in zip(source_indices, relevant_ids):
            v1_anchors.append(
                _anchor(
                    query_id,
                    source_id,
                    units_by_source[source_id],
                    f"anchor-v1-{len(v1_anchors) + 1:03d}",
                )
            )

    v1_judgments_bytes = _jsonl_bytes(v1_judgments)
    v1_anchors_bytes = _jsonl_bytes(v1_anchors)
    (v1_dir / "judgments.jsonl").write_bytes(v1_judgments_bytes)
    (v1_dir / "anchors.jsonl").write_bytes(v1_anchors_bytes)
    case = {"v1_dir": v1_dir, "source_root": "synthetic/knowledge-eval"}
    _refresh_v1_manifest(case)
    manifest_bytes = case["manifest_bytes"]

    additions_path = tmp_path / "additions.jsonl"
    additions = _new_additions(source_ids)
    _write_jsonl(additions_path, additions)
    legacy_metadata_path = tmp_path / "legacy_metadata.jsonl"
    legacy_metadata = [
        {
            "query_id": f"q-{index + 1:03d}",
            "topic": TOPICS[index % len(TOPICS)],
            "query_type": "direct_lookup",
        }
        for index in range(26)
    ]
    _write_jsonl(legacy_metadata_path, list(reversed(legacy_metadata)))
    return {
        "v1_dir": v1_dir,
        "additions_path": additions_path,
        "legacy_metadata_path": legacy_metadata_path,
        "source_ids": source_ids,
        "records_bytes": records_bytes,
        "v1_judgments_bytes": v1_judgments_bytes,
        "v1_anchors_bytes": v1_anchors_bytes,
        "manifest_bytes": manifest_bytes,
        "additions": additions,
        "source_root": "synthetic/knowledge-eval",
    }


def _build(case, output_dir):
    return local_candidate.build_candidate(
        case["v1_dir"],
        case["additions_path"],
        case["legacy_metadata_path"],
        output_dir,
    )


def _validate(case, output_dir):
    return local_candidate.validate_candidate(
        case["v1_dir"],
        case["additions_path"],
        case["legacy_metadata_path"],
        output_dir,
    )


def test_build_candidate_preserves_v1_prefixes_and_writes_deterministic_metadata(
    tmp_path,
):
    case = _make_case(tmp_path)
    first_output = tmp_path / "draft-a"
    second_output = tmp_path / "draft-b"

    assert _build(case, first_output) == EXPECTED_COUNTS
    assert _build(case, second_output) == EXPECTED_COUNTS

    assert (first_output / "records.json").read_bytes() == case["records_bytes"]
    assert (first_output / "judgments.jsonl").read_bytes().startswith(
        case["v1_judgments_bytes"]
    )
    assert (first_output / "anchors.jsonl").read_bytes().startswith(
        case["v1_anchors_bytes"]
    )
    assert (first_output / "judgments.jsonl").read_bytes()[: len(case["v1_judgments_bytes"])] == case[
        "v1_judgments_bytes"
    ]
    assert (first_output / "anchors.jsonl").read_bytes()[: len(case["v1_anchors_bytes"])] == case[
        "v1_anchors_bytes"
    ]

    expected_files = {
        "records.json",
        "judgments.jsonl",
        "anchors.jsonl",
        "question_metadata.jsonl",
        "manifest.json",
    }
    assert {path.name for path in first_output.iterdir()} == expected_files
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in first_output.iterdir()
    } == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in second_output.iterdir()
    }

    judgments = _read_jsonl(first_output / "judgments.jsonl")
    anchors = _read_jsonl(first_output / "anchors.jsonl")
    metadata = _read_jsonl(first_output / "question_metadata.jsonl")
    assert len(judgments) == 80
    assert [row["id"] for row in judgments] == [f"q-{index:03d}" for index in range(1, 81)]
    assert len(metadata) == 80
    assert [row["query_id"] for row in metadata] == [
        f"q-{index:03d}" for index in range(1, 81)
    ]
    assert len(anchors) == 44 + sum(len(row["relevant_ids"]) for row in case["additions"])
    assert all(
        set(row)
        == {"query_id", "topic", "query_type", "relevant_source_count"}
        for row in metadata
    )
    assert [row["relevant_source_count"] for row in metadata] == [
        len(row["relevant_ids"]) for row in judgments
    ]
    new_judgments = judgments[26:]
    assert all(row["judgment_level"] == "source" for row in new_judgments)
    for row, addition in zip(new_judgments, case["additions"]):
        scope = set(addition["scope_source_ids"])
        assert set(row["allowed_source_ids"]) == scope
        assert set(row["disallowed_source_ids"]) == set(case["source_ids"]) - scope
    first_new_anchor = anchors[44]
    first_unit_text = "Synthetic normalized content for source 00."
    assert first_new_anchor["query_id"] == "q-027"
    assert first_new_anchor["source_id"] == case["source_ids"][0]
    assert first_new_anchor["source_sha256"] == case["source_ids"][0]
    assert first_new_anchor["locator"] == {"page_label": "1"}
    assert first_new_anchor["evidence_sha256"] == hashlib.sha256(
        first_unit_text[:12].encode("utf-8")
    ).hexdigest()

    manifest = json.loads((first_output / "manifest.json").read_bytes())
    assert manifest["snapshot_version"] == "v2-draft"
    assert manifest["review_status"] == "draft"
    assert manifest["review_date"] is None
    local_cli = importlib.import_module(
        "kotaemon.indices.knowledge.evaluation.local_cli"
    )
    reviewed_manifest, _ = local_cli._reviewed_manifest_for_freeze(
        first_output, version="v2", approved_at="2026-10-04"
    )
    assert manifest["source_root"] == case["source_root"]
    assert reviewed_manifest["source_provenance"][0]["repository_path"] == (
        f"{case['source_root']}/source-00.md"
    )
    assert manifest["parent_manifest_sha256"] == hashlib.sha256(
        case["manifest_bytes"]
    ).hexdigest()
    assert manifest["counts"] == EXPECTED_COUNTS
    assert set(manifest["payload_sha256"]) == {
        "records.json",
        "judgments.jsonl",
        "anchors.jsonl",
        "question_metadata.jsonl",
    }
    assert all(
        manifest["payload_sha256"][name]
        == hashlib.sha256((first_output / name).read_bytes()).hexdigest()
        for name in manifest["payload_sha256"]
    )
    assert _validate(case, first_output) == EXPECTED_COUNTS


def test_build_candidate_rejects_duplicate_query_ids(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["id"] = "q-026"
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="ID|id"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_duplicate_normalized_prompts(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["query"] = "  SYNTHETIC   LEGACY QUESTION 1?  "
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="duplicate.*prompt|prompt.*duplicate"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_unknown_sources(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["relevant_ids"][0] = "f" * 64
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="unknown.*source|source.*unknown"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_missing_relevant_pair_anchor(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    missing_source_id = additions[0]["scope_source_ids"][-1]
    additions[0]["relevant_ids"].append(missing_source_id)
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="anchor"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_invalid_anchor_offsets(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["anchors"][0]["char_end"] = 10000
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="offset|span|anchor"):
        _build(case, tmp_path / "draft")


@pytest.mark.parametrize("hash_field", ["source_sha256", "evidence_sha256"])
def test_build_candidate_rejects_mismatched_v1_anchor_hashes(tmp_path, hash_field):
    case = _make_case(tmp_path)
    anchors_path = case["v1_dir"] / "anchors.jsonl"
    anchors = _read_jsonl(anchors_path)
    anchors[0][hash_field] = "0" * 64
    _write_jsonl(anchors_path, anchors)
    _refresh_v1_manifest(case)

    with pytest.raises(ValueError, match="hash|SHA"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_wrong_query_type_quotas(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["query_type"] = "procedure_condition"
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="quota|query_type|type count"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_addition_ids_outside_q027_to_q080(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[-1]["id"] = "q-081"
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match="ID|id"):
        _build(case, tmp_path / "draft")


def test_build_candidate_rejects_json_array_inputs(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    case["additions_path"].write_bytes(_json_bytes(additions))

    with pytest.raises(ValueError, match="JSONL"):
        _build(case, tmp_path / "draft")


@pytest.mark.parametrize("output_alias", ["same-directory", "symlink"])
def test_build_candidate_rejects_v1_output_path_without_mutating_parent(
    tmp_path, output_alias
):
    case = _make_case(tmp_path)
    v1_dir = case["v1_dir"]
    output_dir = v1_dir
    if output_alias == "symlink":
        output_dir = tmp_path / "v1-alias"
        output_dir.symlink_to(v1_dir, target_is_directory=True)
    before = {path.name: path.read_bytes() for path in v1_dir.iterdir() if path.is_file()}
    error = None

    try:
        _build(case, output_dir)
    except ValueError as caught:
        error = caught

    after = {path.name: path.read_bytes() for path in v1_dir.iterdir() if path.is_file()}
    assert after == before, "attempted build changed the v1 parent"
    assert error is not None, "build accepted an output path resolving to v1"
    assert "output" in str(error).lower() or "parent" in str(error).lower()


@pytest.mark.parametrize(
    "output_name",
    [
        "records.json",
        "judgments.jsonl",
        "anchors.jsonl",
        "question_metadata.jsonl",
        "manifest.json",
    ],
)
def test_build_candidate_rejects_output_file_symlinks_before_any_write(
    tmp_path, output_name
):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    output_dir.mkdir()
    target_name = output_name if output_name in {
        "records.json",
        "judgments.jsonl",
        "anchors.jsonl",
        "manifest.json",
    } else "judgments.jsonl"
    output_link = output_dir / output_name
    output_link.symlink_to(case["v1_dir"] / target_name)
    before = {path.name: path.read_bytes() for path in case["v1_dir"].iterdir() if path.is_file()}
    error = None

    try:
        _build(case, output_dir)
    except ValueError as caught:
        error = caught

    after = {path.name: path.read_bytes() for path in case["v1_dir"].iterdir() if path.is_file()}
    assert after == before, "attempted build changed the v1 parent through an output symlink"
    assert error is not None, "build accepted a symlink output target"
    assert "symlink" in str(error).lower()
    assert {path.name for path in output_dir.iterdir()} == {output_name}


def test_build_candidate_replaces_output_hardlink_without_changing_parent(tmp_path):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    output_dir.mkdir()
    v1_judgments = case["v1_dir"] / "judgments.jsonl"
    output_judgments = output_dir / "judgments.jsonl"
    os.link(v1_judgments, output_judgments)
    before = {path.name: path.read_bytes() for path in case["v1_dir"].iterdir() if path.is_file()}

    counts = _build(case, output_dir)

    after = {path.name: path.read_bytes() for path in case["v1_dir"].iterdir() if path.is_file()}
    assert after == before, "attempted build changed the v1 parent through an output hardlink"
    assert counts == EXPECTED_COUNTS
    assert output_judgments.read_bytes().startswith(before["judgments.jsonl"])
    assert not os.path.samefile(v1_judgments, output_judgments)


@pytest.mark.parametrize("field", ["topic", "query_type"])
def test_build_candidate_rejects_nonstring_taxonomy_values(tmp_path, field):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0][field] = []
    _write_jsonl(case["additions_path"], additions)

    with pytest.raises(ValueError, match=field):
        _build(case, tmp_path / "draft")


@pytest.mark.parametrize(
    ("field", "value"), [("snapshot_version", "v2"), ("review_status", "draft")]
)
def test_build_candidate_rejects_unapproved_or_wrong_v1_parent(tmp_path, field, value):
    case = _make_case(tmp_path)
    manifest_path = case["v1_dir"] / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest[field] = value
    manifest_path.write_bytes(_json_bytes(manifest))

    with pytest.raises(ValueError, match="v1|approved|snapshot"):
        _build(case, tmp_path / "draft")


@pytest.mark.parametrize(
    "source_root",
    [
        None,
        "",
        "/synthetic/knowledge-eval",
        "synthetic\\knowledge-eval",
        "synthetic/../knowledge-eval",
        "./synthetic/knowledge-eval",
        "synthetic//knowledge-eval",
        "C:/synthetic/knowledge-eval",
    ],
    ids=[
        "missing",
        "empty",
        "absolute",
        "backslash",
        "parent",
        "dot-component",
        "unnormalized",
        "drive",
    ],
)
def test_build_candidate_rejects_unsafe_v1_source_root_before_writing(
    tmp_path, source_root
):
    case = _make_case(tmp_path)
    manifest_path = case["v1_dir"] / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if source_root is None:
        del manifest["source_root"]
    else:
        manifest["source_root"] = source_root
    manifest_path.write_bytes(_json_bytes(manifest))
    output_dir = tmp_path / "draft"

    with pytest.raises(ValueError, match="source_root"):
        _build(case, output_dir)

    assert not output_dir.exists()


def test_validate_candidate_rejects_a_modified_v1_parent(tmp_path):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    _build(case, output_dir)
    parent_manifest = case["v1_dir"] / "manifest.json"
    parent_manifest.write_bytes(parent_manifest.read_bytes() + b" ")

    with pytest.raises(ValueError, match="parent|manifest"):
        _validate(case, output_dir)


def test_validate_candidate_rejects_a_changed_v1_prefix(tmp_path):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    _build(case, output_dir)
    judgments_path = output_dir / "judgments.jsonl"
    judgments_path.write_bytes(b" " + judgments_path.read_bytes())

    with pytest.raises(ValueError, match="prefix|v1|judgment"):
        _validate(case, output_dir)


def test_validate_candidate_rejects_a_changed_v1_source_hash_set(tmp_path):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    _build(case, output_dir)
    records_path = output_dir / "records.json"
    records = json.loads(records_path.read_bytes())
    records["sources"][0]["source_id"] = "0" * 64
    records["sources"][0]["sha256"] = "0" * 64
    records_path.write_bytes(_json_bytes(records))

    with pytest.raises(ValueError, match="source|parent|records"):
        _validate(case, output_dir)


def test_validate_candidate_rejects_output_payload_hash_mismatch(tmp_path):
    case = _make_case(tmp_path)
    output_dir = tmp_path / "draft"
    _build(case, output_dir)
    metadata_path = output_dir / "question_metadata.jsonl"
    metadata_path.write_bytes(metadata_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="hash|metadata|payload"):
        _validate(case, output_dir)


def test_cli_build_and_validate_print_counts_without_candidate_text(tmp_path):
    case = _make_case(tmp_path)
    script = Path(local_candidate.__file__)
    output_dir = tmp_path / "draft"
    common = [
        sys.executable,
        str(script),
        "--v1",
        str(case["v1_dir"]),
        "--additions",
        str(case["additions_path"]),
        "--legacy-metadata",
        str(case["legacy_metadata_path"]),
        "--output",
        str(output_dir),
    ]

    build = subprocess.run(
        [common[0], common[1], "build", *common[2:]],
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0
    assert json.loads(build.stdout) == EXPECTED_COUNTS
    assert "Synthetic" not in build.stdout

    validate = subprocess.run(
        [common[0], common[1], "validate", *common[2:]],
        check=False,
        capture_output=True,
        text=True,
    )
    assert validate.returncode == 0
    assert json.loads(validate.stdout) == EXPECTED_COUNTS
    assert "Synthetic" not in validate.stdout


def test_cli_rejects_nonstring_topic_without_traceback(tmp_path):
    case = _make_case(tmp_path)
    additions = _read_jsonl(case["additions_path"])
    additions[0]["topic"] = []
    _write_jsonl(case["additions_path"], additions)
    script = Path(local_candidate.__file__)

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "build",
            "--v1",
            str(case["v1_dir"]),
            "--additions",
            str(case["additions_path"]),
            "--legacy-metadata",
            str(case["legacy_metadata_path"]),
            "--output",
            str(tmp_path / "draft"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "topic" in result.stderr
