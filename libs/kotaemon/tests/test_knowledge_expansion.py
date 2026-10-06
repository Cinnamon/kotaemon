"""Synthetic authorization and scoring tests for adjacent evidence expansion."""

from __future__ import annotations

from kotaemon.base import Document, RetrievedDocument
from kotaemon.indices.knowledge.retrieval.expansion import (
    ChunkResolver,
    ExpansionPolicy,
    expand_evidence,
)


class SyntheticCatalog:
    def __init__(self, owners):
        self.owners = owners
        self.lookups = []

    def source_ids_for_chunk_ids(self, chunk_ids, *, allowed_source_ids=None):
        ids = tuple(chunk_ids)
        allowed = None if allowed_source_ids is None else set(allowed_source_ids)
        self.lookups.append((ids, allowed))
        return {
            chunk_id: tuple(
                source_id
                for source_id in self.owners.get(chunk_id, ())
                if allowed is None or source_id in allowed
            )
            for chunk_id in ids
            if any(
                allowed is None or source_id in allowed
                for source_id in self.owners.get(chunk_id, ())
            )
        }


class SyntheticDocstore:
    def __init__(self, documents):
        self.documents = {document.doc_id: document for document in documents}
        self.reads = []

    def get(self, ids):
        ids = [ids] if isinstance(ids, str) else list(ids)
        self.reads.append(tuple(ids))
        return [self.documents[doc_id] for doc_id in ids if doc_id in self.documents]


class DeterministicScorer:
    def __init__(self, scores):
        self.scores = scores
        self.calls = []

    def score_pairs(self, query, documents):
        self.calls.append((query, tuple(document.text for document in documents)))
        return tuple(self.scores[document.doc_id] for document in documents)


def make_chunk(
    doc_id,
    text,
    *,
    ordinal=0,
    previous=None,
    next=None,
    source_id="source-a",
    version="version-1",
    unit="unit-1",
    document_type="markdown",
    virtual_path="/team/guide.md",
    entity=None,
    retrieved=True,
):
    metadata = {
        "source_id": source_id,
        "file_id": source_id,
        "document_id": source_id,
        "source_version": version,
        "unit_id": unit,
        "chunk_ordinal": ordinal,
        "source_type": document_type,
        "virtual_path": virtual_path,
        "entity": {} if entity is None else entity,
    }
    if previous is not None:
        metadata["previous_chunk_id"] = previous
    if next is not None:
        metadata["next_chunk_id"] = next
    cls = RetrievedDocument if retrieved else Document
    return cls(id_=doc_id, text=text, metadata=metadata)


def resolver_for(seed, *neighbors, owners=None):
    documents = [seed, *neighbors]
    owner_map = {document.doc_id: ("source-a",) for document in documents}
    if owners:
        owner_map.update(owners)
    docstore = SyntheticDocstore(neighbors)
    catalog = SyntheticCatalog(owner_map)
    return ChunkResolver(docstore=docstore, catalog=catalog), docstore, catalog


def test_neighbor_not_in_authorized_catalog_is_never_read():
    seed = make_chunk("seed", "seed text", next="unowned")
    unowned = make_chunk(
        "unowned", "must not be read", ordinal=1, previous="seed", retrieved=False
    )
    resolver, docstore, _catalog = resolver_for(seed, unowned, owners={"unowned": ()})

    neighbors = resolver.neighbors(
        seed, allowed_chunk_ids=frozenset({"seed", "unowned"})
    )

    assert neighbors == ()
    assert all("unowned" not in read_ids for read_ids in docstore.reads)


def test_explicit_metadata_filter_excludes_neighbor_before_read():
    seed = make_chunk("seed", "seed text", next="wrong-path")
    filtered_out = make_chunk(
        "wrong-path",
        "excluded by the explicit path filter",
        ordinal=1,
        previous="seed",
        virtual_path="/other/guide.md",
        retrieved=False,
    )
    resolver, docstore, catalog = resolver_for(seed, filtered_out)

    neighbors = resolver.neighbors(seed, allowed_chunk_ids=frozenset({"seed"}))

    assert neighbors == ()
    assert docstore.reads == []
    assert all("wrong-path" not in ids for ids, _allowed in catalog.lookups)


def test_neighbor_lookup_reads_at_most_two_ids():
    previous = make_chunk(
        "previous", "previous text", ordinal=0, next="seed", retrieved=False
    )
    seed = make_chunk("seed", "seed text", ordinal=1, previous="previous", next="next")
    next_chunk = make_chunk(
        "next", "next text", ordinal=2, previous="seed", retrieved=False
    )
    resolver, docstore, catalog = resolver_for(seed, previous, next_chunk)

    neighbors = resolver.neighbors(
        seed,
        allowed_chunk_ids=frozenset({"seed", "previous", "next"}),
    )

    assert [document.doc_id for document in neighbors] == ["previous", "next"]
    assert all(len(read_ids) <= 2 for read_ids in docstore.reads)
    assert all(len(ids) <= 2 for ids, _allowed in catalog.lookups)


