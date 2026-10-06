"""Synthetic end-to-end comparison through the Agent knowledge service."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from kotaemon.base import Document, DocumentWithEmbedding
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices import VectorRetrieval
from kotaemon.indices.knowledge.evaluation.retrieval_eval import (
    IndexedCatalog,
    compare_runs,
    load_fixture,
    resolve_judgments,
)
from kotaemon.indices.knowledge.planning.query_planner import (
    KnowledgeSource,
    QueryPlanner,
)
from kotaemon.indices.knowledge.planning.retrieval_plan import RetrievalPlan
from kotaemon.indices.knowledge.retrieval.knowledge_service import KnowledgeService
from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace
from kotaemon.indices.qa.citation_qa import AnswerWithContextPipeline
from kotaemon.indices.qa.format_context import PrepareEvidencePipeline
from kotaemon.storages.docstores.in_memory import InMemoryDocumentStore
from kotaemon.storages.vectorstores.base import BaseVectorStore

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = _ROOT / "libs/kotaemon/tests/fixtures/knowledge_eval"
_RECORDS_PATH = _FIXTURES / "records.json"
_JUDGMENTS_PATH = _FIXTURES / "judgments.jsonl"
_ARTIFACTS = _ROOT / "docs/superpowers/reports/artifacts"
_TRACE_RELATIVE = "docs/superpowers/reports/artifacts/agent-retrieval-zhang-trace.json"
_METRICS_RELATIVE = "docs/superpowers/reports/artifacts/agent-retrieval-evaluation.json"


def _is_cjk(char: str) -> bool:
    codepoint = ord(char)
    return (
        0x3400 <= codepoint <= 0x4DBF
        or 0x4E00 <= codepoint <= 0x9FFF
        or 0xF900 <= codepoint <= 0xFAFF
        or 0x20000 <= codepoint <= 0x2FA1F
    )


def _feature_tokens(text: str) -> list[str]:
    """Stable character-bigram and Latin-token features for synthetic vectors."""
    tokens: list[str] = []
    index = 0
    while index < len(text):
        if _is_cjk(text[index]):
            end = index + 1
            while end < len(text) and _is_cjk(text[end]):
                end += 1
            run = text[index:end]
            grams = (
                [run]
                if len(run) == 1
                else [run[i : i + 2] for i in range(len(run) - 1)]
            )
            for gram in grams:
                tokens.append(f"cjk:{gram}")
            index = end
            continue
        match = re.match(r"[A-Za-z0-9_]+", text[index:])
        if match:
            token = match.group(0).casefold()
            tokens.append(f"word:{token}")
            index += len(match.group(0))
            continue
        index += 1
    return tokens


def _vectorize(text: str) -> list[float]:
    """Map tokens into a stable fixed-width hashed feature vector."""
    vector = [0.0] * 16384
    for feature in _feature_tokens(text):
        index = int.from_bytes(
            hashlib.sha256(feature.encode("utf-8")).digest()[:4], "big"
        ) % len(vector)
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class DeterministicEmbedding(BaseEmbeddings):
    """Fixed test embedding; vectors are normalized token/bigram counts."""

    def run(self, text, *args, **kwargs):
        if isinstance(text, Document):
            text = text.text
        if isinstance(text, list):
            return [
                DocumentWithEmbedding(embedding=_vectorize(str(item))) for item in text
            ]
        return [DocumentWithEmbedding(embedding=_vectorize(str(text)))]


class DeterministicVectorStore(BaseVectorStore):
    """In-memory cosine adapter that ranks indexed synthetic embeddings."""

    def __init__(self):
        self._records: list[tuple[str, list[float]]] = []
        self.query_log: list[dict[str, Any]] = []
        self.add_calls = 0

    def add(self, embeddings, metadatas=None, ids=None):
        self.add_calls += 1
        for offset, item in enumerate(embeddings):
            if isinstance(item, DocumentWithEmbedding):
                chunk_id = item.doc_id
                vector = list(item.embedding)
            else:
                chunk_id = ids[offset] if ids else str(offset)
                vector = list(item)
            self._records.append((chunk_id, vector))
        return [record[0] for record in self._records[-len(embeddings) :]]

    def delete(self, ids, **kwargs):
        selected = set(ids)
        self._records = [
            record for record in self._records if record[0] not in selected
        ]

    def query(self, embedding, top_k=1, ids=None, **kwargs):
        allowed = None if ids is None else set(ids)
        query_vector = list(embedding)
        ranked = []
        for ordinal, (chunk_id, vector) in enumerate(self._records):
            if allowed is not None and chunk_id not in allowed:
                continue
            score = sum(left * right for left, right in zip(query_vector, vector))
            ranked.append((score, ordinal, chunk_id, vector))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        selected = ranked[:top_k]
        self.query_log.append(
            {"top_k": top_k, "ids": None if ids is None else tuple(ids)}
        )
        return (
            [row[3] for row in selected],
            [row[0] for row in selected],
            [row[2] for row in selected],
        )

    def drop(self):
        self._records.clear()


class FixtureCatalog:
    def __init__(self, sources, chunks_by_source):
        self.sources = tuple(sources)
        self.chunks_by_source = {
            source_id: tuple(chunk_ids)
            for source_id, chunk_ids in chunks_by_source.items()
        }
        self.source_by_chunk = {
            chunk_id: source_id
            for source_id, chunk_ids in self.chunks_by_source.items()
            for chunk_id in chunk_ids
        }

    def list_sources(self, allowed_source_ids=None):
        if allowed_source_ids is None:
            return list(self.sources)
        allowed = set(allowed_source_ids)
        return [source for source in self.sources if source.source_id in allowed]

    def chunk_ids(self, source_ids, relation_type="document"):
        assert relation_type == "document"
        return {
            source_id: self.chunks_by_source[source_id]
            for source_id in source_ids
            if source_id in self.chunks_by_source
        }

    def source_ids_for_chunk_ids(self, chunk_ids, allowed_source_ids=None):
        allowed = None if allowed_source_ids is None else set(allowed_source_ids)
        return {
            chunk_id: source_id
            for chunk_id in chunk_ids
            if (source_id := self.source_by_chunk.get(chunk_id)) is not None
            and (allowed is None or source_id in allowed)
        }


class IdentityGlobalPlanner:
    """Baseline planner that preserves explicit service constraints only."""

    def plan(self, query, catalog, **kwargs):
        return RetrievalPlan(
            query=query,
            semantic_query=query,
            confidence=0.0,
            reason="identity baseline: no inferred scope",
            source_ids=None,
        )


def _make_indexed_fixture():
    records = json.loads(_RECORDS_PATH.read_text(encoding="utf-8"))
    assert records["schema_version"] == 1
    fixture = load_fixture(_JUDGMENTS_PATH)
    sources = []
    chunks_by_source = {}
    documents = []
    for source in records["sources"]:
        source_id = source["id"]
        is_legacy = bool(source.get("legacy"))
        source_type = None if is_legacy else source["source_type"]
        virtual_path = None if is_legacy else source["virtual_path"]
        source_name = source["document_name"]
        entity = {} if is_legacy else source["entity"]
        sources.append(
            KnowledgeSource(
                source_id=source_id,
                source_type=source_type,
                virtual_path=virtual_path,
                document_name=source_name,
                entity=entity,
                source_name=source_name,
            )
        )
        chunks_by_source[source_id] = []
        for chunk in source["chunks"]:
            assert not any("relevant" in key.casefold() for key in chunk)
            chunk_id = chunk["id"]
            metadata = {
                **chunk.get("metadata", {}),
                "file_id": source_id,
                "document_id": source_id,
                "file_name": source_name,
            }
            if virtual_path:
                metadata["virtual_path"] = virtual_path
            if is_legacy:
                metadata.pop("virtual_path", None)
            assert not any("relevant" in key.casefold() for key in metadata)
            document = Document(id_=chunk_id, text=chunk["text"], metadata=metadata)
            documents.append(document)
            chunks_by_source[source_id].append(chunk_id)

    embedding = DeterministicEmbedding()
    vector_store = DeterministicVectorStore()
    vector_store.add(
        [
            DocumentWithEmbedding(
                id_=document.doc_id,
                text=document.text,
                metadata=document.metadata,
                embedding=_vectorize(document.text),
            )
            for document in documents
        ]
    )
    docstore = InMemoryDocumentStore()
    docstore.add(documents)
    catalog = FixtureCatalog(sources, chunks_by_source)
    indexed_catalog = IndexedCatalog(
        source_ids=[source.source_id for source in sources],
        chunk_to_source=catalog.source_by_chunk,
    )
    cases = resolve_judgments(fixture, indexed_catalog)
    return {
        "records": records,
        "fixture": fixture,
        "cases": cases,
        "catalog": catalog,
        "indexed_catalog": indexed_catalog,
        "documents": {document.doc_id: document for document in documents},
        "embedding": embedding,
        "vector_store": vector_store,
        "docstore": docstore,
        "record_sha256": hashlib.sha256(
            _RECORDS_PATH.read_bytes() + b"\0" + _JUDGMENTS_PATH.read_bytes()
        ).hexdigest(),
    }


def _make_service(*, planner, fixture_state, top_k):
    retriever = VectorRetrieval(
        vector_store=fixture_state["vector_store"],
        doc_store=fixture_state["docstore"],
        embedding=fixture_state["embedding"],
        retrieval_mode="vector",
        top_k=top_k,
        first_round_top_k_mult=1,
        rerankers=[],
        max_per_parent_or_section=None,
    )
    return KnowledgeService(
        planner=planner,
        catalog=fixture_state["catalog"],
        retriever=retriever,
        docstore=fixture_state["docstore"],
    )


def _metric_by_id(run):
    return {metric.case_id: metric for metric in run.per_query}


def _run_empty_allowlist_parity(baseline_service, planned_service, fixture_state):
    query = "张三在哪实习？"
    parity = {
        "judged": False,
        "query": query,
        "allowed_source_ids": [],
    }
    for arm, service in (
        ("baseline", baseline_service),
        ("planned", planned_service),
    ):
        trace = RetrievalTrace()
        calls_before = len(fixture_state["vector_store"].query_log)
        result = service.search(query, allowed_source_ids=[], trace=trace)
        calls_after = len(fixture_state["vector_store"].query_log)
        trace_snapshot = trace.to_dict()
        vector_query_count = calls_after - calls_before
        no_search_reason = trace_snapshot["no_search_reason"]
        no_search_events = [
            event
            for event in trace_snapshot["events"]
            if event.get("stage") == "no_search"
        ]
        assert result == []
        assert calls_after == calls_before
        assert vector_query_count == 0
        assert no_search_reason == "empty_visibility"
        assert trace_snapshot["search_status"] == "not_run"
        assert no_search_events == [
            {"stage": "no_search", "reason": "empty_visibility"}
        ]
        parity[arm] = {
            "result_ids": [document.doc_id for document in result],
            "vector_query_count": vector_query_count,
            "search_status": trace_snapshot["search_status"],
            "no_search_reason": no_search_reason,
            "no_search_event": no_search_events[0],
        }
    return parity


def _run_synthetic_comparison(artifact_dir: Path | None = None):
    fixture_state = _make_indexed_fixture()
    top_k = 5
    baseline_service = _make_service(
        planner=IdentityGlobalPlanner(), fixture_state=fixture_state, top_k=top_k
    )
    planned_service = _make_service(
        planner=QueryPlanner(), fixture_state=fixture_state, top_k=top_k
    )
    candidate_k = top_k
    rerankers: list[str] = []
    shared_config = {
        "backend": "DeterministicVectorStore cosine + InMemoryDocumentStore",
        "vector_backend": "fixture deterministic cosine adapter",
        "docstore_backend": "InMemoryDocumentStore",
        "lexical_capability": fixture_state["docstore"].supports_lexical_search,
        "retrieval_mode": "vector",
        "top_k": top_k,
        "candidate_k": candidate_k,
        "first_round_top_k_mult": 1,
        "do_extend": False,
        "rerankers": rerankers,
        "max_per_parent_or_section": None,
        "mmr": False,
        "context_budget": 4096,
        "embedding": "deterministic-char-bigram-v1",
        "fixture_sha256": fixture_state["record_sha256"],
        "seed": 0,
    }
    assert not any("relevant" in key.casefold() for key in shared_config)
    result_docs: dict[tuple[str, str], list] = {}
    trace_by_key: dict[tuple[str, str], RetrievalTrace] = {}
    observed_candidate_counts: dict[str, list[int]] = {"baseline": [], "planned": []}

    def make_trace(arm, case):
        trace = RetrievalTrace()
        if arm == "planned" and case.case_id == "zhang-internship" and artifact_dir:
            trace.artifact_path = _TRACE_RELATIVE
        trace_by_key[(arm, case.case_id)] = trace
        return trace

    def search(service, arm):
        def run(case, trace=None):
            query_start = len(fixture_state["vector_store"].query_log)
            documents = service.search(
                case.query,
                path=case.path,
                source_types=case.source_types,
                filters=case.filters,
                top_k=top_k,
                allowed_source_ids=case.allowed_source_ids,
                trace=trace,
            )
            new_calls = fixture_state["vector_store"].query_log[query_start:]
            observed_candidate_counts[arm].extend(call["top_k"] for call in new_calls)
            result_docs[(arm, case.case_id)] = documents
            return documents

        return run

    comparison = compare_runs(
        fixture_state["cases"],
        search_baseline=search(baseline_service, "baseline"),
        search_planned=search(planned_service, "planned"),
        k=top_k,
        chunk_to_source=fixture_state["indexed_catalog"].chunk_to_source,
        baseline_config={**shared_config, "planner": "identity-global"},
        planned_config={**shared_config, "planner": "QueryPlanner"},
        trace_factory=make_trace,
    )
    authorization_parity = _run_empty_allowlist_parity(
        baseline_service, planned_service, fixture_state
    )

    planned_zhang_docs = result_docs[("planned", "zhang-internship")]
    zhang_trace = trace_by_key[("planned", "zhang-internship")]
    evidence = PrepareEvidencePipeline(max_context_length=4096, token_counter=len).run(
        planned_zhang_docs, trace=zhang_trace
    )
    context = evidence.content[1]
    quote = "负责构建检索 API"
    assert quote in context
    synthetic_answer = Document(
        metadata={"citation": type("Citation", (), {"evidences": [quote]})()}
    )
    spans = AnswerWithContextPipeline.match_evidence_with_context(
        AnswerWithContextPipeline, synthetic_answer, planned_zhang_docs
    )
    matched = [
        (document, span)
        for document in planned_zhang_docs
        for span in spans.get(document.doc_id, [])
        if document.text[span["start"] : span["end"]] == quote
    ]
    assert matched
    matched_document, matched_span = matched[0]

    trace_snapshot = zhang_trace.to_dict()
    assert trace_snapshot["original_query"] == "张三实习期间做了什么工作？"
    assert trace_snapshot["plan"]["semantic_query"] == trace_snapshot["original_query"]
    assert trace_snapshot["plan"]["source_ids"] == ["source-zhang"]
    assert trace_snapshot["source_scope"]["mandatory_ids"] == [
        "source-legacy",
        "source-li",
        "source-wang",
        "source-zhang",
    ]
    assert trace_snapshot["chunk_scope"]["planned_ids"] == [
        "chunk-zhang-api",
        "chunk-zhang-li-question",
        "chunk-zhang-rag",
    ]
    assert trace_snapshot["attempts"]
    assert trace_snapshot["attempts"][0]["vector_status"] == "available"
    assert trace_snapshot["attempts"][0]["lexical_status"] == "not_used"
    assert trace_snapshot["final_chunk_ids"] == [
        doc.doc_id for doc in planned_zhang_docs
    ]
    assert trace_snapshot["context"]["chunk_ids"] == [
        doc.doc_id for doc in planned_zhang_docs
    ]
    assert trace_snapshot["context"]["tokens_used"] == len(context)
    assert trace_snapshot.get("scope_fallback_reason") is None
    assert all("text" not in event for event in trace_snapshot["events"])
    assert "张三在实习期间加入 RAG 团队" not in zhang_trace.to_json()

    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        trace_path = artifact_dir / "agent-retrieval-zhang-trace.json"
        trace_path.write_text(zhang_trace.to_json(indent=2) + "\n", encoding="utf-8")
        machine_report = comparison.to_dict()
        machine_report["resolved_judgments"] = [
            case.to_dict() for case in fixture_state["cases"]
        ]
        machine_report["citation_quote_lookup"] = {
            "passed": True,
            "chunk_id": matched_document.doc_id,
            "span": matched_span,
            "quote_sha256": hashlib.sha256(quote.encode("utf-8")).hexdigest(),
            "context_contains_quote": True,
        }
        machine_report["observed_candidate_counts"] = observed_candidate_counts
        machine_report["trace_artifact"] = _TRACE_RELATIVE
        machine_report["authorization_parity"] = {
            "empty_allowlist": authorization_parity
        }
        (artifact_dir / Path(_METRICS_RELATIVE).name).write_text(
            json.dumps(machine_report, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n",
            encoding="utf-8",
        )

    return (
        fixture_state,
        comparison,
        result_docs,
        trace_by_key,
        observed_candidate_counts,
    )


def test_synthetic_baseline_and_planned_retrieval_share_one_fixture_and_config():
    fixture_state, comparison, result_docs, traces, observed_counts = (
        _run_synthetic_comparison(_ARTIFACTS)
    )
    baseline = _metric_by_id(comparison.baseline)
    planned = _metric_by_id(comparison.planned)

    assert fixture_state["vector_store"].add_calls == 1
    assert len(fixture_state["documents"]) == 11
    assert len(comparison.baseline.per_query) == 5
    assert len(comparison.planned.per_query) == 5
    assert len(comparison.baseline_observations) == 5
    assert len(comparison.planned_observations) == 5
    assert observed_counts == {"baseline": [5] * 5, "planned": [5] * 5}
    assert all(
        observation.candidate_k == 5
        for observation in comparison.baseline_observations
        + comparison.planned_observations
    )
    assert all(trace.to_dict()["candidate_k"] == 5 for trace in traces.values())
    assert (
        comparison.baseline_config["fixture_sha256"]
        == comparison.planned_config["fixture_sha256"]
    )
    assert (
        comparison.baseline_config["candidate_k"]
        == comparison.planned_config["candidate_k"]
    )
    assert comparison.baseline_config["top_k"] == 5
    assert comparison.baseline_config["candidate_k"] == 5
    assert comparison.planned_config["top_k"] == 5
    assert comparison.planned_config["candidate_k"] == 5
    assert comparison.baseline_config["max_per_parent_or_section"] is None
    assert comparison.baseline_config["mmr"] is False
    assert comparison.baseline_config["planner"] != comparison.planned_config["planner"]
    assert fixture_state["docstore"].supports_lexical_search is False
    assert comparison.planned_observations[0].vector_statuses == ("available",)
    assert comparison.planned_observations[0].lexical_statuses == ("not_used",)

    assert (
        planned["zhang-internship"].recall_at_k
        >= baseline["zhang-internship"].recall_at_k
    )
    assert planned["zhang-internship"].wrong_scope_rate == 0
    assert planned["li-frontend"].wrong_scope_rate == 0
    # The current deterministic planner does not resolve this wording; retain
    # its global result and expose the observed cross-source distractor.
    assert planned["wang-automation"].wrong_scope_rate == 0.4
    assert comparison.planned.recall_at_k >= comparison.baseline.recall_at_k
    assert comparison.baseline.hit_at_k == comparison.planned.hit_at_k == 1.0
    assert comparison.baseline.recall_at_k == comparison.planned.recall_at_k
    assert round(comparison.baseline.mrr_at_k, 4) == 0.7
    assert round(comparison.planned.mrr_at_k, 4) == 0.8
    assert round(comparison.baseline.wrong_scope_at_k, 4) == round(4 / 13, 4)
    assert round(comparison.planned.wrong_scope_at_k, 4) == round(2 / 11, 4)
    assert comparison.planned.mrr_at_k > comparison.baseline.mrr_at_k
    assert comparison.planned.wrong_scope_at_k < comparison.baseline.wrong_scope_at_k
    assert planned["ambiguous-team"].result_ids == baseline["ambiguous-team"].result_ids
    assert planned["legacy-source"].result_ids == baseline["legacy-source"].result_ids

    planned_status = {
        observation.case_id: observation.planner_status
        for observation in comparison.planned_observations
    }
    assert planned_status == {
        "zhang-internship": "scoped",
        "li-frontend": "scoped",
        "wang-automation": "global",
        "ambiguous-team": "global",
        "legacy-source": "global",
    }
    assert comparison.planned_observations[0].trace_artifact_path == _TRACE_RELATIVE
    assert comparison.config_fingerprint and len(comparison.config_fingerprint) == 64
    assert result_docs[("planned", "zhang-internship")]
    assert traces[("planned", "zhang-internship")].include_content is False


def test_explicit_empty_allowlist_does_not_query_vector_store():
    fixture_state = _make_indexed_fixture()
    service = _make_service(
        planner=QueryPlanner(), fixture_state=fixture_state, top_k=5
    )
    trace = RetrievalTrace()
    before = len(fixture_state["vector_store"].query_log)

    result = service.search("张三在哪实习？", allowed_source_ids=[], trace=trace)

    assert result == []
    assert len(fixture_state["vector_store"].query_log) == before
    assert trace.to_dict()["no_search_reason"] == "empty_visibility"


def test_empty_allowlist_authorization_parity_is_unjudged_and_recorded():
    _run_synthetic_comparison(_ARTIFACTS)
    machine_report = json.loads(
        (_ARTIFACTS / Path(_METRICS_RELATIVE).name).read_text(encoding="utf-8")
    )

    assert machine_report["authorization_parity"]["empty_allowlist"] == {
        "judged": False,
        "query": "张三在哪实习？",
        "allowed_source_ids": [],
        "baseline": {
            "result_ids": [],
            "vector_query_count": 0,
            "search_status": "not_run",
            "no_search_reason": "empty_visibility",
            "no_search_event": {
                "stage": "no_search",
                "reason": "empty_visibility",
            },
        },
        "planned": {
            "result_ids": [],
            "vector_query_count": 0,
            "search_status": "not_run",
            "no_search_reason": "empty_visibility",
            "no_search_event": {
                "stage": "no_search",
                "reason": "empty_visibility",
            },
        },
    }
    assert machine_report["baseline"]["judged_query_count"] == 5
    assert machine_report["planned"]["judged_query_count"] == 5
