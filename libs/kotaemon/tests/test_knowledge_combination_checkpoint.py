"""Strict resume-checkpoint validation for local combination runs."""

from __future__ import annotations

import json

import pytest


def _checkpoint(tmp_path, *, bind_runtime=True):
    from kotaemon.indices.knowledge.evaluation.combination_checkpoint import (
        RunCheckpoint,
    )

    fingerprints = {
        "snapshot": "1" * 64,
        "gold": "2" * 64,
        "model": "3" * 64,
        "model_manifest": "4" * 64,
        "config": "5" * 64,
    }
    arm_fingerprints = {"arm-a": "a" * 64, "arm-b": "b" * 64}
    state = RunCheckpoint.create(
        tmp_path / "staging",
        run_id="synthetic-run",
        fingerprints=fingerprints,
        case_ids=("case-a", "case-b"),
        arm_config_fingerprints=arm_fingerprints,
    )
    if bind_runtime:
        for arm, fingerprint in arm_fingerprints.items():
            state.bind_arm_config(arm, fingerprint)
    return state, fingerprints, arm_fingerprints


def test_checkpoint_round_trip_binds_inputs_and_keeps_private_text_out_of_control_file(
    tmp_path,
):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    trace = {"original_query": "private-query-sentinel", "result_ids": ["chunk-a"]}
    summary = {"case_id": "case-a", "candidate_ids": ["chunk-a"]}

    state.begin("arm-a", 0, "case-a")
    state.complete("arm-a", 0, "case-a", trace=trace, summary=summary)

    resumed = type(state).resume(
        state.root,
        expected_fingerprints=fingerprints,
        expected_case_ids=("case-a", "case-b"),
        expected_arm_config_fingerprints=arm_fingerprints,
    )

    assert resumed.completed_keys == frozenset({("arm-a", 0)})
    loaded_trace, loaded_summary = resumed.read("arm-a", 0)
    assert loaded_trace == trace
    assert loaded_summary == summary
    checkpoint_bytes = (state.root / "run-checkpoint.json").read_bytes()
    assert b"private-query-sentinel" not in checkpoint_bytes
    assert json.loads(checkpoint_bytes)["fingerprints"] == fingerprints


def test_resume_rejects_changed_fingerprint_before_reusing_any_trace(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    state.complete(
        "arm-a",
        0,
        "case-a",
        trace={"original_query": "private-query-sentinel"},
        summary={"case_id": "case-a"},
    )
    changed = {**fingerprints, "model": "f" * 64}

    with pytest.raises(ValueError, match="fingerprint"):
        type(state).resume(
            state.root,
            expected_fingerprints=changed,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_rejects_symlinked_checkpoint_artifacts(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    state.complete(
        "arm-a",
        0,
        "case-a",
        trace={"original_query": "private-query-sentinel"},
        summary={"case_id": "case-a"},
    )
    trace_path = state.root / "traces" / "arm-a" / "query-0000.json"
    target = tmp_path / "trace-target.json"
    target.write_bytes(trace_path.read_bytes())
    trace_path.unlink()
    trace_path.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        type(state).resume(
            state.root,
            expected_fingerprints=fingerprints,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_discards_only_an_uncommitted_inflight_query(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    (state.root / "traces" / "arm-a").mkdir(parents=True)
    (state.root / ".resume" / "rows" / "arm-a").mkdir(parents=True)

    resumed = type(state).resume(
        state.root,
        expected_fingerprints=fingerprints,
        expected_case_ids=("case-a", "case-b"),
        expected_arm_config_fingerprints=arm_fingerprints,
    )

    assert resumed.completed_keys == frozenset()
    assert (state.root / "run-checkpoint.json").is_file()
    assert resumed._data["pending"] is None


def test_resume_rejects_out_of_range_query_index(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    state.complete(
        "arm-a",
        0,
        "case-a",
        trace={"original_query": "private-query-sentinel"},
        summary={"case_id": "case-a"},
    )
    checkpoint_path = state.root / "run-checkpoint.json"
    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    data["completed"][0]["query_index"] = 2
    checkpoint_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="out of range"):
        type(state).resume(
            state.root,
            expected_fingerprints=fingerprints,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_rejects_duplicate_completed_arm_query_pairs(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    state.complete(
        "arm-a",
        0,
        "case-a",
        trace={"original_query": "private-query-sentinel"},
        summary={"case_id": "case-a"},
    )
    checkpoint_path = state.root / "run-checkpoint.json"
    data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    data["completed"].append(dict(data["completed"][0]))
    checkpoint_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        type(state).resume(
            state.root,
            expected_fingerprints=fingerprints,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_rejects_symlinks_anywhere_in_staging_tree(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    state.begin("arm-a", 0, "case-a")
    state.complete(
        "arm-a",
        0,
        "case-a",
        trace={"original_query": "private-query-sentinel"},
        summary={"case_id": "case-a"},
    )
    outside = tmp_path / "outside"
    outside.write_text("synthetic", encoding="utf-8")
    (state.root / "generation-inputs").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        type(state).resume(
            state.root,
            expected_fingerprints=fingerprints,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_rejects_unlisted_artifacts_at_staging_root(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path)
    (state.root / "unexpected.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected artifacts"):
        type(state).resume(
            state.root,
            expected_fingerprints=fingerprints,
            expected_case_ids=("case-a", "case-b"),
            expected_arm_config_fingerprints=arm_fingerprints,
        )


def test_resume_rejects_changed_runtime_derived_arm_configuration(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path, bind_runtime=False)
    state.bind_arm_config("arm-a", "d" * 64)
    resumed = type(state).resume(
        state.root,
        expected_fingerprints=fingerprints,
        expected_case_ids=("case-a", "case-b"),
        expected_arm_config_fingerprints=arm_fingerprints,
    )

    with pytest.raises(ValueError, match="effective arm configuration"):
        resumed.bind_arm_config("arm-a", "e" * 64)


def test_fresh_checkpoint_resumes_before_first_effective_arm_binding(tmp_path):
    state, fingerprints, arm_fingerprints = _checkpoint(tmp_path, bind_runtime=False)

    resumed = type(state).resume(
        state.root,
        expected_fingerprints=fingerprints,
        expected_case_ids=("case-a", "case-b"),
        expected_arm_config_fingerprints=arm_fingerprints,
    )

    assert resumed.effective_arm_config_fingerprints == {}
    with pytest.raises(ValueError, match="unexpected arm"):
        resumed.bind_arm_config("unknown-arm", "c" * 64)
    with pytest.raises(ValueError, match="invalid effective arm"):
        resumed.bind_arm_config("arm-a", "not-a-digest")
    resumed.bind_arm_config("arm-a", "d" * 64)
    assert resumed.effective_arm_config_fingerprints == {"arm-a": "d" * 64}


def test_checkpoint_still_requires_declared_arm_definitions(tmp_path):
    from kotaemon.indices.knowledge.evaluation.combination_checkpoint import (
        RunCheckpoint,
    )

    with pytest.raises(ValueError, match="invalid arm configuration list"):
        RunCheckpoint.create(
            tmp_path / "empty-arms",
            run_id="synthetic-run",
            fingerprints={
                "snapshot": "1" * 64,
                "gold": "2" * 64,
                "model": "3" * 64,
                "model_manifest": "4" * 64,
                "config": "5" * 64,
            },
            case_ids=("case-a", "case-b"),
            arm_config_fingerprints={},
        )