def test_same_unit_wrong_version_is_rejected():
    seed = make_chunk("seed", "seed text", next="stale", version="version-1")
    stale = make_chunk(
        "stale",
        "stale version text",
        ordinal=1,
        previous="seed",
        version="version-2",
        retrieved=False,
    )
    resolver, _docstore, _catalog = resolver_for(seed, stale)

    neighbors = resolver.neighbors(seed, allowed_chunk_ids=frozenset({"seed", "stale"}))

    assert neighbors == ()


def test_nonreciprocal_or_wrong_ordinal_pointer_is_rejected():
    seed = make_chunk(
        "seed", "seed text", previous="bad-ordinal", next="bad-reciprocal"
    )
    bad_ordinal = make_chunk(
        "bad-ordinal", "ordinal mismatch", ordinal=-1, next="seed", retrieved=False
    )
    bad_reciprocal = make_chunk(
        "bad-reciprocal",
        "pointer mismatch",
        ordinal=1,
        previous="elsewhere",
        retrieved=False,
    )
    resolver, _docstore, _catalog = resolver_for(seed, bad_ordinal, bad_reciprocal)

    neighbors = resolver.neighbors(
        seed,
        allowed_chunk_ids=frozenset({"seed", "bad-ordinal", "bad-reciprocal"}),
    )

    assert neighbors == ()


def test_legacy_metadata_skips_expansion():
    seed = RetrievedDocument(
        id_="legacy-seed", text="legacy text", metadata={"next_chunk_id": "neighbor"}
    )
    neighbor = make_chunk(
        "neighbor", "neighbor text", ordinal=1, previous="legacy-seed", retrieved=False
    )
    resolver, docstore, _catalog = resolver_for(seed, neighbor)

    result = expand_evidence(
        [seed],
        query="question",
        resolver=resolver,
        allowed_chunk_ids=frozenset({"legacy-seed", "neighbor"}),
        scorer=DeterministicScorer({"legacy-seed": 0.8, "neighbor": 0.9}),
        policy=ExpansionPolicy(),
    )

    assert result.expansions == ()
    assert docstore.reads == []


def test_scorer_missing_skips_expansion():
    seed = make_chunk("seed", "seed text", next="neighbor")
    neighbor = make_chunk(
        "neighbor", "neighbor text", ordinal=1, previous="seed", retrieved=False
    )
    resolver, docstore, _catalog = resolver_for(seed, neighbor)

    result = expand_evidence(
        [seed],
        query="question",
        resolver=resolver,
        allowed_chunk_ids=frozenset({"seed", "neighbor"}),
        scorer=None,
        policy=ExpansionPolicy(),
    )

    assert result.seeds == (seed,)
    assert result.expansions == ()
    assert docstore.reads == []
    assert any(
        decision.get("reason") == "scorer_unavailable" for decision in result.decisions
    )


def _score_case(neighbor_score):
    seed = make_chunk("seed", "seed text", next="neighbor")
    neighbor = make_chunk(
        "neighbor", "neighbor text", ordinal=1, previous="seed", retrieved=False
    )
    resolver, _docstore, _catalog = resolver_for(seed, neighbor)
    scorer = DeterministicScorer({"seed": 0.8, "neighbor": neighbor_score})
    result = expand_evidence(
        [seed],
        query="question",
        resolver=resolver,
        allowed_chunk_ids=frozenset({"seed", "neighbor"}),
        scorer=scorer,
        policy=ExpansionPolicy(),
    )
    return result, scorer


def test_neighbor_below_lowest_seed_score_is_rejected():
    result, _scorer = _score_case(0.79)

    assert result.expansions == ()
    assert any(
        decision.get("reason") == "below_seed_score_floor"
        for decision in result.decisions
    )


def test_neighbor_score_equal_to_seed_floor_is_accepted():
    result, _scorer = _score_case(0.8)

    assert [document.doc_id for document in result.expansions] == ["neighbor"]


def test_full_seed_text_is_scored():
    full_text = "complete seed passage " * 100
    seed = make_chunk("seed", full_text, next="neighbor")
    neighbor = make_chunk(
        "neighbor", "short neighbor", ordinal=1, previous="seed", retrieved=False
    )
    resolver, _docstore, _catalog = resolver_for(seed, neighbor)
    scorer = DeterministicScorer({"seed": 0.8, "neighbor": 0.9})

    expand_evidence(
        [seed],
        query="question",
        resolver=resolver,
        allowed_chunk_ids=frozenset({"seed", "neighbor"}),
        scorer=scorer,
        policy=ExpansionPolicy(max_neighbor_chars=40),
    )

    assert scorer.calls[0] == ("question", (full_text,))


def test_oversized_neighbor_is_rejected_before_score():
    seed = make_chunk("seed", "seed text", next="large")
    large = make_chunk(
        "large", "oversized neighbor text", ordinal=1, previous="seed", retrieved=False
    )
    resolver, _docstore, _catalog = resolver_for(seed, large)
    scorer = DeterministicScorer({"seed": 0.8, "large": 0.9})

    result = expand_evidence(
        [seed],
        query="question",
        resolver=resolver,
        allowed_chunk_ids=frozenset({"seed", "large"}),
        scorer=scorer,
        policy=ExpansionPolicy(max_neighbor_chars=8),
    )

    assert result.expansions == ()
    assert scorer.calls == [("question", ("seed text",))]
    assert any(
        decision.get("reason") == "neighbor_too_large" for decision in result.decisions
    )
