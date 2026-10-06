"""Synthetic integration tests for the read-only local QA retrieval core."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import pytest
from ktem import local_qa_core
from ktem.local_qa_core import EvidenceCard, LocalQA, open_playground
from ktem.local_qa_ollama import OllamaLocalClient

from kotaemon.base import Document, DocumentWithEmbedding, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.evaluation.local_models import LocalModelPaths
from kotaemon.indices.knowledge.evaluation.local_snapshot import load_local_snapshot
from kotaemon.indices.knowledge.retrieval.context_budget import GenerationBudget


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def _jsonl_bytes(rows):
    return b"".join(_json_bytes(row) for row in rows)


def _write_reviewed_snapshot(
    root: Path,
    *,
    source0_text: str | None = None,
    splitter_configuration: dict | None = None,
) -> tuple[Path, tuple[str, ...]]:
    """Write only synthetic snapshot payloads, following the evaluator fixture."""
    root.mkdir(parents=True)
    sources = []
    units = []
    chunks = []
    provenance = []
    source_ids = []
    for index in range(7):
        relative_path = f"collection/doc-{index}.md"
        source_bytes = f"generated synthetic source {index}".encode()
        source_id = hashlib.sha256(source_bytes).hexdigest()
        source_ids.append(source_id)
        text = source0_text or (
            "alpha unique target phrase"
            if index == 0
            else f"unrelated synthetic source content {index}"
        )
        unit_id = f"unit-{index}"
        locator = {"page_label": "1"}
        sources.append(
            {
                "source_id": source_id,
                "relative_path": relative_path,
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
        )
        units.append(
            {
                "unit_id": unit_id,
                "source_id": source_id,
                "relative_path": relative_path,
                "unit_ordinal": 0,
                "locator": locator,
                "text": text,
                "normalized_text": text,
            }
        )
        chunks.append(
            {
                "chunk_id": f"snapshot-chunk-{index}",
                "source_id": source_id,
                "relative_path": relative_path,
                "unit_id": unit_id,
                "unit_ordinal": 0,
                "chunk_ordinal": 0,
                "locator": locator,
                "text": text,
                "char_start": 0,
                "char_end": len(text),
            }
        )
        provenance.append(
            {
                "source_id": source_id,
                "repository_path": f"synthetic-sources/{relative_path}",
                "sha256": source_id,
            }
        )

    splitter_configuration = splitter_configuration or {
        "version": "main-token-only-v1",
        "name": "TokenSplitter",
        "chunk_size": 1024,
        "chunk_overlap": 256,
        "separator": "\n\n",
        "backup_separators": ["\n", ".", " ", "\u200b"],
    }
    records = {
        "schema_version": 1,
        "parser_configuration": {".md": "TxtReader"},
        "splitter_configuration": splitter_configuration,
        "sources": sources,
        "source_units": units,
        "chunks": chunks,
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
    judgment = {
        "schema_version": 1,
        "id": "q-alpha",
        "query": "alpha unique target phrase",
        "judgment_level": "source",
        "relevant_ids": [source_ids[0]],
        "disallowed_source_ids": source_ids[1:],
        "allowed_source_ids": None,
        "path": None,
        "source_types": ["markdown"],
        "filters": None,
        "case_kind": "named",
    }
    anchor = {
        "schema_version": 1,
        "id": "anchor-alpha",
        "query_id": "q-alpha",
        "source_id": source_ids[0],
        "source_sha256": source_ids[0],
        "unit_id": "unit-0",
        "locator": {"page_label": "1"},
        "char_start": 0,
        "char_end": len("alpha unique target phrase"),
        "evidence_sha256": hashlib.sha256(b"alpha unique target phrase").hexdigest(),
    }
    payloads = {
        "records.json": _json_bytes(records),
        "judgments.jsonl": _jsonl_bytes([judgment]),
        "anchors.jsonl": _jsonl_bytes([anchor]),
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
        "source_root": "synthetic-sources",
        "source_provenance": provenance,
        "parser_configuration": records["parser_configuration"],
        "splitter_configuration": records["splitter_configuration"],
        "counts": {
            "source_paths": len(sources),
            "documents": len(sources),
            "source_units": len(units),
            "chunks": len(chunks),
            "queries": 1,
            "anchors": 1,
        },
    }
    manifest_bytes = _json_bytes(manifest)
    (root / "manifest.json").write_bytes(manifest_bytes)
    approval = {
        "approved_by": "synthetic reviewer",
        "approved_at": "2026-10-03",
        "snapshot_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    (root / "approval.json").write_bytes(_json_bytes(approval))
    return root, tuple(source_ids)


def reviewed_fixture(
    base: Path,
    *,
    source0_text: str | None = None,
    splitter_configuration: dict | None = None,
):
    local_root = base / "local-root"
    snapshots_root = local_root / "snapshots"
    snapshots_root.mkdir(parents=True)
    models_root = local_root / "models"
    embedding_dir = models_root / "synthetic-embedding"
    reranker_dir = models_root / "synthetic-reranker"
    embedding_dir.mkdir(parents=True)
    reranker_dir.mkdir()
    snapshot_dir, source_ids = _write_reviewed_snapshot(
        snapshots_root / "reviewed-v1",
        source0_text=source0_text,
        splitter_configuration=splitter_configuration,
    )
    return local_root, snapshot_dir, embedding_dir, reranker_dir, source_ids


def snapshot_tree(root: Path):
    """Capture tree shape and bytes to prove startup and search make no writes."""
    state = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            state[relative] = ("symlink", path.readlink().as_posix())
        elif path.is_dir():
            state[relative] = ("directory",)
        else:
            state[relative] = ("file", path.read_bytes())
    return state


class CountingEmbedding(BaseEmbeddings):
    """Deterministic real embedding component for in-memory indexing/search."""

    def __init__(self):
        super().__init__()
        object.__setattr__(self, "document_batches", 0)
        object.__setattr__(self, "query_calls", 0)

    def run(self, text, *args, **kwargs):
        if isinstance(text, list):
            object.__setattr__(self, "document_batches", self.document_batches + 1)
            values = text
        else:
            object.__setattr__(self, "query_calls", self.query_calls + 1)
            values = [text]
        result = []
        for value in values:
            document = value if isinstance(value, Document) else Document(content=value)
            result.append(
                DocumentWithEmbedding(content=document, embedding=[1.0, 0.0, 0.0])
            )
        return result


def fake_model_paths(_local_root, embedding_model_dir, reranker_model_dir):
    return LocalModelPaths(
        embedding_model_dir=embedding_model_dir,
        reranker_model_dir=reranker_model_dir,
        embedding_revision="synthetic-embedding-revision",
        embedding_weight_source="cached",
        reranker_revision="synthetic-reranker-revision",
        reranker_weight_source="cached",
    )


def patch_offline_model_gates(monkeypatch):
    monkeypatch.setattr(local_qa_core, "resolve_model_paths", fake_model_paths)
    monkeypatch.setattr(
        local_qa_core, "_require_offline_inference_process", lambda: None
    )


def test_open_playground_builds_index_once_and_does_not_write(tmp_path, monkeypatch):
    local_root, snapshot_dir, embedding_dir, reranker_dir, _source_ids = (
        reviewed_fixture(tmp_path)
    )
    before = snapshot_tree(local_root)
    embedding = CountingEmbedding()
    patch_offline_model_gates(monkeypatch)

    qa = open_playground(
        local_root,
        snapshot_dir,
        embedding_dir,
        reranker_dir,
        embedding_factory=lambda *args, **kwargs: embedding,
    )
    cards = qa.retrieve("alpha unique target phrase")

    assert embedding.document_batches == 1
    assert embedding.query_calls == 1
    assert cards
    assert all(card.source_label for card in cards)
    assert snapshot_tree(local_root) == before


def test_evidence_card_is_frozen():
    card = EvidenceCard(
        source_rank=1,
        chunk_rank=1,
        source_id="synthetic-source",
        source_label="collection/doc.md",
        locator={"page_label": "1"},
        score=0.5,
        text="synthetic evidence",
    )

    with pytest.raises(FrozenInstanceError):
        card.text = "changed"


def _assert_startup_rejected_before_embedding(
    monkeypatch,
    *,
    local_root,
    snapshot_dir,
    embedding_dir,
    reranker_dir,
    error_match,
):
    patch_offline_model_gates(monkeypatch)
    embedding_calls = []

    def embedding_factory(*args, **kwargs):
        embedding_calls.append((args, kwargs))
        return CountingEmbedding()

    with pytest.raises(ValueError, match=error_match):
        open_playground(
            local_root,
            snapshot_dir,
            embedding_dir,
            reranker_dir,
            embedding_factory=embedding_factory,
        )
    assert embedding_calls == []


def test_open_playground_rejects_invalid_approval_before_embedding(
    tmp_path, monkeypatch
):
    local_root, snapshot_dir, embedding_dir, reranker_dir, _ = reviewed_fixture(
        tmp_path
    )
    approval_path = snapshot_dir / "approval.json"
    approval = json.loads(approval_path.read_text())
    approval["snapshot_manifest_sha256"] = "0" * 64
    approval_path.write_bytes(_json_bytes(approval))

    _assert_startup_rejected_before_embedding(
        monkeypatch,
        local_root=local_root,
        snapshot_dir=snapshot_dir,
        embedding_dir=embedding_dir,
        reranker_dir=reranker_dir,
        error_match="approval sidecar manifest hash mismatch",
    )


def test_open_playground_rejects_modified_snapshot_payload_before_embedding(
    tmp_path, monkeypatch
):
    local_root, snapshot_dir, embedding_dir, reranker_dir, _ = reviewed_fixture(
        tmp_path
    )
    records_path = snapshot_dir / "records.json"
    records_path.write_bytes(records_path.read_bytes() + b" ")

    _assert_startup_rejected_before_embedding(
        monkeypatch,
        local_root=local_root,
        snapshot_dir=snapshot_dir,
        embedding_dir=embedding_dir,
        reranker_dir=reranker_dir,
        error_match="records.json payload hash mismatch",
    )


def test_open_playground_rejects_snapshot_outside_snapshots_before_embedding(
    tmp_path, monkeypatch
):
    local_root, _snapshot_dir, embedding_dir, reranker_dir, _ = reviewed_fixture(
        tmp_path
    )
    outside_snapshot, _ = _write_reviewed_snapshot(tmp_path / "outside-snapshot")

    _assert_startup_rejected_before_embedding(
        monkeypatch,
        local_root=local_root,
        snapshot_dir=outside_snapshot,
        embedding_dir=embedding_dir,
        reranker_dir=reranker_dir,
        error_match="snapshot must resolve beneath the selected local root",
    )


def test_open_playground_rejects_symlinked_snapshot_path_before_embedding(
    tmp_path, monkeypatch
):
    local_root, snapshot_dir, embedding_dir, reranker_dir, _ = reviewed_fixture(
        tmp_path
    )
    linked_snapshot = snapshot_dir.parent / "snapshot-link"
    linked_snapshot.symlink_to(snapshot_dir, target_is_directory=True)

    _assert_startup_rejected_before_embedding(
        monkeypatch,
        local_root=local_root,
        snapshot_dir=linked_snapshot,
        embedding_dir=embedding_dir,
        reranker_dir=reranker_dir,
        error_match="must not contain a symlink",
    )


def test_open_playground_rejects_nonbaseline_splitter_before_embedding(
    tmp_path, monkeypatch
):
    local_root, snapshot_dir, embedding_dir, reranker_dir, _ = reviewed_fixture(
        tmp_path,
        splitter_configuration={
            "version": "main-token-only-v1",
            "name": "TokenSplitter",
            "chunk_size": 512,
            "chunk_overlap": 256,
            "separator": "\n\n",
            "backup_separators": ["\n", ".", " ", "\u200b"],
        },
    )

    _assert_startup_rejected_before_embedding(
        monkeypatch,
        local_root=local_root,
        snapshot_dir=snapshot_dir,
        embedding_dir=embedding_dir,
        reranker_dir=reranker_dir,
        error_match="required baseline splitter configuration",
    )


class CandidateService:
    def __init__(self, candidates):
        self.candidates = candidates
        self.queries = []

    def search(self, question, *, top_k):
        self.queries.append((question, top_k))
        return self.candidates[:top_k]


@pytest.fixture
def fake_qa(tmp_path):
    local_root, snapshot_dir, _embedding_dir, _reranker_dir, source_ids = (
        reviewed_fixture(tmp_path)
    )
    snapshot = load_local_snapshot(snapshot_dir)
    candidate_sources = [
        source_ids[0],
        source_ids[1],
        source_ids[0],
        source_ids[2],
        source_ids[3],
        source_ids[4],
        source_ids[5],
        source_ids[1],
    ]
    candidates = [
        RetrievedDocument(
            text=f"candidate text {index}",
            id_=f"candidate-{index}",
            score=(float("nan") if index == 4 else index / 10),
        )
        for index in range(len(candidate_sources))
    ]
    service = CandidateService(candidates)
    bundle = {
        "chunk_to_source": {
            candidate.doc_id: source_id
            for candidate, source_id in zip(candidates, candidate_sources)
        },
        "draft_chunks": {
            candidate.doc_id: SimpleNamespace(locator={"page_label": str(index + 1)})
            for index, candidate in enumerate(candidates)
        },
        "unresolved_offsets": {},
    }
    qa = LocalQA(snapshot=snapshot, bundle=bundle, service=service)
    return qa, service, source_ids


def test_retrieve_projects_first_five_sources_in_candidate_order(fake_qa):
    qa, service, source_ids = fake_qa

    cards = qa.retrieve("question")

    assert [card.source_rank for card in cards] == [1, 2, 1, 3, 4, 5, 2]
    assert [card.chunk_rank for card in cards] == [1, 2, 3, 4, 5, 6, 8]
    assert [card.source_id for card in cards] == [
        source_ids[0],
        source_ids[1],
        source_ids[0],
        source_ids[2],
        source_ids[3],
        source_ids[4],
        source_ids[1],
    ]
    assert [card.source_label for card in cards] == [
        "collection/doc-0.md",
        "collection/doc-1.md",
        "collection/doc-0.md",
        "collection/doc-2.md",
        "collection/doc-3.md",
        "collection/doc-4.md",
        "collection/doc-1.md",
    ]
    assert [card.locator for card in cards] == [
        {"page_label": str(rank)} for rank in (1, 2, 3, 4, 5, 6, 8)
    ]
    assert cards[3].score == 0.3
    assert cards[4].score is None
    assert service.queries == [("question", 20)]
    assert all(not Path(card.source_label).is_absolute() for card in cards)


def test_local_packer_accounts_for_exact_ollama_messages_and_reserves(fake_qa):
    qa, _service, _source_ids = fake_qa
    question = "What does the guide say?"
    history = ("Earlier question?",)
    output_reserve = 8
    format_reserve = 3
    unbounded_client = OllamaLocalClient(
        model="synthetic:local",
        output_reserve=output_reserve,
        format_reserve=format_reserve,
        count_tokens=len,
    )
    cards = qa.retrieve(question, user_history=history)
    baseline_body = unbounded_client._request_body(
        question, cards, stream=False, user_history=history
    )
    baseline_messages = json.loads(baseline_body)["messages"]
    exact_message_tokens = len(
        json.dumps(
            baseline_messages,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    )
    model_context = exact_message_tokens + output_reserve + format_reserve - 1
    client = OllamaLocalClient(
        model="synthetic:local",
        model_context=model_context,
        output_reserve=output_reserve,
        format_reserve=format_reserve,
        count_tokens=len,
    )

    packed = qa.retrieve_result(
        question,
        user_history=history,
        generation_budget=GenerationBudget(
            model_context=model_context,
            output_reserve=output_reserve,
            format_reserve=format_reserve,
        ),
        count_tokens=len,
        base_prompt=client.base_prompt(question),
    )

    request_body = client._request_body(
        question, packed.cards, stream=False, user_history=history
    )
    request_messages = json.loads(request_body)["messages"]
    request_tokens = len(
        json.dumps(
            request_messages,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    )
    assert request_tokens + output_reserve + format_reserve <= model_context


def test_retrieve_returns_empty_tuple_without_candidates(fake_qa):
    qa, service, _source_ids = fake_qa
    service.candidates = []

    assert qa.retrieve("question") == ()
    assert service.queries == [("question", 20)]


@pytest.mark.parametrize("question", ["", "   ", None])
def test_retrieve_rejects_empty_question(fake_qa, question):
    qa, service, _source_ids = fake_qa

    with pytest.raises(ValueError, match="question must not be empty"):
        qa.retrieve(question)
    assert service.queries == []


def test_ambiguous_repeated_chunk_uses_recorded_locator(tmp_path, monkeypatch):
    repeated_text = "alpha unique target phrase " * 1500
    local_root, snapshot_dir, embedding_dir, reranker_dir, source_ids = (
        reviewed_fixture(tmp_path, source0_text=repeated_text)
    )
    embedding = CountingEmbedding()
    patch_offline_model_gates(monkeypatch)
    qa = open_playground(
        local_root,
        snapshot_dir,
        embedding_dir,
        reranker_dir,
        embedding_factory=lambda *args, **kwargs: embedding,
    )

    question = "alpha unique target phrase"
    cards = qa.retrieve(question)
    unresolved_cards = [
        card
        for card in cards
        if card.source_id == source_ids[0]
        and card.chunk_id in qa._bundle["unresolved_offsets"]
    ]

    assert unresolved_cards
    assert all(
        card.locator == dict(qa._bundle["unresolved_offsets"][card.chunk_id].locator)
        for card in unresolved_cards
    )
