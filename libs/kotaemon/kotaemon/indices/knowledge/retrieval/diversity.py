"""Deterministic post-rerank candidate diversity filtering."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Sequence
from typing import Optional

from kotaemon.base import RetrievedDocument


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _group_keys(document: RetrievedDocument) -> tuple[tuple[str, str, str], ...]:
    metadata = document.metadata or {}
    source_id = metadata.get("document_id") or metadata.get("file_id")
    if source_id is None or str(source_id) == "":
        return ()

    keys = []
    parent_id = metadata.get("parent_id")
    if parent_id is not None and str(parent_id) != "":
        keys.append((str(source_id), "parent", str(parent_id)))

    section_path = metadata.get("section_path") or metadata.get("section")
    if isinstance(section_path, (list, tuple)):
        section_path = "/".join(str(part) for part in section_path if part is not None)
    if section_path is not None and str(section_path) != "":
        keys.append((str(source_id), "section", str(section_path)))
    return tuple(keys)


def _five_grams(text: str) -> set[str]:
    return {text[index : index + 5] for index in range(len(text) - 4)}


def _is_overlapping_sibling(
    candidate: RetrievedDocument,
    prior: RetrievedDocument,
    candidate_text: str,
    prior_text: str,
    threshold: float,
    min_chars: int,
) -> bool:
    if not set(_group_keys(candidate)).intersection(_group_keys(prior)):
        return False
    if min(len(candidate_text), len(prior_text)) < min_chars:
        return False
    candidate_grams = _five_grams(candidate_text)
    prior_grams = _five_grams(prior_text)
    if not candidate_grams or not prior_grams:
        return False
    union = candidate_grams | prior_grams
    return len(candidate_grams & prior_grams) / len(union) >= threshold


def select_diverse_documents(
    documents: Sequence[RetrievedDocument],
    *,
    top_k: int,
    parent_section_cap: Optional[int] = 2,
    overlap_threshold: float = 0.85,
    min_overlap_chars: int = 60,
    on_exclusion: Callable[[str | None, str], None] | None = None,
) -> list[RetrievedDocument]:
    """Deduplicate and cap siblings while retaining reranker order.

    Missing source/group metadata disables only the group cap and sibling overlap
    check for that document. Exact IDs and normalized exact text are always removed.
    Candidates excluded by the group cap are deferred and used to fill an otherwise
    short result list.
    """
    if top_k <= 0:
        return []

    cap = parent_section_cap if parent_section_cap and parent_section_cap > 0 else None
    seen_ids: set[str] = set()
    seen_exact_text: set[str] = set()
    unique: list[
        tuple[int, RetrievedDocument, str, tuple[tuple[str, str, str], ...]]
    ] = []

    for index, document in enumerate(documents):
        doc_id = document.doc_id
        if doc_id is not None and doc_id in seen_ids:
            if on_exclusion is not None:
                on_exclusion(doc_id, "duplicate_id")
            continue
        if doc_id is not None:
            seen_ids.add(doc_id)

        normalized_text = _normalize_text(str(document.text or ""))
        if normalized_text and normalized_text in seen_exact_text:
            if on_exclusion is not None:
                on_exclusion(doc_id, "duplicate_text")
            continue

        if normalized_text and any(
            _is_overlapping_sibling(
                document,
                prior,
                normalized_text,
                prior_text,
                overlap_threshold,
                min_overlap_chars,
            )
            for _, prior, prior_text, _ in unique
            if prior_text
        ):
            if on_exclusion is not None:
                on_exclusion(doc_id, "overlap")
            continue

        if normalized_text:
            seen_exact_text.add(normalized_text)
        unique.append((index, document, normalized_text, _group_keys(document)))

    accepted: list[tuple[int, RetrievedDocument]] = []
    deferred: list[tuple[int, RetrievedDocument]] = []
    group_counts: dict[tuple[str, str, str], int] = {}
    for index, document, _, groups in unique:
        if cap is not None and any(
            group_counts.get(group, 0) >= cap for group in groups
        ):
            deferred.append((index, document))
            continue
        accepted.append((index, document))
        for group in groups:
            group_counts[group] = group_counts.get(group, 0) + 1

    selected = list(accepted)
    if len(selected) < top_k:
        selected.extend(deferred[: top_k - len(selected)])
    selected_indexes = {index for index, _ in selected}
    if on_exclusion is not None:
        for index, document in deferred:
            if index not in selected_indexes:
                on_exclusion(document.doc_id, "group_cap")
    selected.sort(key=lambda item: item[0])
    return [document for _, document in selected[:top_k]]
