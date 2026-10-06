"""Authorized, bounded expansion from persisted adjacent chunk pointers."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kotaemon.base import Document, RetrievedDocument
from kotaemon.indices.knowledge.retrieval.diversity import select_diverse_documents

if TYPE_CHECKING:
    from kotaemon.models.local_bge import BgeM3Reranking


def _require_int(name: str, value: int, *, minimum: int, maximum: int | None = None):
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or maximum is not None
        and value > maximum
    ):
        if maximum is None:
            constraint = f"an integer greater than or equal to {minimum}"
        else:
            constraint = f"an integer from {minimum} through {maximum}"
        raise ValueError(f"{name} must be {constraint}")


@dataclass(frozen=True)
class ExpansionPolicy:
    """Limits for optional supporting evidence; v3 permits one chunk per side."""

    max_neighbors_each_side: int = 1
    max_total_evidence: int = 15
    max_per_source: int = 8
    max_neighbor_chars: int = 4000

    def __post_init__(self) -> None:
        _require_int(
            "max_neighbors_each_side",
            self.max_neighbors_each_side,
            minimum=0,
            maximum=1,
        )
        _require_int("max_total_evidence", self.max_total_evidence, minimum=1)
        _require_int("max_per_source", self.max_per_source, minimum=1)
        _require_int("max_neighbor_chars", self.max_neighbor_chars, minimum=1)


@dataclass(frozen=True)
class EvidenceBundle:
    seeds: tuple[RetrievedDocument, ...]
    expansions: tuple[RetrievedDocument, ...]
    decisions: tuple[dict, ...]


def _metadata(document: Document) -> dict:
    value = getattr(document, "metadata", None)
    return dict(value) if isinstance(value, Mapping) else {}


def _doc_id(document: Document) -> str | None:
    value = getattr(document, "doc_id", None)
    return value if isinstance(value, str) and value else None


def _source_hint(metadata: Mapping) -> tuple[str | None, bool]:
    values = {
        value
        for key in ("source_id", "file_id", "document_id")
        if isinstance((value := metadata.get(key)), str) and value
    }
    if len(values) > 1:
        return None, True
    return (next(iter(values)), False) if values else (None, False)


def _identity(metadata: Mapping) -> tuple[str, str, int] | None:
    version = metadata.get("source_version")
    unit = metadata.get("unit_id")
    ordinal = metadata.get("chunk_ordinal")
    if (
        not isinstance(version, str)
        or not version
        or not isinstance(unit, str)
        or not unit
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 0
    ):
        return None
    return version, unit, ordinal


def _owner_ids(value) -> tuple[str, ...]:
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, Sequence):
        values = tuple(value)
    else:
        return ()
    return tuple(sorted({item for item in values if isinstance(item, str) and item}))


def _as_document_list(value) -> list[Document]:
    if isinstance(value, Document):
        return [value]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [document for document in value if isinstance(document, Document)]
    return []


class ChunkResolver:
    """Resolve at most two persisted pointers after hard chunk authorization."""

    def __init__(self, *, docstore, catalog):
        self.docstore = docstore
        self.catalog = catalog

    def _seed_source_id(
        self, seed: RetrievedDocument, *, allowed_chunk_ids: frozenset[str]
    ) -> tuple[str | None, str | None]:
        seed_id = _doc_id(seed)
        if seed_id is None or seed_id not in allowed_chunk_ids:
            return None, "seed_not_authorized"
        seed_metadata = _metadata(seed)
        if _identity(seed_metadata) is None:
            return None, "legacy_metadata_missing"
        hint, conflict = _source_hint(seed_metadata)
        if conflict:
            return None, "seed_source_metadata_conflict"

        try:
            owners = self.catalog.source_ids_for_chunk_ids([seed_id])
        except Exception:
            return None, "catalog_error"
        owner_map = owners if isinstance(owners, Mapping) else {}
        source_ids = _owner_ids(owner_map.get(seed_id))
        if len(source_ids) != 1:
            return None, "seed_catalog_owner_missing_or_ambiguous"
        source_id = source_ids[0]
        if hint is not None and hint != source_id:
            return None, "seed_source_metadata_mismatch"
        return source_id, None

    @staticmethod
    def _metadata_matches_seed(
        seed_metadata: Mapping, neighbor_metadata: Mapping
    ) -> bool:
        for key in ("source_type", "virtual_path", "entity"):
            if (
                key in seed_metadata
                and neighbor_metadata.get(key) != seed_metadata[key]
            ):
                return False
        return True

    def _neighbors_for_source(
        self,
        seed: RetrievedDocument,
        *,
        allowed_chunk_ids: frozenset[str],
        seed_source_id: str,
    ) -> tuple[tuple[Document, ...], tuple[dict, ...]]:
        seed_id = _doc_id(seed)
        seed_metadata = _metadata(seed)
        seed_identity = _identity(seed_metadata)
        if seed_id is None or seed_identity is None:
            return (), (
                {
                    "seed_id": seed_id,
                    "decision": "rejected",
                    "reason": "legacy_metadata_missing",
                },
            )

        seed_version, seed_unit, seed_ordinal = seed_identity
        pointers = (
            ("previous", "previous_chunk_id", "next_chunk_id", seed_ordinal - 1),
            ("next", "next_chunk_id", "previous_chunk_id", seed_ordinal + 1),
        )
        candidates: list[tuple[str, str, str, int]] = []
        decisions: list[dict] = []
        pointer_ids = [
            value
            for _side, key, _reciprocal_key, _expected in pointers
            if isinstance((value := seed_metadata.get(key)), str) and value
        ]
        duplicate_pointer_ids = {
            value for value, count in Counter(pointer_ids).items() if count > 1
        }

        for side, key, reciprocal_key, expected_ordinal in pointers:
            candidate_id = seed_metadata.get(key)
            if candidate_id is None:
                continue
            if (
                not isinstance(candidate_id, str)
                or not candidate_id
                or candidate_id == seed_id
            ):
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "invalid_pointer",
                    }
                )
                continue
            if candidate_id in duplicate_pointer_ids:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "duplicate_pointer",
                    }
                )
                continue
            if expected_ordinal < 0:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "wrong_ordinal",
                    }
                )
                continue
            if candidate_id not in allowed_chunk_ids:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "outside_authorized_chunk_ids",
                    }
                )
                continue
            candidates.append((side, candidate_id, reciprocal_key, expected_ordinal))

        if not candidates:
            return (), tuple(decisions)

        candidate_ids = [candidate_id for _, candidate_id, _, _ in candidates]
        try:
            catalog_result = self.catalog.source_ids_for_chunk_ids(
                candidate_ids, allowed_source_ids=(seed_source_id,)
            )
        except Exception:
            decisions.extend(
                {
                    "seed_id": seed_id,
                    "neighbor_id": candidate_id,
                    "side": side,
                    "decision": "rejected",
                    "reason": "catalog_error",
                }
                for side, candidate_id, _, _ in candidates
            )
            return (), tuple(decisions)

        catalog_map = catalog_result if isinstance(catalog_result, Mapping) else {}
        authorized: list[tuple[str, str, str, int]] = []
        for candidate in candidates:
            side, candidate_id, reciprocal_key, expected_ordinal = candidate
            owners = _owner_ids(catalog_map.get(candidate_id))
            if owners != (seed_source_id,):
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "not_authorized_in_catalog",
                    }
                )
                continue
            authorized.append(candidate)

        if not authorized:
            return (), tuple(decisions)

        # The intersection and catalog ownership checks both precede this read.
        read_ids = [candidate_id for _, candidate_id, _, _ in authorized]
        try:
            fetched = _as_document_list(self.docstore.get(read_ids))
        except Exception:
            decisions.extend(
                {
                    "seed_id": seed_id,
                    "neighbor_id": candidate_id,
                    "side": side,
                    "decision": "rejected",
                    "reason": "docstore_error",
                }
                for side, candidate_id, _, _ in authorized
            )
            return (), tuple(decisions)

        fetched_by_id: dict[str, list[Document]] = {}
        for document in fetched:
            fetched_id = _doc_id(document)
            if fetched_id in read_ids:
                fetched_by_id.setdefault(fetched_id, []).append(document)

        neighbors: list[Document] = []
        for side, candidate_id, reciprocal_key, expected_ordinal in authorized:
            records = fetched_by_id.get(candidate_id, [])
            if len(records) != 1:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": "missing_or_duplicate_document",
                    }
                )
                continue
            document = records[0]
            neighbor_metadata = _metadata(document)
            neighbor_identity = _identity(neighbor_metadata)
            neighbor_hint, source_conflict = _source_hint(neighbor_metadata)
            if (
                source_conflict
                or neighbor_hint is not None
                and neighbor_hint != seed_source_id
            ):
                reason = "source_metadata_mismatch"
            elif neighbor_identity is None:
                reason = "legacy_metadata_missing"
            elif neighbor_identity[0] != seed_version:
                reason = "source_version_mismatch"
            elif neighbor_identity[1] != seed_unit:
                reason = "unit_mismatch"
            elif neighbor_identity[2] != expected_ordinal:
                reason = "wrong_ordinal"
            elif neighbor_metadata.get(reciprocal_key) != seed_id:
                reason = "nonreciprocal_pointer"
            elif not self._metadata_matches_seed(seed_metadata, neighbor_metadata):
                reason = "explicit_metadata_mismatch"
            else:
                reason = None

            if reason is not None:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "neighbor_id": candidate_id,
                        "side": side,
                        "decision": "rejected",
                        "reason": reason,
                    }
                )
                continue
            neighbors.append(document)
            decisions.append(
                {
                    "seed_id": seed_id,
                    "neighbor_id": candidate_id,
                    "side": side,
                    "decision": "eligible",
                    "reason": "authorized_adjacent_chunk",
                }
            )

        return tuple(neighbors), tuple(decisions)

    def _neighbors_with_decisions(
        self, seed: RetrievedDocument, *, allowed_chunk_ids: frozenset[str]
    ) -> tuple[str | None, tuple[Document, ...], tuple[dict, ...]]:
        source_id, reason = self._seed_source_id(
            seed, allowed_chunk_ids=allowed_chunk_ids
        )
        if source_id is None:
            return (
                None,
                (),
                (
                    {
                        "seed_id": _doc_id(seed),
                        "decision": "rejected",
                        "reason": reason or "seed_source_unavailable",
                    },
                ),
            )
        documents, decisions = self._neighbors_for_source(
            seed,
            allowed_chunk_ids=allowed_chunk_ids,
            seed_source_id=source_id,
        )
        return source_id, documents, decisions

    def neighbors(
        self,
        seed: RetrievedDocument,
        *,
        allowed_chunk_ids: frozenset[str],
    ) -> tuple[Document, ...]:
        """Read only authorized persisted previous/next IDs for a valid seed."""
        allowed = _normalize_allowed_chunk_ids(allowed_chunk_ids)
        _source_id, documents, _decisions = self._neighbors_with_decisions(
            seed, allowed_chunk_ids=allowed
        )
        return documents


def _normalize_allowed_chunk_ids(values) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise TypeError("allowed_chunk_ids must be a collection of chunk IDs")
    try:
        normalized = frozenset(
            value for value in values if isinstance(value, str) and value
        )
    except TypeError:
        raise TypeError("allowed_chunk_ids must be a collection of chunk IDs") from None
    return normalized


def _valid_score(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    score = float(value)
    return score if math.isfinite(score) else None


def _text(document: Document) -> str:
    value = getattr(document, "text", "")
    return value if isinstance(value, str) else str(value or "")


def _retrieved_clone(document: Document) -> RetrievedDocument:
    payload = document.to_dict()
    payload["score"] = getattr(document, "score", 0.0)
    payload["retrieval_metadata"] = dict(
        getattr(document, "retrieval_metadata", {}) or {}
    )
    return RetrievedDocument(**payload)


def _select_seed_window(
    seeds: Sequence[RetrievedDocument],
    owners: Mapping[str, str | None],
    policy: ExpansionPolicy,
    decisions: list[dict],
) -> tuple[RetrievedDocument, ...]:
    retained: list[RetrievedDocument] = []
    counts: Counter[str | None] = Counter()
    for seed in seeds:
        seed_id = _doc_id(seed)
        if seed_id is not None and seed_id in owners:
            source_id = owners[seed_id]
        else:
            source_id, _conflict = _source_hint(_metadata(seed))
        if len(retained) >= policy.max_total_evidence:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "decision": "rejected",
                    "reason": "max_total_evidence",
                }
            )
            continue
        if counts[source_id] >= policy.max_per_source:
            decisions.append(
                {"seed_id": seed_id, "decision": "rejected", "reason": "max_per_source"}
            )
            continue
        retained.append(seed)
        counts[source_id] += 1
    return tuple(retained)


def expand_evidence(
    seeds: Sequence[RetrievedDocument],
    *,
    query: str,
    resolver: ChunkResolver,
    allowed_chunk_ids: frozenset[str],
    scorer: BgeM3Reranking | None,
    policy: ExpansionPolicy,
) -> EvidenceBundle:
    """Add only same-source, same-version, same-unit adjacent scored chunks."""
    allowed = _normalize_allowed_chunk_ids(allowed_chunk_ids)
    decisions: list[dict] = []
    unique_seeds: list[RetrievedDocument] = []
    seen_seed_ids: set[str] = set()
    for seed in seeds:
        seed_id = _doc_id(seed)
        if seed_id is None or seed_id not in allowed:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "decision": "rejected",
                    "reason": "seed_not_authorized",
                }
            )
            continue
        if seed_id in seen_seed_ids:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "decision": "rejected",
                    "reason": "duplicate_seed_id",
                }
            )
            continue
        seen_seed_ids.add(seed_id)
        if not _text(seed).strip():
            decisions.append(
                {
                    "seed_id": seed_id,
                    "decision": "rejected",
                    "reason": "empty_seed_text",
                }
            )
            continue
        unique_seeds.append(seed)

    if not unique_seeds:
        return EvidenceBundle((), (), tuple(decisions))

    if scorer is None:
        retained = _select_seed_window(unique_seeds, {}, policy, decisions)
        decisions.extend(
            {
                "seed_id": _doc_id(seed),
                "decision": "skipped",
                "reason": "scorer_unavailable",
            }
            for seed in retained
        )
        return EvidenceBundle(retained, (), tuple(decisions))

    try:
        seed_scores_raw = scorer.score_pairs(query, unique_seeds)
    except Exception:
        retained = _select_seed_window(unique_seeds, {}, policy, decisions)
        decisions.append({"decision": "skipped", "reason": "seed_scoring_error"})
        return EvidenceBundle(retained, (), tuple(decisions))
    if not isinstance(seed_scores_raw, Sequence) or len(seed_scores_raw) != len(
        unique_seeds
    ):
        retained = _select_seed_window(unique_seeds, {}, policy, decisions)
        decisions.append({"decision": "skipped", "reason": "invalid_seed_scores"})
        return EvidenceBundle(retained, (), tuple(decisions))
    seed_scores = [_valid_score(score) for score in seed_scores_raw]
    if any(score is None for score in seed_scores):
        retained = _select_seed_window(unique_seeds, {}, policy, decisions)
        decisions.append({"decision": "skipped", "reason": "invalid_seed_scores"})
        return EvidenceBundle(retained, (), tuple(decisions))

    owners: dict[str, str | None] = {}
    for seed in unique_seeds:
        seed_id = _doc_id(seed)
        source_id, reason = resolver._seed_source_id(seed, allowed_chunk_ids=allowed)
        owners[seed_id] = source_id
        if source_id is None and reason:
            decisions.append(
                {"seed_id": seed_id, "decision": "skipped", "reason": reason}
            )

    retained_seeds = _select_seed_window(unique_seeds, owners, policy, decisions)
    if not retained_seeds:
        return EvidenceBundle((), (), tuple(decisions))

    seed_floor = min(score for score in seed_scores if score is not None)
    seed_counts = Counter(owners.get(_doc_id(seed)) for seed in retained_seeds)
    eligible_neighbors: list[tuple[RetrievedDocument, str | None, str | None]] = []
    seen_neighbor_ids: set[str] = set()

    if policy.max_neighbors_each_side:
        for seed in retained_seeds:
            seed_id = _doc_id(seed)
            source_id = owners.get(seed_id)
            if source_id is None:
                continue
            if (
                len(retained_seeds) + len(eligible_neighbors)
                >= policy.max_total_evidence
            ):
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "decision": "skipped",
                        "reason": "max_total_evidence",
                    }
                )
                continue
            if seed_counts[source_id] >= policy.max_per_source:
                decisions.append(
                    {
                        "seed_id": seed_id,
                        "decision": "skipped",
                        "reason": "max_per_source",
                    }
                )
                continue

            documents, resolver_decisions = resolver._neighbors_for_source(
                seed,
                allowed_chunk_ids=allowed,
                seed_source_id=source_id,
            )
            decisions.extend(resolver_decisions)
            for document in documents:
                neighbor_id = _doc_id(document)
                neighbor_text = _text(document)
                if neighbor_id is None:
                    decisions.append(
                        {
                            "seed_id": seed_id,
                            "decision": "rejected",
                            "reason": "invalid_neighbor_id",
                        }
                    )
                    continue
                if neighbor_id in seen_neighbor_ids or neighbor_id in seen_seed_ids:
                    decisions.append(
                        {
                            "seed_id": seed_id,
                            "neighbor_id": neighbor_id,
                            "decision": "rejected",
                            "reason": "duplicate_id",
                        }
                    )
                    continue
                seen_neighbor_ids.add(neighbor_id)
                if not neighbor_text.strip():
                    decisions.append(
                        {
                            "seed_id": seed_id,
                            "neighbor_id": neighbor_id,
                            "decision": "rejected",
                            "reason": "empty_neighbor_text",
                        }
                    )
                    continue
                if len(neighbor_text) > policy.max_neighbor_chars:
                    decisions.append(
                        {
                            "seed_id": seed_id,
                            "neighbor_id": neighbor_id,
                            "decision": "rejected",
                            "reason": "neighbor_too_large",
                        }
                    )
                    continue
                clone = _retrieved_clone(document)
                eligible_neighbors.append((clone, seed_id, source_id))

    if not eligible_neighbors:
        return EvidenceBundle(retained_seeds, (), tuple(decisions))

    neighbor_documents = [item[0] for item in eligible_neighbors]
    try:
        neighbor_scores_raw = scorer.score_pairs(query, neighbor_documents)
    except Exception:
        decisions.append({"decision": "skipped", "reason": "neighbor_scoring_error"})
        return EvidenceBundle(retained_seeds, (), tuple(decisions))
    if not isinstance(neighbor_scores_raw, Sequence) or len(neighbor_scores_raw) != len(
        eligible_neighbors
    ):
        decisions.append({"decision": "skipped", "reason": "invalid_neighbor_scores"})
        return EvidenceBundle(retained_seeds, (), tuple(decisions))

    scored_neighbors: list[
        tuple[float, int, RetrievedDocument, str | None, str | None]
    ] = []
    for index, ((document, seed_id, source_id), raw_score) in enumerate(
        zip(eligible_neighbors, neighbor_scores_raw)
    ):
        score = _valid_score(raw_score)
        neighbor_id = _doc_id(document)
        if score is None:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "neighbor_id": neighbor_id,
                    "decision": "rejected",
                    "reason": "nonfinite_neighbor_score",
                }
            )
            continue
        if score < seed_floor:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "neighbor_id": neighbor_id,
                    "score": score,
                    "decision": "rejected",
                    "reason": "below_seed_score_floor",
                }
            )
            continue
        scored_neighbors.append((score, index, document, seed_id, source_id))

    scored_neighbors.sort(key=lambda item: (-item[0], item[1]))
    accepted_neighbors: list[RetrievedDocument] = []
    for score, _index, document, seed_id, source_id in scored_neighbors:
        neighbor_id = _doc_id(document)
        if len(retained_seeds) + len(accepted_neighbors) >= policy.max_total_evidence:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "neighbor_id": neighbor_id,
                    "score": score,
                    "decision": "rejected",
                    "reason": "max_total_evidence",
                }
            )
            continue
        if seed_counts[source_id] >= policy.max_per_source:
            decisions.append(
                {
                    "seed_id": seed_id,
                    "neighbor_id": neighbor_id,
                    "score": score,
                    "decision": "rejected",
                    "reason": "max_per_source",
                }
            )
            continue
        retrieval_metadata = dict(document.retrieval_metadata or {})
        retrieval_metadata.update(
            {
                "evidence_role": "expansion",
                "expanded_from": seed_id,
                "neighbor_score": score,
            }
        )
        document.retrieval_metadata = retrieval_metadata
        accepted_neighbors.append(document)
        seed_counts[source_id] += 1
        decisions.append(
            {
                "seed_id": seed_id,
                "neighbor_id": neighbor_id,
                "score": score,
                "decision": "accepted",
                "reason": "score_at_or_above_seed_floor",
            }
        )

    combined = [*retained_seeds, *accepted_neighbors]
    exclusions: list[tuple[str | None, str]] = []
    selected = select_diverse_documents(
        combined,
        top_k=policy.max_total_evidence,
        parent_section_cap=None,
        on_exclusion=lambda document_id, reason: exclusions.append(
            (document_id, reason)
        ),
    )
    selected_ids = {_doc_id(document) for document in selected}
    for document_id, reason in exclusions:
        decisions.append(
            {"neighbor_id": document_id, "decision": "rejected", "reason": reason}
        )
    selected_seeds = tuple(
        seed for seed in retained_seeds if _doc_id(seed) in selected_ids
    )
    selected_seed_ids = {_doc_id(seed) for seed in selected_seeds}
    selected_expansions = tuple(
        document
        for document in accepted_neighbors
        if _doc_id(document) in selected_ids
        and _doc_id(document) not in selected_seed_ids
    )
    return EvidenceBundle(selected_seeds, selected_expansions, tuple(decisions))
