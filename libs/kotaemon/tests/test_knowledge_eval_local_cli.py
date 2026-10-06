"""Synthetic tests for the local-only knowledge evaluation CLI."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path, PurePosixPath
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from kotaemon.indices.knowledge.evaluation import local_cli
from kotaemon.indices.knowledge.evaluation import local_ingest
from kotaemon.indices.knowledge.evaluation import local_snapshot
from kotaemon.indices.knowledge.evaluation.local_models import LocalModelPaths


EMBEDDING_ID = "BAAI/bge-m3"
RERANKER_ID = "BAAI/bge-reranker-v2-m3"
EMBEDDING_REVISION = "a" * 40
RERANKER_REVISION = "b" * 40


def _json_bytes(value):
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )


def _write_approved_snapshot_sidecar(snapshot: Path, *, manifest_hash=None):
    manifest = _json_bytes({"review_status": "approved", "review_date": "2026-10-04"})
    (snapshot / "manifest.json").write_bytes(manifest)
    (snapshot / "approval.json").write_bytes(
        _json_bytes(
            {
                "approved_by": "synthetic-reviewer",
                "approved_at": "2026-10-04",
                "snapshot_manifest_sha256": manifest_hash
                or hashlib.sha256(manifest).hexdigest(),
            }
        )
    )


def _synthetic_source(root: Path) -> Path:
    path = root / "physical-folder-is-not-a-topic" / "notes.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Actual Content Heading\n\nGenerated evidence for CLI tests.\n",
        encoding="utf-8",
    )
    return root


def _fake_model_directory(path: Path, weight_bytes: bytes) -> dict[str, str]:
    path.mkdir(parents=True)
    (path / "config.json").write_text("{}", encoding="utf-8")
    (path / "tokenizer.json").write_text("{}", encoding="utf-8")
    (path / "tokenizer_config.json").write_text("{}", encoding="utf-8")
    (path / "special_tokens_map.json").write_text("{}", encoding="utf-8")
    (path / "vocab.txt").write_text("synthetic-token\n", encoding="utf-8")
    (path / "model.safetensors").write_bytes(weight_bytes)
    return {"model.safetensors": hashlib.sha256(weight_bytes).hexdigest()}


def _asset_sha256(model_dir: Path) -> dict[str, str]:
    return {
        path.relative_to(model_dir)
        .as_posix(): hashlib.sha256(path.read_bytes())
        .hexdigest()
        for path in sorted(model_dir.rglob("*"))
        if path.is_file()
        and PurePosixPath(path.relative_to(model_dir).as_posix()).parts[:2]
        != (".cache", "huggingface")
    }


def _write_model_manifest(
    local_root: Path, *, overrides=None, models=None
) -> tuple[Path, Path, Path]:
    models_root = local_root / "models"
    models_root.mkdir(parents=True, exist_ok=True)
    embedding_dir = models_root / "bge-m3"
    reranker_dir = models_root / "bge-reranker-v2-m3"
    embedding_hashes = _fake_model_directory(
        embedding_dir, b"synthetic embedding weights"
    )
    reranker_hashes = _fake_model_directory(reranker_dir, b"synthetic reranker weights")
    manifest_models = models or [
        {
            "role": "embedding",
            "model_id": EMBEDDING_ID,
            "revision": EMBEDDING_REVISION,
            "directory": "bge-m3",
            "weights_sha256": embedding_hashes,
            "assets_sha256": _asset_sha256(embedding_dir),
            "source": "cached",
        },
        {
            "role": "reranker",
            "model_id": RERANKER_ID,
            "revision": RERANKER_REVISION,
            "directory": "bge-reranker-v2-m3",
            "weights_sha256": reranker_hashes,
            "assets_sha256": _asset_sha256(reranker_dir),
            "source": "downloaded",
        },
    ]
    manifest = {"schema_version": 2, "models": manifest_models}
    manifest.update(overrides or {})
    manifest_path = models_root / "model-manifest.json"
    manifest_path.write_bytes(_json_bytes(manifest))
    return manifest_path, embedding_dir, reranker_dir


def test_cli_exposes_the_local_evaluation_commands():
    assert set(local_cli.main.commands) == {
        "combination-experiment",
        "supplemental-baseline",
        "resume-combination-experiment",
        "repack-combination-experiment",
        "inventory",
        "prepare-review",
        "freeze",
        "download-models",
        "run",
    }


def test_combination_experiment_help_exposes_versioned_inputs():
    result = CliRunner().invoke(local_cli.main, ["combination-experiment", "--help"])

    assert result.exit_code == 0, result.output
    for flag in (
        "--local-root",
        "--snapshot",
        "--embedding-model-dir",
        "--reranker-model-dir",
        "--artifact-dir",
        "--conversation-fixture",
    ):
        assert flag in result.output

    resume_help = CliRunner().invoke(
        local_cli.main, ["resume-combination-experiment", "--help"]
    )
    assert resume_help.exit_code == 0, resume_help.output
    for flag in ("--local-root", "--snapshot", "--artifact-dir", "--staging-dir"):
        assert flag in resume_help.output

    repack_help = CliRunner().invoke(
        local_cli.main, ["repack-combination-experiment", "--help"]
    )
    assert repack_help.exit_code == 0, repack_help.output
    for flag in (
        "--local-root",
        "--snapshot",
        "--artifact-dir",
        "--source-staging-dir",
    ):
        assert flag in repack_help.output

    supplemental_help = CliRunner().invoke(
        local_cli.main, ["supplemental-baseline", "--help"]
    )
    assert supplemental_help.exit_code == 0, supplemental_help.output
    for flag in (
        "--local-root",
        "--snapshot",
        "--embedding-model-dir",
        "--reranker-model-dir",
        "--reference-artifact-dir",
        "--artifact-dir",
    ):
        assert flag in supplemental_help.output


def test_combination_experiment_rejects_snapshot_outside_local_root(tmp_path):
    local_root = tmp_path / "local"
    outside_snapshot = tmp_path / "outside-snapshot"
    outside_snapshot.mkdir()

    result = CliRunner().invoke(
        local_cli.main,
        [
            "combination-experiment",
            "--local-root",
            str(local_root),
            "--snapshot",
            str(outside_snapshot),
            "--embedding-model-dir",
            str(tmp_path / "embedding"),
            "--reranker-model-dir",
            str(tmp_path / "reranker"),
            "--artifact-dir",
            str(local_root / "runs" / "run-1"),
        ],
    )

    assert result.exit_code != 0
    assert "snapshot" in result.output.lower()
    assert not (local_root / "runs").exists()


def _mock_combination_cli_prerequisites(monkeypatch, local_root: Path):
    snapshot = local_root / "snapshots" / "v2"
    snapshot.mkdir(parents=True)
    monkeypatch.setattr(local_cli, "load_local_snapshot", lambda _path: object())
    monkeypatch.setattr(local_cli, "_validate_snapshot_approval", lambda _path: None)
    monkeypatch.setattr(
        local_cli,
        "_resolve_model_paths_with_manifest",
        lambda *_args: (SimpleNamespace(), b"{}"),
    )
    monkeypatch.setattr(local_cli, "_require_offline_inference_process", lambda: None)

    def run_combination(
        _snapshot,
        *,
        artifact_dir,
        staging_dir,
        conversation_fixture=None,
        **_kwargs,
    ):
        if conversation_fixture is not None:
            from kotaemon.indices.knowledge.evaluation.combination_eval import (
                load_conversation_fixture,
            )

            load_conversation_fixture(conversation_fixture)
        staging_dir.mkdir(parents=True)
        (staging_dir / "report.json").write_text("{}", encoding="utf-8")
        (staging_dir / "artifact-manifest.json").write_text(
            json.dumps({"artifacts": []}), encoding="utf-8"
        )
        staging_dir.rename(artifact_dir)

    monkeypatch.setattr(local_cli, "run_combination_experiment", run_combination)
    return snapshot


def _combination_cli_args(local_root: Path, snapshot: Path, artifact_dir: Path):
    return [
        "combination-experiment",
        "--local-root",
        str(local_root),
        "--snapshot",
        str(snapshot),
        "--embedding-model-dir",
        str(local_root / "models" / "bge-m3"),
        "--reranker-model-dir",
        str(local_root / "models" / "bge-reranker-v2-m3"),
        "--artifact-dir",
        str(artifact_dir),
    ]


def test_combination_experiment_rejects_artifact_escape_and_overwrite(
    tmp_path, monkeypatch
):
    local_root = tmp_path / "local"
    snapshot = _mock_combination_cli_prerequisites(monkeypatch, local_root)
    runs = local_root / "runs"
    runs.mkdir()
    existing = runs / "existing"
    existing.mkdir()
    marker = existing / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")
    runner = CliRunner()

    escape = runner.invoke(
        local_cli.main,
        _combination_cli_args(local_root, snapshot, tmp_path / "outside"),
    )
    overwrite = runner.invoke(
        local_cli.main,
        _combination_cli_args(local_root, snapshot, existing),
    )

    assert escape.exit_code != 0
    assert "artifact" in escape.output.lower()
    assert overwrite.exit_code != 0
    assert "already exists" in overwrite.output.lower()
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_resume_combination_experiment_uses_selected_staging_path(
    tmp_path, monkeypatch
):
    local_root = tmp_path / "local"
    snapshot = _mock_combination_cli_prerequisites(monkeypatch, local_root)
    runs = local_root / "runs"
    runs.mkdir()
    staging = runs / ".resumed.staging-synthetic"
    staging.mkdir()
    captured = {}

    def run_combination(_snapshot, **kwargs):
        captured.update(kwargs)
        (staging / "report.json").write_text("{}", encoding="utf-8")
        (staging / "artifact-manifest.json").write_text(
            json.dumps({"artifacts": []}), encoding="utf-8"
        )
        staging.rename(kwargs["artifact_dir"])

    monkeypatch.setattr(local_cli, "run_combination_experiment", run_combination)
    arguments = _combination_cli_args(local_root, snapshot, runs / "resumed")
    arguments[0] = "resume-combination-experiment"
    arguments.extend(["--staging-dir", str(staging)])

    result = CliRunner().invoke(local_cli.main, arguments)

    assert result.exit_code == 0, result.output
    assert captured["staging_dir"] == staging
    assert captured["resume"] is True
    assert (runs / "resumed" / "model-manifest.json").is_file()


def test_combination_experiment_rejects_unreviewed_fixture(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    snapshot = _mock_combination_cli_prerequisites(monkeypatch, local_root)
    fixture_path = local_root / "conversation-fixtures" / "unreviewed.json"
    fixture_path.parent.mkdir(parents=True)
    fixture_path.write_text(
        json.dumps({"schema_version": 1, "reviewed": False, "cases": []}),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        local_cli.main,
        [
            *_combination_cli_args(local_root, snapshot, local_root / "runs" / "new"),
            "--conversation-fixture",
            str(fixture_path),
        ],
    )

    assert result.exit_code != 0
    assert "explicitly reviewed" in result.output.lower()
    assert not (local_root / "runs" / "new").exists()


def test_prepare_review_is_local_deterministic_and_does_not_invent_gold(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    original = (
        source_root / "physical-folder-is-not-a-topic" / "notes.md"
    ).read_bytes()
    local_a = tmp_path / "local-a"
    local_b = tmp_path / "local-b"
    runner = CliRunner()
    common = [
        "prepare-review",
        "--source-root",
        str(source_root),
        "--source-root-label",
        "synthetic/sources",
        "--version",
        "fixture",
        "--all-sources",
    ]

    first = runner.invoke(local_cli.main, [*common, "--local-root", str(local_a)])
    second = runner.invoke(local_cli.main, [*common, "--local-root", str(local_b)])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    draft_a = local_a / "draft" / "fixture"
    draft_b = local_b / "draft" / "fixture"
    expected_files = {
        "records.json",
        "judgments.jsonl",
        "anchors.jsonl",
        "manifest.json",
        "REVIEW.md",
    }
    assert {path.name for path in draft_a.iterdir()} == expected_files
    assert {path.name for path in draft_b.iterdir()} == expected_files
    for name in expected_files:
        assert (draft_a / name).read_bytes() == (draft_b / name).read_bytes()
    assert (draft_a / "judgments.jsonl").read_bytes() == b""
    assert (draft_a / "anchors.jsonl").read_bytes() == b""
    records = json.loads((draft_a / "records.json").read_bytes())
    candidates = records["topic_candidates"]
    assert [candidate["text"] for candidate in candidates] == ["Actual Content Heading"]
    assert all(candidate["needs_review"] for candidate in candidates)
    review = (draft_a / "REVIEW.md").read_text(encoding="utf-8").lower()
    assert "unreviewed" in review
    assert candidates[0]["text"] != "physical-folder-is-not-a-topic"
    assert (
        source_root / "physical-folder-is-not-a-topic" / "notes.md"
    ).read_bytes() == original
    assert not (tmp_path / "draft").exists()
    assert (
        json.loads((draft_a / "manifest.json").read_bytes())["review_status"] == "draft"
    )


def test_inventory_output_is_contained_in_selected_local_root(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    local_root = tmp_path / "local"
    result = CliRunner().invoke(
        local_cli.main,
        [
            "inventory",
            "--source-root",
            str(source_root),
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code == 0, result.output
    inventory_path = local_root / "draft" / "inventory.json"
    assert inventory_path.is_file()
    inventory = json.loads(inventory_path.read_bytes())
    assert [row["relative_path"] for row in inventory] == [
        "physical-folder-is-not-a-topic/notes.md"
    ]
    assert all(path.is_relative_to(local_root) for path in local_root.rglob("*"))


def _repository_root() -> Path:
    module_dir = Path(local_cli.__file__).resolve().parent
    result = subprocess.run(
        ["git", "-C", str(module_dir), "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def test_inventory_rejects_unignored_root_inside_repository_without_writes(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    local_root = _repository_root() / f"task7-unignored-{tmp_path.name}"
    assert not local_root.exists()
    try:
        result = CliRunner().invoke(
            local_cli.main,
            [
                "inventory",
                "--source-root",
                str(source_root),
                "--local-root",
                str(local_root),
            ],
        )
        assert result.exit_code != 0
        assert "git-ignored" in result.output.lower()
        assert not local_root.exists()
    finally:
        if local_root.exists():
            shutil.rmtree(local_root)


def test_git_ignore_guard_accepts_local_fixture_root_without_writes():
    local_root = (
        _repository_root() / "libs/kotaemon/tests/fixtures/knowledge_eval/local"
    )
    existed_before = local_root.exists()

    local_cli._require_ignored_repo_local_root(local_root)

    assert local_root.exists() is existed_before


def test_output_category_symlink_cannot_redirect_writes_to_another_tree(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    local_root = tmp_path / "local"
    local_root.mkdir()
    redirected = local_root / "other"
    redirected.mkdir()
    (local_root / "draft").symlink_to(redirected, target_is_directory=True)

    result = CliRunner().invoke(
        local_cli.main,
        [
            "inventory",
            "--source-root",
            str(source_root),
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code != 0
    assert "symlink" in result.output.lower()
    assert not (redirected / "inventory.json").exists()


def test_all_sources_cannot_be_mislabeled_as_the_v1_sample(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    local_root = tmp_path / "local"
    result = CliRunner().invoke(
        local_cli.main,
        [
            "prepare-review",
            "--source-root",
            str(source_root),
            "--source-root-label",
            "synthetic/sources",
            "--local-root",
            str(local_root),
            "--version",
            "v1",
            "--all-sources",
        ],
    )

    assert result.exit_code != 0
    assert "non-v1" in result.output.lower()


def test_v1_sampling_refuses_fewer_than_20_usable_documents(tmp_path):
    source_root = _synthetic_source(tmp_path / "sources")
    local_root = tmp_path / "local"
    result = CliRunner().invoke(
        local_cli.main,
        [
            "prepare-review",
            "--source-root",
            str(source_root),
            "--source-root-label",
            "synthetic/sources",
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code != 0
    assert "at least 20 usable unique documents" in result.output.lower()
    assert not (local_root / "draft" / "v1").exists()


def test_explicit_v1_sample_rejects_failed_and_empty_selected_sources(
    tmp_path, monkeypatch
):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for index in range(20):
        (source_root / f"document-{index:02d}.md").write_text(
            f"# Synthetic topic {index}\n\nGenerated body {index}.\n",
            encoding="utf-8",
        )

    real_loader = local_ingest._load_reader_documents

    def fail_or_empty_selected_source(source, path):
        if source.relative_path in {"document-00.md", "document-01.md"}:
            error_type = (
                "SyntheticReaderError"
                if source.relative_path == "document-00.md"
                else None
            )
            diagnostic = local_ingest._reader_diagnostic(
                source,
                None,
                ("TxtReader",),
                False,
                "file",
                needs_review=True,
                detail=("synthetic read failure" if error_type else "synthetic empty"),
            )
            if error_type is None:
                return [SimpleNamespace(text="   ", metadata={})], diagnostic, None
            return [], diagnostic, error_type
        return real_loader(source, path)

    monkeypatch.setattr(
        local_ingest, "_load_reader_documents", fail_or_empty_selected_source
    )
    source_ids = [row.source_id for row in local_cli.scan_sources(source_root)]
    local_root = tmp_path / "local"
    arguments = [
        "prepare-review",
        "--source-root",
        str(source_root),
        "--source-root-label",
        "synthetic/sources",
        "--local-root",
        str(local_root),
    ]
    for source_id in source_ids:
        arguments.extend(("--sample-id", source_id))

    result = CliRunner().invoke(local_cli.main, arguments)

    assert result.exit_code != 0
    assert "18 usable unique documents" in result.output.lower()
    assert "document-00.md" in result.output
    assert "SyntheticReaderError" in result.output
    assert "document-01.md" in result.output
    assert "empty_extraction" in result.output
    assert not (local_root / "draft" / "v1").exists()


def test_explicit_v1_sample_requires_coverage_of_usable_source_formats(tmp_path):
    import fitz

    source_root = tmp_path / "sources"
    source_root.mkdir()
    for index in range(20):
        (source_root / f"document-{index:02d}.md").write_text(
            f"# Synthetic topic {index}\n\nGenerated body {index}.\n",
            encoding="utf-8",
        )
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Generated PDF evidence.")
    pdf.save(source_root / "z-generated.pdf")
    pdf.close()

    markdown_ids = [
        row.source_id
        for row in local_cli.scan_sources(source_root)
        if row.suffix == ".md"
    ]
    local_root = tmp_path / "local"
    arguments = [
        "prepare-review",
        "--source-root",
        str(source_root),
        "--source-root-label",
        "synthetic/sources",
        "--local-root",
        str(local_root),
    ]
    for source_id in markdown_ids:
        arguments.extend(("--sample-id", source_id))

    result = CliRunner().invoke(local_cli.main, arguments)

    assert result.exit_code != 0
    assert ".pdf" in result.output
    assert "format coverage" in result.output.lower()
    assert "selected usable formats are .md" in result.output.lower()
    assert not (local_root / "draft" / "v1").exists()


def test_explicit_v1_sample_explains_omitted_topics_truthfully(tmp_path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for index in range(22):
        (source_root / f"document-{index:02d}.md").write_text(
            f"# Unique explicit topic {index:02d}\n\nGenerated body {index}.\n",
            encoding="utf-8",
        )

    source_rows = local_cli.scan_sources(source_root)
    sample_ids = [row.source_id for row in source_rows[:20]]
    omitted_rows = source_rows[20:]
    local_root = tmp_path / "local"
    arguments = [
        "prepare-review",
        "--source-root",
        str(source_root),
        "--source-root-label",
        "synthetic/sources",
        "--local-root",
        str(local_root),
    ]
    for source_id in sample_ids:
        arguments.extend(("--sample-id", source_id))

    result = CliRunner().invoke(local_cli.main, arguments)

    assert result.exit_code == 0, result.output
    records = json.loads((local_root / "draft" / "v1" / "records.json").read_bytes())
    assert sum(row["status"] == "parsed" for row in records["sources"]) == 20
    review = (local_root / "draft" / "v1" / "REVIEW.md").read_text(encoding="utf-8")
    assert "not selected for this v1 sample" in review
    assert "omitted by the 24-source cap" not in review
    for index, row in enumerate(omitted_rows, start=20):
        assert f"`{row.source_id}` — Unique explicit topic {index:02d}" in review


def test_default_v1_review_selects_24_documents_by_format_and_content_candidates(
    tmp_path,
):
    source_root = tmp_path / "sources"
    for index in range(26):
        path = (
            source_root / f"misleading-folder-{index % 3}" / f"document-{index:02}.md"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# Content Topic {index % 4}\n\nGenerated body {index}.\n",
            encoding="utf-8",
        )
    local_root = tmp_path / "local"

    result = CliRunner().invoke(
        local_cli.main,
        [
            "prepare-review",
            "--source-root",
            str(source_root),
            "--source-root-label",
            "synthetic/sources",
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code == 0, result.output
    draft = local_root / "draft" / "v1"
    records = json.loads((draft / "records.json").read_bytes())
    selected = [row for row in records["sources"] if row["status"] == "parsed"]
    assert len(selected) == 24
    assert len({row["source_id"] for row in selected}) == 24
    assert sum(row["status"] == "not_selected" for row in records["sources"]) == 2
    assert (
        sum(row["reason"] == "not_selected" for row in records["excluded_inputs"]) == 2
    )
    selected_ids = {row["source_id"] for row in selected}
    topics = {
        row["text"]
        for row in records["topic_candidates"]
        if row["source_id"] in selected_ids
    }
    assert topics == {f"Content Topic {index}" for index in range(4)}
    assert all(row["needs_review"] for row in records["topic_candidates"])
    review = (draft / "REVIEW.md").read_text(encoding="utf-8")
    assert "24 of 26" in review
    assert "unreviewed" in review.lower()
    assert (draft / "judgments.jsonl").read_bytes() == b""
    assert (draft / "anchors.jsonl").read_bytes() == b""


def test_v1_selector_covers_all_supported_formats_under_24_source_cap():
    suffixes = (".pdf", ".docx", ".md", ".xlsx")
    sources = []
    chunks = []
    candidates = []
    for index in range(32):
        source_id = f"{index + 1:064x}"
        relative_path = f"generated/{index:02d}{suffixes[index % len(suffixes)]}"
        sources.append(
            {
                "source_id": source_id,
                "relative_path": relative_path,
                "suffix": suffixes[index % len(suffixes)],
                "duplicate_of": None,
                "status": "parsed",
            }
        )
        chunks.append(
            {
                "chunk_id": f"chunk-{index:02d}",
                "source_id": source_id,
                "text": f"Generated body {index}.",
            }
        )
        candidates.append(
            {
                "candidate_id": f"topic-{index:02d}",
                "source_id": source_id,
                "relative_path": relative_path,
                "locator": {"unit_ordinal": 0},
                "text": f"Generated content topic {index:02d}",
                "needs_review": True,
            }
        )
    records = {
        "sources": sources,
        "source_units": [],
        "chunks": chunks,
        "topic_candidates": candidates,
        "topic_review_source_ids": [],
        "excluded_inputs": [],
        "quality": {
            name: []
            for name in (
                "empty_locators",
                "unusable_locators",
                "reader_diagnostics",
                "extraction_failures",
                "chunk_mapping_issues",
                "pages",
                "sheets",
            )
        },
    }

    selected_ids = set(local_cli._select_v1_source_ids(records))
    assert len(selected_ids) == 24
    selected_formats = {
        row["suffix"] for row in sources if row["source_id"] in selected_ids
    }
    assert selected_formats == set(suffixes)

    filtered = local_cli._filter_records_to_sources(records, selected_ids)
    omitted_candidates = [
        row for row in candidates if row["source_id"] not in selected_ids
    ]
    review = local_cli._render_review(
        filtered, omitted_topic_candidates=omitted_candidates
    ).decode("utf-8")
    assert "Selected usable source formats: .docx, .md, .pdf, .xlsx." in review
    assert "omitted by the 24-source cap" in review.lower()
    for candidate in omitted_candidates:
        assert f"`{candidate['source_id']}` — {candidate['text']}" in review


def test_prepare_review_lists_content_topics_omitted_by_v1_cap(tmp_path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for index in range(30):
        (source_root / f"document-{index:02d}.md").write_text(
            f"# Unique generated topic {index:02d}\n\nGenerated body {index}.\n",
            encoding="utf-8",
        )
    local_root = tmp_path / "local"

    result = CliRunner().invoke(
        local_cli.main,
        [
            "prepare-review",
            "--source-root",
            str(source_root),
            "--source-root-label",
            "synthetic/sources",
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code == 0, result.output
    draft = local_root / "draft" / "v1"
    records = json.loads((draft / "records.json").read_bytes())
    selected_ids = {
        row["source_id"] for row in records["sources"] if row["status"] == "parsed"
    }
    # The candidate set persisted in records is selected-only; review text must
    # retain candidate pairs omitted by the selector cap.
    omitted = [
        row
        for row in local_cli.build_local_draft(
            source_root, tmp_path / "full-draft"
        ).topic_candidates
        if row.source_id not in selected_ids
    ]
    review = (draft / "REVIEW.md").read_text(encoding="utf-8")
    assert omitted
    for candidate in omitted:
        assert f"`{candidate.source_id}` — {candidate.text}" in review


def test_v1_review_preserves_failed_source_and_failed_canonical_duplicate(
    tmp_path, monkeypatch
):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    for index in range(20):
        (source_root / f"doc-{index:02d}.md").write_text(
            f"# Synthetic topic {index}\n\nGenerated usable document {index}.\n",
            encoding="utf-8",
        )
    failed_bytes = b"# Generated unreadable source\n\nSynthetic failure.\n"
    (source_root / "00-unreadable.md").write_bytes(failed_bytes)
    (source_root / "99-unreadable-copy.md").write_bytes(failed_bytes)

    real_loader = local_ingest._load_reader_documents

    def fail_generated_source(source, path):
        if source.relative_path == "00-unreadable.md":
            diagnostic = local_ingest._reader_diagnostic(
                source,
                None,
                ("TxtReader",),
                False,
                "file",
                needs_review=True,
                detail="synthetic reader failure",
            )
            return [], diagnostic, "SyntheticReaderError"
        return real_loader(source, path)

    monkeypatch.setattr(local_ingest, "_load_reader_documents", fail_generated_source)
    local_root = tmp_path / "local"

    result = CliRunner().invoke(
        local_cli.main,
        [
            "prepare-review",
            "--source-root",
            str(source_root),
            "--source-root-label",
            "synthetic/sources",
            "--local-root",
            str(local_root),
        ],
    )

    assert result.exit_code == 0, result.output
    records = json.loads((local_root / "draft" / "v1" / "records.json").read_bytes())
    source_by_path = {row["relative_path"]: row for row in records["sources"]}
    assert source_by_path["00-unreadable.md"]["status"] == "failed"
    assert source_by_path["99-unreadable-copy.md"]["status"] == "duplicate_bytes"
    assert source_by_path["99-unreadable-copy.md"]["duplicate_of"] == "00-unreadable.md"
    assert records["quality"]["extraction_failures"] == [
        {
            "relative_path": "00-unreadable.md",
            "source_id": source_by_path["00-unreadable.md"]["source_id"],
            "error_type": "SyntheticReaderError",
            "reason": "reader_failed",
        }
    ]
    excluded_by_path = {row["relative_path"]: row for row in records["excluded_inputs"]}
    assert set(excluded_by_path) == {"99-unreadable-copy.md"}
    assert "00-unreadable.md" not in excluded_by_path
    assert excluded_by_path["99-unreadable-copy.md"]["reason"] == "duplicate_bytes"
    assert (
        excluded_by_path["99-unreadable-copy.md"]["duplicate_of"] == "00-unreadable.md"
    )
    review = (local_root / "draft" / "v1" / "REVIEW.md").read_text(encoding="utf-8")
    assert "- Extraction failure: `00-unreadable.md` (`SyntheticReaderError`)" in review


def _write_complete_synthetic_draft(local_root: Path) -> Path:
    draft = local_root / "draft" / "v1"
    draft.mkdir(parents=True)
    source_bytes = b"generated-only CLI source bytes"
    source_id = hashlib.sha256(source_bytes).hexdigest()
    text = "Generated evidence passage."
    locator = {"unit_ordinal": 0}
    records = {
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
        "sources": [
            {
                "source_id": source_id,
                "relative_path": "notes.md",
                "sha256": source_id,
                "suffix": ".md",
                "byte_size": len(source_bytes),
                "duplicate_of": None,
                "selected_reader": "TxtReader",
                "reader_attempts": ["TxtReader"],
                "reader_fallback_used": False,
                "reader_granularity": "file",
                "status": "parsed",
            }
        ],
        "source_units": [
            {
                "unit_id": "unit-1",
                "source_id": source_id,
                "relative_path": "notes.md",
                "unit_ordinal": 0,
                "locator": locator,
                "text": text,
                "normalized_text": text,
            }
        ],
        "chunks": [
            {
                "chunk_id": "chunk-1",
                "source_id": source_id,
                "relative_path": "notes.md",
                "unit_id": "unit-1",
                "unit_ordinal": 0,
                "chunk_ordinal": 0,
                "locator": locator,
                "text": text,
                "char_start": 0,
                "char_end": len(text),
            }
        ],
        "topic_candidates": [],
        "topic_review_source_ids": [],
        "quality": {
            "empty_locators": [],
            "unusable_locators": [],
            "reader_diagnostics": [],
            "extraction_failures": [],
            "chunk_mapping_issues": [],
            "pages": [],
            "sheets": [],
        },
        "excluded_inputs": [],
    }
    records_payload = _json_bytes(records)
    judgment = {
        "schema_version": 1,
        "id": "q-1",
        "query": "What is the generated evidence?",
        "judgment_level": "source",
        "relevant_ids": [source_id],
        "disallowed_source_ids": [],
        "allowed_source_ids": [source_id],
        "path": None,
        "source_types": None,
        "filters": None,
        "case_kind": "named",
    }
    judgments_payload = _json_bytes(judgment)
    span = text.encode("utf-8")
    anchor = {
        "schema_version": 1,
        "id": "anchor-1",
        "query_id": "q-1",
        "source_id": source_id,
        "source_sha256": source_id,
        "unit_id": "unit-1",
        "locator": locator,
        "char_start": 0,
        "char_end": len(text),
        "evidence_sha256": hashlib.sha256(span).hexdigest(),
    }
    anchors_payload = _json_bytes(anchor)
    payloads = {
        "records.json": records_payload,
        "judgments.jsonl": judgments_payload,
        "anchors.jsonl": anchors_payload,
    }
    for name, payload in payloads.items():
        (draft / name).write_bytes(payload)
    manifest = {
        "schema_version": 1,
        "snapshot_version": "v1",
        "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
        "payload_sha256": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in payloads.items()
        },
        "review_status": "draft",
        "review_date": None,
        "source_root": "synthetic/sources",
        "source_provenance": [
            {
                "source_id": source_id,
                "repository_path": "synthetic/sources/notes.md",
                "sha256": source_id,
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
    (draft / "manifest.json").write_bytes(_json_bytes(manifest))
    return draft


def test_freeze_persists_approver_and_date_in_manifest_bound_sidecar(tmp_path):
    local_root = tmp_path / "local"
    draft = _write_complete_synthetic_draft(local_root)

    result = CliRunner().invoke(
        local_cli.main,
        [
            "freeze",
            "--draft-dir",
            str(draft),
            "--local-root",
            str(local_root),
            "--approved-by",
            "reviewer@example.invalid",
            "--approved-at",
            "2026-10-04",
        ],
    )

    assert result.exit_code == 0, result.output
    frozen = local_root / "snapshots" / "v1"
    snapshot_manifest = (frozen / "manifest.json").read_bytes()
    approval = json.loads((frozen / "approval.json").read_bytes())
    assert approval == {
        "approved_by": "reviewer@example.invalid",
        "approved_at": "2026-10-04",
        "snapshot_manifest_sha256": hashlib.sha256(snapshot_manifest).hexdigest(),
    }


def test_freeze_converts_v2_draft_to_strict_snapshot_manifest(tmp_path):
    local_root = tmp_path / "local"
    draft = _write_complete_synthetic_draft(local_root)
    candidate = local_root / "draft" / "v2" / "candidate"
    candidate.parent.mkdir(parents=True)
    draft.rename(candidate)

    draft_manifest_path = candidate / "manifest.json"
    draft_manifest = json.loads(draft_manifest_path.read_bytes())
    draft_manifest["snapshot_version"] = "v2-draft"
    del draft_manifest["schema_version"]
    draft_manifest["parent_manifest_sha256"] = hashlib.sha256(
        b"synthetic parent manifest"
    ).hexdigest()
    draft_manifest_path.write_bytes(_json_bytes(draft_manifest))

    result = CliRunner().invoke(
        local_cli.main,
        [
            "freeze",
            "--draft-dir",
            str(candidate),
            "--local-root",
            str(local_root),
            "--version",
            "v2",
            "--approved-by",
            "reviewer@example.invalid",
            "--approved-at",
            "2026-10-04",
        ],
    )

    assert result.exit_code == 0, result.output
    frozen = local_root / "snapshots" / "v2"
    local_snapshot.load_local_snapshot(frozen)
    manifest_bytes = (frozen / "manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    records = json.loads((frozen / "records.json").read_bytes())
    source = records["sources"][0]
    assert set(manifest) == local_snapshot._MANIFEST_FIELDS
    assert manifest["schema_version"] == 1
    assert manifest["snapshot_version"] == "v2"
    assert "parent_manifest_sha256" not in manifest
    assert manifest["source_root"] == "synthetic/sources"
    assert manifest["source_provenance"] == [
        {
            "source_id": source["source_id"],
            "repository_path": "synthetic/sources/notes.md",
            "sha256": source["sha256"],
        }
    ]
    assert manifest["counts"] == {
        "source_paths": 1,
        "documents": 1,
        "source_units": 1,
        "chunks": 1,
        "queries": 1,
        "anchors": 1,
    }
    assert manifest["payload_sha256"] == {
        name: hashlib.sha256((frozen / name).read_bytes()).hexdigest()
        for name in ("records.json", "judgments.jsonl", "anchors.jsonl")
    }
    approval = json.loads((frozen / "approval.json").read_bytes())
    assert (
        approval["snapshot_manifest_sha256"]
        == hashlib.sha256(manifest_bytes).hexdigest()
    )


def test_freeze_requires_both_approval_fields(tmp_path):
    local_root = tmp_path / "local"
    draft = local_root / "draft" / "v1"
    draft.mkdir(parents=True)
    result = CliRunner().invoke(
        local_cli.main,
        ["freeze", "--draft-dir", str(draft), "--local-root", str(local_root)],
    )

    assert result.exit_code != 0
    assert "--approved-by" in result.output
    with_approver = CliRunner().invoke(
        local_cli.main,
        [
            "freeze",
            "--draft-dir",
            str(draft),
            "--local-root",
            str(local_root),
            "--approved-by",
            "reviewer",
        ],
    )
    assert with_approver.exit_code != 0
    assert "--approved-at" in with_approver.output


def test_run_refuses_a_draft_snapshot_before_model_setup(tmp_path):
    local_root = tmp_path / "local"
    snapshot = local_root / "snapshots" / "draft-v1"
    snapshot.mkdir(parents=True)
    payload_hashes = {}
    for name in ("records.json", "judgments.jsonl", "anchors.jsonl"):
        payload = b""
        (snapshot / name).write_bytes(payload)
        payload_hashes[name] = hashlib.sha256(payload).hexdigest()
    (snapshot / "manifest.json").write_bytes(
        _json_bytes(
            {
                "schema_version": 1,
                "snapshot_version": "draft-v1",
                "schema_versions": {"records": 1, "judgments": 1, "anchors": 1},
                "payload_sha256": payload_hashes,
                "review_status": "draft",
                "review_date": None,
                "source_root": "synthetic/sources",
                "source_provenance": [],
                "parser_configuration": {},
                "splitter_configuration": {},
                "counts": {
                    "source_paths": 0,
                    "documents": 0,
                    "source_units": 0,
                    "chunks": 0,
                    "queries": 0,
                    "anchors": 0,
                },
            }
        )
    )

    result = CliRunner().invoke(
        local_cli.main,
        ["run", "--snapshot", str(snapshot), "--local-root", str(local_root)],
    )

    assert result.exit_code != 0
    assert "approved snapshot" in result.output.lower()


def test_model_manifest_resolves_exact_model_identity_and_provenance(tmp_path):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)

    paths = local_cli.resolve_model_paths(local_root, embedding_dir, reranker_dir)

    assert paths == LocalModelPaths(
        embedding_model_dir=embedding_dir,
        reranker_model_dir=reranker_dir,
        embedding_revision=EMBEDDING_REVISION,
        embedding_weight_source="cached",
        reranker_revision=RERANKER_REVISION,
        reranker_weight_source="downloaded",
    )
    with pytest.raises(ValueError, match="does not match"):
        local_cli.resolve_model_paths(local_root, reranker_dir, embedding_dir)


def test_model_manifest_rejects_missing_and_ambiguous_files(tmp_path):
    local_root = tmp_path / "local"
    models_root = local_root / "models"
    models_root.mkdir(parents=True)
    with pytest.raises(ValueError, match="manifest.*missing|missing.*manifest"):
        local_cli.resolve_model_paths(
            local_root, models_root / "embedding", models_root / "reranker"
        )

    _write_model_manifest(local_root)
    nested = models_root / "backup" / "model-manifest.json"
    nested.parent.mkdir()
    nested.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous|exactly one"):
        local_cli.resolve_model_paths(
            local_root, models_root / "bge-m3", models_root / "bge-reranker-v2-m3"
        )


def test_model_manifest_rejects_wrong_identity_revision_source_path_or_hash(tmp_path):
    mutations = [
        (lambda models: models[0].update(model_id="wrong/model"), "model_id"),
        (lambda models: models[0].update(revision="main"), "revision"),
        (lambda models: models[0].update(source="unknown"), "source"),
        (lambda models: models[0].update(directory="../outside"), "directory"),
        (
            lambda models: models[0]["weights_sha256"].update(
                {"model.safetensors": "0" * 64}
            ),
            "hash",
        ),
    ]
    for mutate, expected_message in mutations:
        case = tmp_path / expected_message
        local_root = case / "local"
        manifest_path, embedding_dir, reranker_dir = _write_model_manifest(local_root)
        manifest = json.loads(manifest_path.read_bytes())
        mutate(manifest["models"])
        manifest_path.write_bytes(_json_bytes(manifest))
        with pytest.raises(ValueError, match=expected_message):
            local_cli.resolve_model_paths(local_root, embedding_dir, reranker_dir)


def test_model_manifest_rejects_weight_tampering_and_duplicate_roles(tmp_path):
    local_root = tmp_path / "tampered"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    (embedding_dir / "model.safetensors").write_bytes(b"modified synthetic weights")
    with pytest.raises(ValueError, match="hash"):
        local_cli.resolve_model_paths(local_root, embedding_dir, reranker_dir)

    duplicate_root = tmp_path / "duplicate"
    manifest_path, embedding_dir, reranker_dir = _write_model_manifest(duplicate_root)
    manifest = json.loads(manifest_path.read_bytes())
    manifest["models"].append(dict(manifest["models"][0]))
    manifest_path.write_bytes(_json_bytes(manifest))
    with pytest.raises(ValueError, match="role|duplicate"):
        local_cli.resolve_model_paths(duplicate_root, embedding_dir, reranker_dir)


@pytest.mark.parametrize("asset_kind", ["config", "tokenizer", "added"])
def test_model_manifest_rejects_any_model_asset_tampering(tmp_path, asset_kind):
    local_root = tmp_path / asset_kind
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    if asset_kind == "config":
        (embedding_dir / "config.json").write_text('{"model_type":"changed"}')
    elif asset_kind == "tokenizer":
        (embedding_dir / "tokenizer.json").write_text('{"tokenizer":"changed"}')
    else:
        (embedding_dir / "extra-inference-asset.json").write_text("{}")

    with pytest.raises(ValueError, match="asset"):
        local_cli.resolve_model_paths(local_root, embedding_dir, reranker_dir)


def test_model_manifest_rejects_symlinked_model_assets_outside_local_root(tmp_path):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    external = tmp_path / "external-config.json"
    external.write_text("{}", encoding="utf-8")
    (embedding_dir / "config.json").unlink()
    (embedding_dir / "config.json").symlink_to(external)

    with pytest.raises(ValueError, match="symlink"):
        local_cli.resolve_model_paths(local_root, embedding_dir, reranker_dir)


def test_run_forwards_manifest_values_and_writes_only_under_runs(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    snapshot = local_root / "snapshots" / "approved-snapshot"
    snapshot.mkdir(parents=True)
    _write_approved_snapshot_sidecar(snapshot)
    captured = {}

    def fake_load_snapshot(path):
        assert Path(path) == snapshot
        return object()

    def fake_run(snapshot_object, *, model_paths, artifact_dir):
        captured["snapshot"] = snapshot_object
        captured["paths"] = model_paths
        captured["artifact_dir"] = Path(artifact_dir)
        Path(artifact_dir).mkdir(parents=True)
        (Path(artifact_dir) / "report.json").write_bytes(
            _json_bytes({"synthetic": True})
        )
        (Path(artifact_dir) / "artifact-manifest.json").write_bytes(
            _json_bytes(
                {
                    "schema_version": 1,
                    "snapshot_fingerprint": "synthetic",
                    "arm_configurations": {},
                    "artifacts": [],
                }
            )
        )
        return object()

    monkeypatch.setattr(local_cli, "load_local_snapshot", fake_load_snapshot)
    monkeypatch.setattr(local_cli, "run_local_experiment", fake_run)
    preflight_calls = []
    monkeypatch.setattr(
        local_cli,
        "_require_offline_inference_process",
        lambda: preflight_calls.append("checked"),
    )
    result = CliRunner().invoke(
        local_cli.main,
        [
            "run",
            "--snapshot",
            str(snapshot),
            "--local-root",
            str(local_root),
            "--embedding-model-dir",
            str(embedding_dir),
            "--reranker-model-dir",
            str(reranker_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["paths"].embedding_revision == EMBEDDING_REVISION
    assert captured["paths"].embedding_weight_source == "cached"
    assert captured["paths"].reranker_revision == RERANKER_REVISION
    assert captured["paths"].reranker_weight_source == "downloaded"
    assert captured["artifact_dir"].is_relative_to(local_root / "runs")
    assert preflight_calls == ["checked"]
    final_artifacts = local_root / "runs" / snapshot.name
    copied_manifest = final_artifacts / "model-manifest.json"
    manifest_bytes = (local_root / "models" / "model-manifest.json").read_bytes()
    assert copied_manifest.read_bytes() == manifest_bytes
    artifact_manifest = json.loads(
        (final_artifacts / "artifact-manifest.json").read_bytes()
    )
    linked_model_entry = next(
        row
        for row in artifact_manifest["artifacts"]
        if row["path"] == "model-manifest.json"
    )
    assert linked_model_entry == {
        "path": "model-manifest.json",
        "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "size_bytes": len(manifest_bytes),
        "kind": "verified_model_manifest",
    }
    assert list((local_root / "runs").iterdir()) == [final_artifacts]


@pytest.mark.parametrize("error_type", [RuntimeError, ImportError])
def test_run_offline_preflight_failure_is_actionable_and_prevents_experiment(
    tmp_path, monkeypatch, error_type
):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    snapshot = local_root / "snapshots" / "approved-v1"
    snapshot.mkdir(parents=True)
    _write_approved_snapshot_sidecar(snapshot)
    calls = []
    monkeypatch.setattr(local_cli, "load_local_snapshot", lambda path: object())

    def fail_preflight():
        calls.append("preflight")
        raise error_type(
            "Local inference requires HF_HUB_OFFLINE=1 and "
            "TRANSFORMERS_OFFLINE=1 in a fresh process"
        )

    monkeypatch.setattr(local_cli, "_require_offline_inference_process", fail_preflight)
    monkeypatch.setattr(
        local_cli,
        "run_local_experiment",
        lambda *args, **kwargs: calls.append("experiment"),
    )
    result = CliRunner().invoke(
        local_cli.main,
        [
            "run",
            "--snapshot",
            str(snapshot),
            "--local-root",
            str(local_root),
            "--embedding-model-dir",
            str(embedding_dir),
            "--reranker-model-dir",
            str(reranker_dir),
        ],
    )

    assert result.exit_code != 0
    assert "fresh process" in result.output.lower()
    assert "HF_HUB_OFFLINE=1" in result.output
    assert calls == ["preflight"]
    assert not (local_root / "runs").exists()


def test_run_does_not_publish_partial_artifact_bundle(tmp_path, monkeypatch):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    snapshot = local_root / "snapshots" / "approved-v1"
    snapshot.mkdir(parents=True)
    _write_approved_snapshot_sidecar(snapshot)
    monkeypatch.setattr(local_cli, "load_local_snapshot", lambda path: object())
    monkeypatch.setattr(local_cli, "_require_offline_inference_process", lambda: None)

    def incomplete_run(snapshot_object, *, model_paths, artifact_dir):
        Path(artifact_dir).mkdir(parents=True)
        (Path(artifact_dir) / "report.json").write_bytes(_json_bytes({"partial": True}))

    monkeypatch.setattr(local_cli, "run_local_experiment", incomplete_run)
    result = CliRunner().invoke(
        local_cli.main,
        [
            "run",
            "--snapshot",
            str(snapshot),
            "--local-root",
            str(local_root),
            "--embedding-model-dir",
            str(embedding_dir),
            "--reranker-model-dir",
            str(reranker_dir),
        ],
    )

    runs_root = local_root / "runs"
    assert result.exit_code != 0
    assert "artifact-manifest" in result.output.lower()
    assert not (runs_root / snapshot.name).exists()
    assert not any(path.name.startswith(".") for path in runs_root.iterdir())


def test_run_rejects_an_invalid_approval_sidecar_before_experiment(
    tmp_path, monkeypatch
):
    local_root = tmp_path / "local"
    _, embedding_dir, reranker_dir = _write_model_manifest(local_root)
    snapshot = local_root / "snapshots" / "approved-v1"
    snapshot.mkdir(parents=True)
    _write_approved_snapshot_sidecar(snapshot, manifest_hash="0" * 64)
    called = []
    monkeypatch.setattr(local_cli, "load_local_snapshot", lambda path: object())
    monkeypatch.setattr(
        local_cli,
        "run_local_experiment",
        lambda *args, **kwargs: called.append(True),
    )

    result = CliRunner().invoke(
        local_cli.main,
        [
            "run",
            "--snapshot",
            str(snapshot),
            "--local-root",
            str(local_root),
            "--embedding-model-dir",
            str(embedding_dir),
            "--reranker-model-dir",
            str(reranker_dir),
        ],
    )

    assert result.exit_code != 0
    assert "approval sidecar" in result.output.lower()
    assert not called


def test_download_models_checks_offline_cache_before_network_and_records_full_manifest(
    tmp_path, monkeypatch
):
    local_root = tmp_path / "local"
    cached_revision = "c" * 40
    downloaded_revision = "d" * 40
    cached_snapshot = tmp_path / "hf-cache" / "snapshots" / cached_revision
    _fake_model_directory(cached_snapshot, b"cached synthetic weights")
    (cached_snapshot / "pytorch_model.bin").write_bytes(b"second cached shard")
    cache_bookkeeping = cached_snapshot / ".cache" / "huggingface" / "download"
    cache_bookkeeping.mkdir(parents=True)
    (cache_bookkeeping / "config.json.metadata").write_text("cached", encoding="utf-8")
    events = []

    def offline_lookup(model_id):
        events.append(("offline", model_id))
        return cached_snapshot if model_id == EMBEDDING_ID else None

    def resolve_revision(model_id):
        events.append(("resolve", model_id))
        return downloaded_revision

    def download_snapshot(model_id, revision, destination):
        events.append(("download", model_id))
        assert revision == downloaded_revision
        path = Path(destination)
        path.mkdir(parents=True)
        (path / "config.json").write_text("{}", encoding="utf-8")
        (path / "tokenizer.json").write_text("{}", encoding="utf-8")
        (path / "tokenizer_config.json").write_text("{}", encoding="utf-8")
        (path / "special_tokens_map.json").write_text("{}", encoding="utf-8")
        (path / "vocab.txt").write_text("synthetic-token\n", encoding="utf-8")
        (path / "model.safetensors").write_bytes(b"downloaded synthetic weights")
        return path

    monkeypatch.setattr(local_cli, "_offline_hub_snapshot", offline_lookup)
    monkeypatch.setattr(local_cli, "_resolve_hub_revision", resolve_revision)
    monkeypatch.setattr(local_cli, "_download_hub_snapshot", download_snapshot)
    result = CliRunner().invoke(
        local_cli.main,
        ["download-models", "--local-root", str(local_root)],
    )

    assert result.exit_code == 0, result.output
    assert events == [
        ("offline", EMBEDDING_ID),
        ("offline", RERANKER_ID),
        ("resolve", RERANKER_ID),
        ("download", RERANKER_ID),
    ]
    manifest = json.loads((local_root / "models" / "model-manifest.json").read_bytes())
    assert [row["role"] for row in manifest["models"]] == ["embedding", "reranker"]
    embedding, reranker = manifest["models"]
    assert (embedding["model_id"], embedding["revision"], embedding["source"]) == (
        EMBEDDING_ID,
        cached_revision,
        "cached",
    )
    assert (reranker["model_id"], reranker["revision"], reranker["source"]) == (
        RERANKER_ID,
        downloaded_revision,
        "downloaded",
    )
    assert embedding["directory"] == "bge-m3"
    assert reranker["directory"] == "bge-reranker-v2-m3"
    assert list(embedding["weights_sha256"]) == sorted(embedding["weights_sha256"])
    assert set(embedding["weights_sha256"]) == {
        "model.safetensors",
        "pytorch_model.bin",
    }
    assert list(embedding["assets_sha256"]) == sorted(embedding["assets_sha256"])
    assert set(embedding["assets_sha256"]) == {
        "config.json",
        "model.safetensors",
        "pytorch_model.bin",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    }
    assert not any(
        name.startswith(".cache/huggingface/") for name in embedding["assets_sha256"]
    )
    assert set(reranker["weights_sha256"]) == {"model.safetensors"}
    assert set(reranker["assets_sha256"]) == {
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    }
