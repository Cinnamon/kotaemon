"""Integration contracts for the shared v3 runtime and opt-in entry points."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from ktem import local_qa_core
from ktem.index.file.pipelines import DocumentRetrievalPipeline
from ktem.local_qa_core import EvidenceCard
from ktem.local_qa_playground import answer_question

from kotaemon.base import DocumentWithEmbedding, RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.evaluation.local_snapshot import LocalSnapshot
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.indices.rankings import BaseReranking
from kotaemon.models.local_bge import LocalModelPaths

_SPLITTER = {
    "version": "main-token-only-v1",
    "name": "TokenSplitter",
    "chunk_size": 1024,
    "chunk_overlap": 256,
    "separator": "\n\n",
    "backup_separators": ["\n", ".", " ", "\u200b"],
}


class ConstantEmbeddings(BaseEmbeddings):
    def run(self, text, *args, **kwargs):
        documents = self.prepare_input(text)
        return [
            DocumentWithEmbedding(content=document, embedding=[1.0, 0.0, 0.0])
            for document in documents
        ]


class ReverseReranker(BaseReranking):
    def __init__(self):
        super().__init__()
        object.__setattr__(self, "calls", [])

    @property
    def name(self):
        return "synthetic-reverse-reranker"

    def run(self, documents, query):
        self.calls.append((query, tuple(document.doc_id for document in documents)))
        return list(reversed(documents))


def _snapshot(tmp_path: Path, *, text: str | None = None) -> LocalSnapshot:
    source_bytes = b"synthetic approved source bytes"
    source_id = hashlib.sha256(source_bytes).hexdigest()
    text = text or "# First\n\nTarget passage one.\n\n# Second\n\nTarget passage two."
    source = {
        "source_id": source_id,
        "relative_path": "guide.md",
        "sha256": source_id,
        "suffix": ".md",
        "byte_size": len(source_bytes),
    }
    unit = {
        "unit_id": "unit-guide-0",
        "source_id": source_id,
        "relative_path": "guide.md",
        "unit_ordinal": 0,
        "locator": {"page_label": "1"},
        "text": text,
        "normalized_text": text,
    }
    return LocalSnapshot(
        root=tmp_path,
        records={"source_units": (unit,), "splitter_configuration": _SPLITTER},
        sources=(source,),
        canonical_sources=(source,),
        selected_sources=(source,),
        judgments=None,
        anchors=(),
        fingerprint=hashlib.sha256(b"synthetic snapshot manifest").hexdigest(),
    )


def _query_ids(service) -> tuple[str, ...]:
    return tuple(
        document.doc_id for document in service.search("Target passage", top_k=20)
    )


def test_core_runtime_does_not_import_evaluation():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import kotaemon.indices.knowledge.runtime.index; "
                "assert not any(name == 'kotaemon.indices.knowledge.evaluation' "
                "or name.startswith('kotaemon.indices.knowledge.evaluation.') "
                "for name in sys.modules)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_snapshot_builder_token_and_registry_modes_are_distinct(tmp_path):
    from kotaemon.indices.knowledge.evaluation.snapshot_adapter import (
        build_snapshot_runtime,
    )

    snapshot = _snapshot(tmp_path)
    token = build_snapshot_runtime(
        snapshot,
        embedding=ConstantEmbeddings(),
        reranker=None,
        policy=RetrievalPolicy(),
        chunking_mode="token",
    )
    registry = build_snapshot_runtime(
        snapshot,
        embedding=ConstantEmbeddings(),
        reranker=None,
        policy=RetrievalPolicy(),
        chunking_mode="registry",
    )

    assert token.config["chunking_mode"] == "token"
    assert registry.config["chunking_mode"] == "registry"
    assert tuple(document.doc_id for document in token.documents) != tuple(
        document.doc_id for document in registry.documents
    )
    assert all(
        document.metadata.get("source_version")
        == snapshot.selected_sources[0]["sha256"]
        for document in registry.documents
    )
    token.close()
    registry.close()


def test_frozen_v2_token_and_registry_wrappers_retain_candidate_ids(tmp_path):
    from kotaemon.indices.knowledge.evaluation.local_experiment import (
        _make_bundle,
        _service,
    )
    from kotaemon.indices.knowledge.evaluation.snapshot_adapter import (
        build_snapshot_runtime,
    )

    snapshot = _snapshot(tmp_path)
    for chunking_arm, mode in ((False, "token"), (True, "registry")):
        bundle = _make_bundle(
            snapshot,
            embedding=ConstantEmbeddings(),
            chunking_arm=chunking_arm,
        )
        legacy_ids = _query_ids(_service(bundle))
        runtime = build_snapshot_runtime(
            snapshot,
            embedding=ConstantEmbeddings(),
            reranker=None,
            policy=RetrievalPolicy(),
            chunking_mode=mode,
        )
        assert _query_ids(runtime.service) == legacy_ids
        runtime.close()


def test_frozen_v2_reranker_wrapper_retains_candidate_order(tmp_path):
    from kotaemon.indices.knowledge.evaluation.local_experiment import (
        _make_bundle,
        _service,
    )

    bundle = _make_bundle(
        _snapshot(tmp_path), embedding=ConstantEmbeddings(), chunking_arm=False
    )
    initial = _query_ids(_service(bundle))
    reranker = ReverseReranker()
    reranked = _query_ids(_service(bundle, rerankers=(reranker,)))

    assert reranker.calls == [("Target passage", initial)]
    assert reranked == tuple(reversed(initial))


def _prepare_open_playground(monkeypatch, tmp_path, snapshot):
    snapshots_root = tmp_path / "snapshots"
    snapshots_root.mkdir(exist_ok=True)
    snapshot_path = snapshots_root / "approved-v1"
    snapshot_path.mkdir(exist_ok=True)
    model_paths = LocalModelPaths(
        embedding_model_dir=tmp_path / "embedding",
        reranker_model_dir=tmp_path / "reranker",
        embedding_revision="embedding-revision",
        embedding_weight_source="cached",
        reranker_revision="reranker-revision",
        reranker_weight_source="cached",
    )
    monkeypatch.setattr(
        local_qa_core, "_require_ignored_repo_local_root", lambda _: None
    )
    monkeypatch.setattr(local_qa_core, "_ensure_contained", lambda path, *_: Path(path))
    monkeypatch.setattr(
        local_qa_core, "_reject_symlink_components", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(local_qa_core, "_validate_snapshot_approval", lambda *_: None)
    monkeypatch.setattr(
        local_qa_core, "load_local_snapshot", lambda *_args, **_kwargs: snapshot
    )
    monkeypatch.setattr(local_qa_core, "_validate_baseline_splitter", lambda *_: None)
    monkeypatch.setattr(
        local_qa_core, "resolve_model_paths", lambda *_args: model_paths
    )
    monkeypatch.setattr(local_qa_core, "_validate_model_provenance", lambda *_: None)
    monkeypatch.setattr(
        local_qa_core, "_require_offline_inference_process", lambda: None
    )
    return snapshot_path, model_paths


def test_workbench_uses_public_runtime_and_reranker(monkeypatch, tmp_path):
    from kotaemon.indices.knowledge.evaluation import snapshot_adapter

    snapshot = _snapshot(tmp_path)
    snapshot_path, model_paths = _prepare_open_playground(
        monkeypatch, tmp_path, snapshot
    )
    reranker = ReverseReranker()
    reranker_arguments = []

    def make_reranker(**kwargs):
        reranker_arguments.append(kwargs)
        return reranker

    monkeypatch.setattr(local_qa_core, "BgeM3Reranking", make_reranker, raising=False)
    runtime_calls = []
    build_runtime = snapshot_adapter.build_snapshot_runtime

    def capture_runtime(*args, **kwargs):
        runtime_calls.append(kwargs)
        return build_runtime(*args, **kwargs)

    monkeypatch.setattr(snapshot_adapter, "build_snapshot_runtime", capture_runtime)
    qa = local_qa_core.open_playground(
        tmp_path,
        snapshot_path,
        model_paths.embedding_model_dir,
        model_paths.reranker_model_dir,
        embedding_factory=lambda *_args, **_kwargs: ConstantEmbeddings(),
    )

    assert reranker_arguments[0]["revision"] == "reranker-revision"
    assert runtime_calls[0]["reranker"] is reranker
    assert runtime_calls[0]["lexical"] is True
    assert reranker in qa._service.retriever.rerankers


def test_fts_unavailable_shows_degraded_stack(monkeypatch, tmp_path):
    from ktem.local_qa_core import LocalQA

    from kotaemon.indices.knowledge.evaluation.snapshot_adapter import (
        build_snapshot_runtime,
    )
    from kotaemon.storages import InMemoryDocumentStore

    class NoFtsDocumentStore(InMemoryDocumentStore):
        supports_lexical_search = False

    monkeypatch.setattr(
        "kotaemon.indices.knowledge.runtime.index.SQLiteFTSDocumentStore",
        NoFtsDocumentStore,
        raising=False,
    )
    snapshot = _snapshot(tmp_path)
    runtime = build_snapshot_runtime(
        snapshot,
        embedding=ConstantEmbeddings(),
        reranker=None,
        policy=RetrievalPolicy(enabled=True, candidate_k=5),
        lexical=True,
    )
    qa = LocalQA(
        snapshot=snapshot,
        runtime=runtime,
        reranker_status="unavailable (synthetic)",
    )
    result = qa.retrieve_result("Target passage")

    assert result.cards
    assert result.diagnostics["lexical_status"] == "unavailable"
    assert result.diagnostics["lexical_requested"] is True
    assert result.diagnostics["reranker_status"] == "unavailable (synthetic)"
    assert result.diagnostics["route_statuses"]
    assert any(
        status["branch"] == "lexical" and status["status"] == "unavailable"
        for status in result.diagnostics["route_statuses"]
    )
    assert result.diagnostics["route_candidates"]
    assert result.diagnostics["fusion_scores"]
    assert any(
        decision.get("reason") == "scorer_unavailable"
        for decision in result.diagnostics["expansion_decisions"]
    )
    assert runtime.docstore.supports_lexical_search is False
    runtime.close()


def test_ephemeral_fts_hybrid_runtime_is_thread_safe(tmp_path):
    from kotaemon.indices.knowledge.evaluation.snapshot_adapter import (
        build_snapshot_runtime,
    )
    from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace

    runtime = build_snapshot_runtime(
        _snapshot(tmp_path),
        embedding=ConstantEmbeddings(),
        reranker=None,
        policy=RetrievalPolicy(enabled=True, candidate_k=5),
        lexical=True,
    )
    trace = RetrievalTrace()
    try:
        result = runtime.service.search(
            "Target passage",
            top_k=5,
            trace=trace,
            retrieval_policy=RetrievalPolicy(enabled=True, candidate_k=5),
        )
        route_events = [
            event
            for event in trace.to_dict()["events"]
            if event.get("stage") == "recall_route"
        ]
        assert result
        assert {(event["branch"], event["status"]) for event in route_events} == {
            ("dense", "available"),
            ("lexical", "available"),
        }
    finally:
        runtime.close()


def _result(cards, *, status="ready", diagnostics=None):
    return SimpleNamespace(
        cards=tuple(cards),
        packed_context=object(),
        trace={},
        diagnostics=diagnostics or {},
        status=status,
    )


class _ResultQA:
    def __init__(self, result, legacy_cards=()):
        self.result = result
        self.legacy_cards = tuple(legacy_cards)

    def retrieve(self, _question):
        return self.legacy_cards

    def retrieve_result(self, _question, **_kwargs):
        return self.result


class _Generator:
    model = "synthetic:local"

    def __init__(self):
        self.calls = []

    def generate(self, question, cards):
        self.calls.append((question, tuple(cards)))
        return "synthetic answer"


def _card(text):
    return EvidenceCard(
        source_rank=1,
        chunk_rank=1,
        source_id="source-a",
        source_label="guide.md",
        locator={"page_label": "1"},
        score=0.75,
        text=text,
    )


def test_generator_receives_only_packed_cards():
    packed = _card("fits the generation budget")
    omitted = _card("was omitted from the packed context")
    generator = _Generator()

    answer_question(
        _ResultQA(_result([packed]), legacy_cards=[packed, omitted]),
        generator,
        "question",
    )

    assert generator.calls == [("question", (packed,))]


def test_no_seed_fit_skips_ollama():
    oversized_seed = _card("oversized evidence")
    generator = _Generator()

    answer, evidence = answer_question(
        _ResultQA(
            _result([], status="insufficient_evidence"),
            legacy_cards=[oversized_seed],
        ),
        generator,
        "question",
    )

    assert generator.calls == []
    assert "budget" in answer.casefold() or "fit" in answer.casefold()
    assert evidence["cards"] == []


def test_estimated_budget_is_labeled():
    generator = _Generator()

    _answer, evidence = answer_question(
        _ResultQA(
            _result(
                [_card("packed")],
                diagnostics={"budget_estimated": True, "lexical_status": "available"},
            ),
            legacy_cards=[_card("packed")],
        ),
        generator,
        "question",
    )

    assert evidence["diagnostics"]["generation_budget"] == "estimated"


def test_product_disabled_preserves_selected_file_contract(monkeypatch):
    from ktem.index.file import pipelines

    selected = RetrievedDocument(id_="selected-chunk", text="selected")
    service = SimpleNamespace(search_calls=[], chunk_calls=[])

    def search(query, **kwargs):
        service.search_calls.append((query, kwargs))
        return [selected]

    service.search = search
    service.chunk_ids_for_sources = lambda ids: service.chunk_calls.append(
        list(ids)
    ) or ["selected-chunk"]
    monkeypatch.setattr(pipelines, "create_file_knowledge_service", lambda **_: service)
    settings = DocumentRetrievalPipeline.get_user_settings()
    assert settings["v3_enabled"]["value"] is False

    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        top_k=3,
        v3_enabled=False,
    )
    assert pipeline.run(
        text="question",
        doc_ids=["source-a"],
        path="/team",
        source_types=["markdown"],
        filters={"owner": "alice"},
    ) == [selected]
    assert service.search_calls == [
        ("question", {"allowed_source_ids": ["source-a"], "top_k": 3, "trace": None})
    ]


def test_product_v3_empty_selection_skips_rewrite(monkeypatch):
    from ktem.index.file import pipelines

    calls = []
    monkeypatch.setattr(
        pipelines,
        "create_file_knowledge_service",
        lambda **kwargs: calls.append(("service", kwargs)),
    )
    pipeline = DocumentRetrievalPipeline(
        embedding=None,
        Source=object(),
        Index=object(),
        VS=object(),
        DS=object(),
        v3_enabled=True,
        query_enrichment=True,
    )
    object.__setattr__(
        pipeline,
        "query_enricher",
        lambda *args, **kwargs: calls.append(("rewrite", args)),
    )

    assert pipeline.run(text="follow up?", doc_ids=[]) == []
    assert calls == []


def _agent_service(tmp_path):
    from ktem.index.file.knowledge_service import create_agent_knowledge_service
    from sqlalchemy import JSON, Column, Integer, String, create_engine
    from sqlalchemy.ext.mutable import MutableDict
    from sqlalchemy.orm import declarative_base, sessionmaker

    base = declarative_base()

    class Source(base):
        __tablename__ = "task6_agent_source"
        id = Column(String, primary_key=True)
        name = Column(String)
        user = Column(String)
        note = Column(MutableDict.as_mutable(JSON))

    class Index(base):
        __tablename__ = "task6_agent_index"
        id = Column(Integer, primary_key=True)
        source_id = Column(String)
        target_id = Column(String)
        relation_type = Column(String)

    engine = create_engine(f"sqlite:///{tmp_path / 'task6-agent.db'}")
    base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        session.add_all(
            [
                Source(
                    id="visible",
                    name="visible.md",
                    user="user-a",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/visible.md",
                        }
                    },
                ),
                Source(
                    id="hidden",
                    name="hidden.md",
                    user="user-b",
                    note={
                        "knowledge": {
                            "source_type": "markdown",
                            "virtual_path": "/team/hidden.md",
                        }
                    },
                ),
            ]
        )
        session.add_all(
            [
                Index(
                    source_id="visible",
                    target_id="visible-chunk",
                    relation_type="document",
                ),
                Index(
                    source_id="hidden",
                    target_id="hidden-chunk",
                    relation_type="document",
                ),
            ]
        )
        session.commit()

    retrieval_calls = []

    def retrieve(**kwargs):
        retrieval_calls.append(kwargs)
        return []

    service = create_agent_knowledge_service(
        Source=Source,
        Index=Index,
        vector_retrieval=retrieve,
        docstore=object(),
        private=True,
        user_id="user-a",
        session_factory=session_factory,
    )
    return service, retrieval_calls


def test_agent_global_uses_visible_catalog(tmp_path):
    service, retrieval_calls = _agent_service(tmp_path)

    assert service.search("unmatched global question") == []
    assert retrieval_calls[0]["scope"] is None
    assert retrieval_calls[0]["fallback_scope"] == ["visible-chunk"]
    assert service.authorized_chunk_ids() == frozenset({"visible-chunk"})


def test_agent_allowlist_cannot_expand_visibility(tmp_path):
    service, _retrieval_calls = _agent_service(tmp_path)

    assert service.authorized_chunk_ids(
        allowed_source_ids=["visible", "hidden"]
    ) == frozenset({"visible-chunk"})
