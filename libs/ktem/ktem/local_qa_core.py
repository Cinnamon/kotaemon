"""Read-only retrieval over one approved local knowledge snapshot."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.evaluation import snapshot_adapter
from kotaemon.indices.knowledge.evaluation.local_cli import (
    _ensure_contained,
    _reject_symlink_components,
    _require_ignored_repo_local_root,
    _validate_snapshot_approval,
    resolve_model_paths,
)
from kotaemon.indices.knowledge.evaluation.local_experiment import (
    _validate_baseline_splitter,
    _validate_model_provenance,
)
from kotaemon.indices.knowledge.evaluation.local_models import (
    _require_offline_inference_process,
)
from kotaemon.indices.knowledge.evaluation.local_snapshot import (
    LocalSnapshot,
    load_local_snapshot,
)
from kotaemon.indices.knowledge.evaluation.snapshot_adapter import SnapshotRuntime
from kotaemon.indices.knowledge.evaluation.source_metrics import source_ranked_chunks
from kotaemon.indices.knowledge.planning.query_enrichment import QueryEnricher
from kotaemon.indices.knowledge.retrieval.context_budget import (
    GenerationBudget,
    PackedContext,
    pack_evidence,
    serialize_chat_messages,
)
from kotaemon.indices.knowledge.retrieval.contracts import RetrievalPolicy
from kotaemon.indices.knowledge.retrieval.expansion import (
    ChunkResolver,
    EvidenceBundle,
    ExpansionPolicy,
    expand_evidence,
)
from kotaemon.indices.knowledge.retrieval.trace import RetrievalTrace
from kotaemon.models.local_bge import BgeM3Embeddings, BgeM3Reranking

from ktem.local_qa_conversation import (
    DEFAULT_HISTORY_TOKEN_LIMIT,
    DEFAULT_MAX_TURNS,
    ConversationState,
)


@dataclass(frozen=True)
class EvidenceCard:
    source_rank: int
    chunk_rank: int
    source_id: str
    source_label: str
    locator: Mapping[str, Any]
    score: float | None
    text: str
    chunk_id: str | None = None


@dataclass(frozen=True)
class LocalQAResult:
    """Evidence cards and diagnostics for one workbench generation request."""

    cards: tuple[EvidenceCard, ...]
    packed_context: PackedContext | None
    trace: Mapping[str, Any]
    diagnostics: Mapping[str, Any]
    status: str


def render_generation_context(
    question: str,
    cards: Sequence[EvidenceCard],
    *,
    user_history: Sequence[str] = (),
) -> str:
    """Render the exact user-message body sent to the local Ollama client."""
    evidence = []
    for card in cards:
        item = {
            "source_rank": card.source_rank,
            "chunk_rank": card.chunk_rank,
            "source_id": card.source_id,
            "source_label": card.source_label,
            "locator": dict(card.locator),
            "score": card.score,
            "text": card.text,
        }
        if card.chunk_id is not None:
            item["chunk_id"] = card.chunk_id
        evidence.append(item)
    payload = {"question": question, "evidence": evidence}
    if user_history:
        payload["user_history"] = list(user_history)
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


class LocalQA:
    def __init__(
        self,
        *,
        snapshot: LocalSnapshot,
        bundle: Mapping[str, Any] | None = None,
        service=None,
        runtime: SnapshotRuntime | None = None,
        reranker_status: str = "available",
    ):
        if runtime is not None:
            self._runtime = runtime
            self._service = runtime.service
            self._bundle = {
                "chunk_to_source": runtime.chunk_to_source,
                "draft_chunks": runtime.draft_chunks,
                "unresolved_offsets": runtime.unresolved_offsets,
            }
            self._retrieval_policy = runtime.policy
            self._reranker = (
                runtime.service.retriever.rerankers[0]
                if runtime.service.retriever.rerankers
                else None
            )
            self._runtime_config = dict(runtime.config)
        else:
            if bundle is None or service is None:
                raise TypeError("bundle and service are required without a runtime")
            self._runtime = None
            self._service = service
            self._bundle = bundle
            self._retrieval_policy = RetrievalPolicy()
            self._reranker = None
            self._runtime_config = {"lexical_status": "not_used"}
        self._runtime_config["reranker_status"] = reranker_status
        self._chunk_to_source = self._bundle["chunk_to_source"]
        self._sources_by_id = {
            source["source_id"]: source for source in snapshot.selected_sources
        }

    def _locator_for_chunk(self, chunk_id: str) -> Mapping[str, Any]:
        if self._runtime is not None and chunk_id in self._runtime.locators:
            return self._runtime.locators[chunk_id]
        draft = self._bundle["draft_chunks"].get(chunk_id)
        if draft is not None:
            return draft.locator
        unresolved = self._bundle["unresolved_offsets"].get(chunk_id)
        if unresolved is None:
            raise ValueError(f"retrieved chunk {chunk_id!r} has no source locator")
        return unresolved.locator

    def retrieve(
        self,
        question: str,
        *,
        user_history: Sequence[str] = (),
        generation_budget: GenerationBudget | None = None,
        count_tokens: Callable[[str], int] | None = None,
        base_prompt: str = "",
        query_rewriter: Callable[[str, tuple[str, ...]], str] | None = None,
    ) -> tuple[EvidenceCard, ...]:
        return self.retrieve_result(
            question,
            user_history=user_history,
            generation_budget=generation_budget,
            count_tokens=count_tokens,
            base_prompt=base_prompt,
            query_rewriter=query_rewriter,
        ).cards

    def retrieve_result(
        self,
        question: str,
        *,
        user_history: Sequence[str] = (),
        generation_budget: GenerationBudget | None = None,
        count_tokens: Callable[[str], int] | None = None,
        base_prompt: str = "",
        query_rewriter: Callable[[str, tuple[str, ...]], str] | None = None,
    ) -> LocalQAResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question must not be empty")

        clean_question = question.strip()
        history_counter = count_tokens or (lambda text: len(text.encode("utf-8")))
        bounded_history_state = ConversationState()
        history_turns = (
            (user_history,) if isinstance(user_history, str) else user_history
        )
        for turn in history_turns:
            if isinstance(turn, str):
                bounded_history_state = bounded_history_state.append_user(
                    turn,
                    max_turns=DEFAULT_MAX_TURNS,
                    token_limit=DEFAULT_HISTORY_TOKEN_LIMIT,
                    count_tokens=history_counter,
                )
        bounded_user_history = bounded_history_state.user_turns
        trace = RetrievalTrace()
        if self._runtime is None:
            candidates = self._service.search(clean_question, top_k=20)
            enriched_query = None
        else:
            enriched_query = QueryEnricher(
                rewriter=query_rewriter,
                max_variants=self._retrieval_policy.max_variants,
            ).enrich(clean_question, bounded_user_history)
            candidates = self._service.search(
                clean_question,
                top_k=20,
                trace=trace,
                enriched_query=enriched_query,
                retrieval_policy=self._retrieval_policy,
            )
        trace_data = trace.to_dict()
        representatives = source_ranked_chunks(
            candidates, self._chunk_to_source, limit=5
        )
        source_ranks = {
            self._chunk_to_source[document.doc_id]: rank
            for rank, document in enumerate(representatives, start=1)
        }
        selected_sources = set(source_ranks)

        seed_documents = tuple(
            document
            for document in candidates
            if self._chunk_to_source.get(document.doc_id) in selected_sources
        )
        chunk_ranks = {
            document.doc_id: rank for rank, document in enumerate(candidates, start=1)
        }
        expansion_bundle = EvidenceBundle(seed_documents, (), ())
        if self._runtime is not None:
            authorized_chunk_ids = self._service.authorized_chunk_ids()
            expansion_bundle = expand_evidence(
                seed_documents,
                query=clean_question,
                resolver=ChunkResolver(
                    docstore=self._runtime.docstore,
                    catalog=self._runtime.catalog,
                ),
                allowed_chunk_ids=authorized_chunk_ids,
                scorer=self._reranker,
                policy=ExpansionPolicy(),
            )

        ranked_documents = list(expansion_bundle.seeds)
        ranked_documents.extend(expansion_bundle.expansions)
        next_chunk_rank = len(candidates)
        for document in ranked_documents:
            if document.doc_id not in chunk_ranks:
                next_chunk_rank += 1
                chunk_ranks[document.doc_id] = next_chunk_rank
        source_labels = (
            self._runtime.source_labels
            if self._runtime is not None
            else {
                source_id: source["relative_path"]
                for source_id, source in self._sources_by_id.items()
            }
        )
        cards_by_id: dict[str, EvidenceCard] = {}
        for document in ranked_documents:
            source_id = self._chunk_to_source.get(document.doc_id)
            if source_id is None or source_id not in selected_sources:
                continue
            score = document.score
            if not isinstance(score, Real) or not math.isfinite(score):
                score = None
            cards_by_id[document.doc_id] = EvidenceCard(
                source_rank=source_ranks[source_id],
                chunk_rank=chunk_ranks[document.doc_id],
                source_id=source_id,
                source_label=source_labels[source_id],
                locator=dict(self._locator_for_chunk(document.doc_id)),
                score=score,
                text=document.text,
                chunk_id=document.doc_id,
            )

        packed_context = None
        if generation_budget is not None:
            if count_tokens is None:
                raise ValueError("count_tokens is required with generation_budget")
            packed_context = pack_evidence(
                expansion_bundle,
                budget=generation_budget,
                count_tokens=count_tokens,
                base_prompt="",
                render_context=lambda documents: render_generation_context(
                    clean_question,
                    [cards_by_id[document.doc_id] for document in documents],
                    user_history=bounded_user_history,
                ),
                render_budgeted_request=lambda user_message: serialize_chat_messages(
                    [
                        {"role": "system", "content": base_prompt},
                        {"role": "user", "content": user_message},
                    ]
                ),
            )
            cards = tuple(
                cards_by_id[document.doc_id]
                for document in packed_context.documents
                if document.doc_id in cards_by_id
            )
            status = packed_context.status
        else:
            cards = tuple(
                cards_by_id[document.doc_id]
                for document in ranked_documents
                if document.doc_id in cards_by_id
            )
            status = "ready" if cards else "no_evidence"

        route_statuses = trace_data.get("route_statuses", [])
        trace_events = trace_data.get("events", [])
        route_candidates = []
        fusion_scores = []
        reranker_candidates = []
        for event in trace_events:
            if not isinstance(event, Mapping):
                continue
            if event.get("stage") == "recall_route":
                route_candidates.append(
                    {
                        "branch": event.get("branch"),
                        "query_index": event.get("query_index"),
                        "status": event.get("status"),
                        "candidates": [
                            {
                                "id": candidate.get("id"),
                                "rank": rank,
                                "score": candidate.get("score"),
                                "score_available": candidate.get(
                                    "score_available", False
                                ),
                            }
                            for rank, candidate in enumerate(
                                event.get("candidates", []), start=1
                            )
                            if isinstance(candidate, Mapping)
                        ],
                    }
                )
            elif event.get("stage") == "fusion":
                fusion_scores.append(
                    [
                        {"id": document_id, "score": score}
                        for document_id, score in zip(
                            event.get("ids", []), event.get("scores", [])
                        )
                    ]
                )
            elif event.get("stage") == "reranker":
                reranker_candidates.append(
                    {
                        "name": event.get("name"),
                        "candidates": event.get("candidates", []),
                    }
                )
        diagnostics = {
            "lexical_status": trace_data.get(
                "lexical_status", self._runtime_config.get("lexical_status", "not_used")
            ),
            "lexical_requested": self._runtime_config.get("lexical_requested", False),
            "route_statuses": route_statuses,
            "route_candidates": route_candidates,
            "fusion_ids": trace_data.get("merged_ids", []),
            "fusion_scores": fusion_scores,
            "rerankers": trace_data.get("rerankers", []),
            "reranker_candidates": reranker_candidates,
            "reranker_status": self._runtime_config.get("reranker_status", "not_used"),
            "expansion_decisions": list(expansion_bundle.decisions),
            "budget_estimated": (
                generation_budget.estimated if generation_budget is not None else None
            ),
            "budget_tokens_used": (
                (
                    packed_context.request_token_count
                    if packed_context.request_token_count is not None
                    else packed_context.token_count
                )
                if packed_context is not None
                else None
            ),
            "budget_tokens_available": (
                (
                    packed_context.request_tokens_available
                    if packed_context.request_tokens_available is not None
                    else packed_context.available_tokens
                )
                if packed_context is not None
                else None
            ),
            "packed_context_ids": (
                [document.doc_id for document in packed_context.documents]
                if packed_context is not None
                else [card.chunk_id for card in cards if card.chunk_id]
            ),
            "omitted_ids": (
                list(packed_context.omitted_ids) if packed_context is not None else []
            ),
            "chunk_seed_k": 20,
            "distinct_source_k": 5,
            "history_turns": len(bounded_user_history),
            "history_tokens": history_counter("\n".join(bounded_user_history)),
        }
        return LocalQAResult(
            cards=cards,
            packed_context=packed_context,
            trace=trace_data,
            diagnostics=diagnostics,
            status=status,
        )


def open_playground(
    local_root: Path,
    snapshot_dir: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    *,
    embedding_factory: Callable[..., BaseEmbeddings] | None = None,
) -> LocalQA:
    root = Path(local_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("local root must be an existing directory")
    _require_ignored_repo_local_root(root)

    snapshots_root = _ensure_contained(root / "snapshots", root, "snapshots")
    _reject_symlink_components(snapshots_root, stop=root)
    if not snapshots_root.is_dir():
        raise ValueError("local snapshots/ directory must already exist")

    snapshot_path = _ensure_contained(snapshot_dir, snapshots_root, "snapshot")
    _reject_symlink_components(snapshot_path, stop=snapshots_root)
    _validate_snapshot_approval(snapshot_path)
    snapshot = load_local_snapshot(snapshot_path, require_reviewed=True)
    _validate_baseline_splitter(snapshot)

    paths = resolve_model_paths(root, embedding_model_dir, reranker_model_dir)
    _validate_model_provenance(paths)
    _require_offline_inference_process()
    factory = embedding_factory or BgeM3Embeddings
    embedding = factory(
        paths.embedding_model_dir,
        revision=paths.embedding_revision,
        weight_source=paths.embedding_weight_source,
    )
    reranker = None
    reranker_status = "available"
    try:
        reranker = BgeM3Reranking(
            model_path=paths.reranker_model_dir,
            revision=paths.reranker_revision,
            weight_source=paths.reranker_weight_source,
        )
    except Exception as error:
        # Missing local weights or an unavailable optional inference dependency
        # degrades reranking and expansion without weakening retrieval scope.
        reranker_status = f"unavailable ({type(error).__name__})"

    policy = RetrievalPolicy(
        enabled=True,
        candidate_k=20,
        max_fused_candidates=40,
    )
    runtime = snapshot_adapter.build_snapshot_runtime(
        snapshot,
        embedding=embedding,
        reranker=reranker,
        policy=policy,
        chunking_mode="token",
        lexical=True,
    )
    return LocalQA(
        snapshot=snapshot,
        runtime=runtime,
        reranker_status=reranker_status,
    )
