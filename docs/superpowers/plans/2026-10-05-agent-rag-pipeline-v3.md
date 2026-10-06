# Agent RAG Pipeline v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded hybrid retrieval, query enrichment, BGE reranking, authorized evidence expansion, conversation retrieval, and combination evaluation to the existing product and local workbench.

**Architecture:** Keep `KnowledgeService -> VectorRetrieval -> PrepareEvidencePipeline` as the shared product path. Extract pure policies and a public snapshot-runtime builder, then adapt the product and workbench to those contracts. Compute caller visibility before soft enrichment and authorize every candidate and expanded chunk before it reaches generation.

**Tech Stack:** Python >=3.10, existing Kotaemon Documents/SQL catalog/vector stores/readers, standard-library SQLite FTS5, optional FlagEmbedding==1.4.2, local Ollama, Gradio, pytest, uv.

## Global Constraints

- The frozen v2 mini corpus, judgments, anchors, and four single-factor reports remain immutable.
- Query text, source text, generated answers, and per-query traces stay local.
- No remote model call is permitted by the local workbench.
- The file UI keeps its selected-file contract; the Agent service continues to use the SQL-visible catalog and an optional caller allowlist.
- A rewritten query can change recall text but cannot enlarge `allowed_source_ids`, path/type/entity filters, or user visibility.
- At most one neighbor on either side is eligible in v3.
- Without a scorer, expansion is skipped and traced as `scorer_unavailable`; the original seeds remain usable.
- Oversized units are skipped, never silently cut.
- Zero unauthorized chunks, zero violations of the configured token-counter budget, stable fingerprints, and trace-to-context identity are hard acceptance conditions.
- New product behavior is opt-in. With v3 settings absent/disabled, retain existing lexical-first merge, existing rerankers, selected-source behavior, and legacy evidence formatting.
- Never `git add` the private local fixture tree, model weights, source files, query-level reports, conversation answers, or logs. Stage only named implementation/test/document files.
- Fake model/reader/backend tests run without network or model weights. Real-model evaluations are explicit local runs, not ordinary pytest side effects.
- This plan is authored only; do not commit it during planning. Execution commits below are checkpoints after the task passes review.

## Working directory, baseline, and review protocol

Run all commands from `/Users/zx/.codex/worktrees/agent-knowledge-structure/kotaemon`. Design baseline: `docs/superpowers/specs/2026-10-05-agent-rag-pipeline-v3-design.md`, commit `8fed06a9`.

Use `uv run --package ktem pytest ... -q` for workspace tests. Before real-model smoke/evaluation, use `uv sync --package kotaemon --extra local-eval`; then run with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem ...`. Do not install/download weights from tests. If dependencies are unavailable, record the exact missing dependency and preserve RED evidence; do not reinterpret an import/environment failure as the intended functional failure.

Every task is reviewed separately: write the listed test, run the RED command, confirm the named behavioral assertion/import failure, implement the minimum path, run GREEN plus listed regressions, record changed files and evidence, and commit only after review. Do not merge tasks to hide failures.

## File and interface map

Paths below are repository-relative; new files marked **new**.

| File | Responsibility |
|---|---|
| `libs/kotaemon/kotaemon/indices/knowledge/chunking/identity.py` **new** | Source version, semantic unit, persisted neighbor IDs and conservative offsets |
| `libs/kotaemon/kotaemon/indices/knowledge/retrieval/contracts.py` **new** | Immutable query/route/fusion policy contracts |
| `libs/kotaemon/kotaemon/indices/knowledge/retrieval/fusion.py` **new** | Pure weighted RRF |
| `libs/kotaemon/kotaemon/indices/knowledge/planning/query_enrichment.py` **new** | Identity/deterministic/bounded rewrite enrichment |
| `libs/kotaemon/kotaemon/storages/docstores/sqlite_fts.py` **new** | Ephemeral local FTS5 adapter |
| `libs/kotaemon/kotaemon/models/local_bge.py` **new** | Public optional local BGE adapters and provenance helpers |
| `libs/kotaemon/kotaemon/indices/knowledge/retrieval/expansion.py` **new** | Authorized adjacency resolver, neighbor scoring, evidence decisions |
| `libs/kotaemon/kotaemon/indices/knowledge/retrieval/context_budget.py` **new** | Generator budget/counter and seed-first packing |
| `libs/kotaemon/kotaemon/indices/knowledge/runtime/index.py` **new** | Reusable in-memory runtime construction from Documents and a catalog; no evaluation imports |
| `libs/kotaemon/kotaemon/indices/knowledge/evaluation/snapshot_adapter.py` **new** | Convert an approved LocalSnapshot to runtime inputs without changing the snapshot |
| `libs/ktem/ktem/local_qa_conversation.py` **new** | Session-local bounded user history and local rewrite adapter |
| `libs/kotaemon/kotaemon/indices/knowledge/evaluation/combination_eval.py` **new** | New immutable-run combination and ablation evaluator |

Public contracts to implement in the owning tasks:

```python
# Task 3: contracts.py; branch/status are Literal aliases.
@dataclass(frozen=True)
class EnrichedQuery:
    original_query: str
    standalone_query: str
    variants: tuple[str, ...]  # standalone first; unique; original retained
    reason: str

@dataclass(frozen=True)
class RecallBatch:
    branch: Literal['dense', 'lexical']
    query_index: int
    query: str
    documents: tuple[RetrievedDocument, ...]
    status: Literal['available', 'empty', 'unavailable', 'error']
    error_type: str | None = None

@dataclass(frozen=True)
class RetrievalPolicy:
    enabled: bool = False
    candidate_k: int = 20      # per route
    max_fused_candidates: int = 40
    max_variants: int = 3     # total including standalone/original
    dense_weight: float = 1.0
    lexical_weight: float = 1.0
    rrf_k: int = 60

# Task 5: context_budget.py
@dataclass(frozen=True)
class GenerationBudget:
    model_context: int
    output_reserve: int
    format_reserve: int
    estimated: bool = False

@dataclass(frozen=True)
class PackedContext:
    documents: tuple[RetrievedDocument, ...]
    token_count: int
    available_tokens: int
    status: Literal['ready', 'insufficient_evidence']
    omitted_ids: tuple[str, ...]
```

Validate policy/budget fields as finite non-boolean integers or finite nonnegative weights. Reject impossible budgets. A token counter is `Callable[[str], int]`; reject negative/non-integer counts. No score is a probability.

## Task dependencies

`2 + 3 -> 4`; `1 + 4 -> 5`; `4 + 5 -> 6`; `6 -> 7`; `7 -> 8`. Task 1/2/3 can be reviewed separately, but implement serially unless the authorized execution coordinator explicitly delegates. Task 6 owns integration points after all policies exist.

### Task 1: Parsing provenance and safe chunk adjacency

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/identity.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/chunking/base.py`, `token.py`, `registry.py`, `libs/kotaemon/kotaemon/indices/knowledge/metadata.py`
- Modify: `libs/ktem/ktem/index/file/pipelines.py` (`_split_and_normalize_text_docs`, `stream`, `finish`)
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_ingest.py` (`ReaderDiagnostic`, `_reader_diagnostic`, `build_local_draft`)
- Test: `libs/kotaemon/tests/test_knowledge_adjacency.py` **new**, `libs/kotaemon/tests/test_knowledge_eval_local_ingest.py`, `libs/ktem/ktem_tests/test_knowledge_indexing.py` (existing integration test file)

**Interfaces:**
- Consumes existing `Document`, normalized metadata, existing chunk strategies, raw upload bytes/source hash, and local `SourceUnit`/`DraftChunk` records.
- Produces `stamp_chunk_identity(source: Document, chunks: Sequence[Document], *, source_version: str) -> list[Document]`, `source_version_for_bytes(content: bytes) -> str`, and a streaming `source_version_for_path(path: Path) -> str` for product uploads.
- Metadata keys: `source_version` (SHA256), `unit_id` (version + stable parser unit ordinal/locator + semantic section/symbol identity), `chunk_ordinal` (zero-based per unit), `previous_chunk_id`/`next_chunk_id` (real IDs of adjacent chunks in the same unit, omitted at boundaries), and optional `char_start/char_end` relative to the declared source unit. Existing chunk IDs remain unchanged. Ambiguous repeated text has no asserted offsets. Never derive neighbors from globally sorted UUIDs.
- Reader diagnostic additions: parser version (nullable), fallback reason (nullable), extraction granularity. Existing snapshot v2 schema/files are read unchanged; diagnostics live only in new drafts/runs.

- [ ] **RED tests:** Use synthetic in-memory reader outputs. Write:

```python
def test_repeated_text_does_not_invent_offsets():
    source = Document(text='same same', metadata={'document_id': 's'})
    chunks = [Document(text='same'), Document(text='same')]
    version = source_version_for_bytes(b'v1')
    result = stamp_chunk_identity(source, chunks, source_version=version)
    assert [d.metadata['chunk_ordinal'] for d in result] == [0, 1]
    assert result[0].metadata['next_chunk_id'] == result[1].doc_id
    assert result[1].metadata['previous_chunk_id'] == result[0].doc_id
    assert all('char_start' not in d.metadata for d in result)
    assert {d.doc_id for d in result} == {d.doc_id for d in chunks}
```

Add named cases `test_semantic_sections_have_separate_units`, `test_reindex_changes_version`, `test_unit_boundaries_do_not_link`, `test_legacy_chunk_is_not_given_fake_adjacency`, `test_parser_fallback_is_recorded`, `test_product_metadata_roundtrip_keeps_locator`. For the section case, use actual Markdown strategy outputs for `# A\nalpha\n# B\nbeta` and assert different units with no cross-unit pointer; oversized section pieces share a unit and have reciprocal pointers. The indexing test uses fake DS/VS writes and asserts the same IDs/metadata in both stores. Reindex with changed bytes and assert stale neighbor IDs cannot be followed across versions.
- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_adjacency.py libs/ktem/ktem_tests/test_knowledge_indexing.py -q`. Expected new import/adjacency assertions fail, not reader dependency failures.
- [ ] **Implement:** Stamp after strategy splitting and before DS/VS writes; group by existing semantic parent within this split call before generating unit ID, but derive the persisted unit ID from stable locator/section/symbol/ordinal values rather than random parent UUIDs. In each unit, write reciprocal previous/next chunk IDs from the emitted order; the terminal pointers are absent. Hash upload bytes once with streaming reads and persist version in Source.note knowledge. Preserve canonical/legacy fields. Unique substring offsets are optional; never infer source order from UUID sorting. Add diagnostics without reparsing/replacing approved snapshots.
- [ ] **Run GREEN/regressions:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_adjacency.py libs/ktem/ktem_tests/test_knowledge_indexing.py libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_knowledge_eval_local_ingest.py -q`.
- [ ] **Acceptance/review:** Real indexed IDs and locators survive; semantic boundaries/version and O(1) neighbor IDs are explicit; malformed structure keeps fallback; old chunks skip expansion. Commit named files with `feat: record parser provenance and chunk adjacency`.

### Task 2: Ephemeral SQLite FTS5 lexical adapter

**Files:**
- Create: `libs/kotaemon/kotaemon/storages/docstores/sqlite_fts.py`
- Modify: `libs/kotaemon/kotaemon/storages/docstores/__init__.py`
- Test: `libs/kotaemon/tests/test_sqlite_fts_docstore.py` **new**

**Interfaces:**
- Produces `SQLiteFTSDocumentStore(*, connection_factory=sqlite3.connect)` with existing BaseDocumentStore `add/get/query/delete/count/get_all` semantics and `supports_lexical_search: bool`, `capability_reason: str | None`, `close() -> None`.
- Construct an in-memory ordinary document table for get/storage plus FTS5 text table. Store normalized search tokens generated by `lexical_tokens(text: str) -> tuple[str, ...]`: NFKC/casefold Latin and code identifiers, plus overlapping bigrams from each contiguous CJK run. Index those space-delimited tokens with FTS5 `unicode61`. A single CJK character is not an indexed keyword unless it is an explicitly delimited term; no stemming or synonym claim is made. If FTS5 cannot be created, storage still works, lexical capability is false, and `query` is never called by hybrid routing.
- `query(query: str, top_k: int=10, doc_ids: list[str] | None=None) -> list[Document]`: explicit empty IDs means empty; missing IDs means all. Return ordered real IDs; rank ties by ID. Preserve text and metadata.

- [ ] **RED tests:** Add:

```python
def test_empty_allowlist_cannot_search_all_documents():
    store = SQLiteFTSDocumentStore()
    store.add([Document(id_='a', text='VPN reset'), Document(id_='b', text='VPN admin')])
    assert store.query('VPN', doc_ids=[]) == []
    assert [d.doc_id for d in store.query('VPN', doc_ids=['a'])] == ['a']
```

Also test `test_match_syntax_is_quoted_not_executed` using literal `" OR * )`; `test_delete_updates_fts`; `test_fts_unavailable_keeps_get_usable` with an injected connection wrapper raising OperationalError only for virtual-table creation; `test_mixed_chinese_latin_terms_recall` using `请检查企业VPN登录流程` and asserting that both `VPN` and `登录` retrieve the same document; `test_cjk_bigrams_do_not_bridge_metadata_or_unrelated_fields`; and `test_bm25_order_is_deterministic`. These are correctness checks on synthetic text, not a claim about real-corpus lexical quality.
- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_sqlite_fts_docstore.py -q`; expected new adapter import failures.
- [ ] **Implement:** Use SQLite bound SQL parameters, escape each normalized MATCH token as a quoted literal, deduplicate tokens, and join alternatives with explicit `OR`. Enforce the source allowlist inside SQL and return FTS5 `bm25` order with ID as a stable tie break. Store original text and JSON metadata unchanged. Use stock FTS5 `unicode61` over pretokenized text; record both the SQLite tokenizer and `cjk_bigram_v1` preprocessing version in configuration. Do not characterize it as equivalent to a dedicated Chinese segmenter. No disk database and no corpus writes.
- [ ] **Run GREEN:** Repeat RED command; then `uv run --package ktem pytest libs/kotaemon/tests/test_indexing_retrieval.py -q`.
- [ ] **Acceptance/review:** Real lexical route recalls both synthetic Chinese and embedded Latin terms, handles literal MATCH syntax, cannot widen scope, and closes its connection; unavailable capability explicit. Commit named files with `feat: add ephemeral scoped FTS5 document store`.

### Task 3: Multi-route contracts, enrichment, and weighted RRF

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/retrieval/contracts.py`, `fusion.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/planning/query_enrichment.py`
- Test: `libs/kotaemon/tests/test_knowledge_fusion.py`, `test_query_enrichment.py` **new**

**Interfaces:**
- Produces contracts defined above and `fuse_batches(batches: Sequence[RecallBatch], policy: RetrievalPolicy) -> list[RetrievedDocument]`.
- Produces `QueryEnricher(*, rewriter: Callable[[str, tuple[str, ...]], str] | None=None, max_variants: int=3)`; `.enrich(query: str, user_history: Sequence[str]=()) -> EnrichedQuery`.
- Extract quoted literals, paths, codes/versions as a lexical variant deterministically. Default rewriter absent means standalone is original. Optional rewriter gets bounded user turns; empty/invalid/exception output falls back original. Preserve original in variants, cap and deduplicate normalized routes.
- Relative route weight is branch weight divided by scheduled unique routes for that branch, including failed/unavailable routes. Do not redistribute on failure, which would change configuration semantics.

- [ ] **RED tests:**

```python
def test_rrf_duplicate_id_votes_once_per_route():
    a = RetrievedDocument(id_='a', text='a')
    b = RetrievedDocument(id_='b', text='b')
    batches = [RecallBatch('dense', 0, 'q', (a, a, b), 'available'),
               RecallBatch('lexical', 0, 'q', (b, a), 'available')]
    ranked = fuse_batches(batches, RetrievalPolicy(enabled=True))
    assert [d.doc_id for d in ranked] == ['a', 'b']
    assert ranked[0].retrieval_metadata['fusion_score'] == pytest.approx(1/61 + 1/62)
```

Add `test_duplicate_variant_does_not_multiply_branch_weight`, `test_stable_tie_order`, `test_raw_scores_survive_fusion`, `test_failed_branch_is_not_empty`, `test_nonfinite_policy_rejected`, `test_enrichment_retains_original_and_exact_code`, `test_rewriter_failure_falls_back`, `test_rewriter_receives_user_turns_only`.
- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_fusion.py libs/kotaemon/tests/test_query_enrichment.py -q`; expected missing modules/functions.
- [ ] **Implement:** Deduplicate each route before assigning one-based ranks. Sum `branch_weight/route_count/(60+rank)`; retain first-seen route order then ID for ties; cap fused pool after merge. Clone documents before adding retrieval_metadata so independent arms do not mutate shared candidates. Keep raw score and route rank separately. Enrichment emits bounded soft queries only; it has no scope parameter or authority.
- [ ] **Run GREEN:** Repeat RED command. Verify no model/network imports in pure policy modules.
- [ ] **Acceptance/review:** Hand-calculated fusion matches; query count cannot inflate total branch weight; original retained and no scope claims emitted. Commit named files with `feat: add bounded query routes and weighted RRF`.

### Task 4: Public BGE adapters and scope-safe retrieval integration

**Files:**
- Create: `libs/kotaemon/kotaemon/models/__init__.py`, `local_bge.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_models.py` (compatibility reexports), `local_experiment.py` (public adapter imports)
- Modify: `libs/kotaemon/kotaemon/indices/vectorindex.py`, `libs/kotaemon/kotaemon/indices/knowledge/retrieval/knowledge_service.py`
- Test: `libs/kotaemon/tests/test_knowledge_pipeline_v3.py`, `test_public_bge.py` **new**

**Interfaces:**
- Public `BgeM3Embeddings`, `BgeM3Reranking` keep existing constructor/run/metadata API; preserve `LocalModelPaths/LocalModelMetadata` compatibility exports.
- Add `.score_pairs(query: str, documents: Sequence[Document]) -> tuple[float, ...]` in input order. `run()` returns cloned documents in score order with `retrieval_metadata['rerank_score']` and model/truncation metadata. Validate finite outputs and exact score count.
- `KnowledgeService.search` gains optional `enriched_query: EnrichedQuery | None=None`, `retrieval_policy: RetrievalPolicy | None=None` keywords, keeping return type and old callers.
- `VectorRetrieval.run` accepts these optional keywords and explicit candidate depth. Service computes hard scope from original `query`; planner may use standalone text within the bounded catalog. Every route shares authorized scope and fallback_scope. Final authorization remains mandatory.

- [ ] **RED tests:** Spy backend receives original ordered query/passage pairs and returns `[0.1, 0.9]`; assert output IDs reverse, raw vector scores remain, and rerank scores are available. Write `test_empty_visibility_does_not_enrich_or_retrieve`, `test_rewritten_name_cannot_escape_path_filter`, `test_all_variants_use_same_hard_scope`, `test_one_branch_failure_degrades`, `test_both_branches_fail_raises`, `test_disabled_policy_retains_legacy_merge`, `test_malicious_reranker_id_is_filtered`.

```python
def test_public_bge_pair_scores_keep_input_order(tmp_path):
    class Backend:
        def compute_score(self, pairs, **kwargs):
            assert pairs == [('q', 'first'), ('q', 'second')]
            return [0.1, 0.9]
    model = BgeM3Reranking(tmp_path, backend=Backend())
    docs = [Document(id_='a', text='first'), Document(id_='b', text='second')]
    assert model.score_pairs('q', docs) == (0.1, 0.9)
    assert [d.doc_id for d in model.run(docs, 'q')] == ['b', 'a']
```

Use existing scoped-retrieval fake catalog/store fixtures for service assertions; ensure tests assert zero backend calls for empty authorization.
- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_public_bge.py libs/kotaemon/tests/test_knowledge_pipeline_v3.py -q`.
- [ ] **Implement:** Relocate adapters/provenance helpers without optional imports at module import time. Preserve offline preflight and tests. In v3 collect route batches, filter each against hard scope, fuse once, rerank once on the standalone query, filter again, then use existing diversity. Preserve legacy path when policy disabled. Trace route status, score availability, observed candidate depth, fusion order, model revision, errors, and fallback. Branch error does not trigger broad scope retry.
- [ ] **Run GREEN/regressions:** `uv run --package ktem pytest libs/kotaemon/tests/test_public_bge.py libs/kotaemon/tests/test_knowledge_pipeline_v3.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py libs/kotaemon/tests/test_knowledge_eval_local_models.py libs/kotaemon/tests/test_knowledge_retrieval_eval.py -q`.
- [ ] **Acceptance/review:** Product v3 uses existing stores and authorization lifecycle; local BGE public import works offline with fake backend; legacy reports/tests unchanged. Commit named files with `feat: integrate scoped route fusion and public BGE reranking`.

### Task 5: Authorized evidence expansion and generator budgets

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/retrieval/expansion.py`, `context_budget.py`
- Modify: `libs/kotaemon/kotaemon/indices/qa/format_context.py` (expose formatter to packer; preserve legacy `run`)
- Test: `libs/kotaemon/tests/test_knowledge_expansion.py`, `test_knowledge_context_budget.py` **new**

**Interfaces:**
- `ChunkResolver(*, docstore, catalog)`; `.neighbors(seed: RetrievedDocument, *, allowed_chunk_ids: frozenset[str]) -> tuple[Document, ...]` reads at most the two persisted `previous_chunk_id`/`next_chunk_id` pointers from a seed. Before any docstore read it intersects pointers with `allowed_chunk_ids`, which already includes caller visibility and explicit path/type/entity filters. It resolves authoritative ownership through `catalog.source_ids_for_chunk_ids(candidate_ids, allowed_source_ids=...)`, then validates matching source/version/unit with ordinal exactly `seed.ordinal ± 1` on fetched records. The snapshot catalog receives the same reverse-lookup method in Task 6. It never builds a per-query whole-corpus adjacency index.
- `ExpansionPolicy(max_neighbors_each_side=1, max_total_evidence=15, max_per_source=8, max_neighbor_chars=4000)`; no setting may increase sides beyond 1 in v3.
- `EvidenceBundle(seeds: tuple[RetrievedDocument,...], expansions: tuple[RetrievedDocument,...], decisions: tuple[dict,...])`.
- `expand_evidence(seeds, *, query: str, resolver: ChunkResolver, allowed_chunk_ids: frozenset[str], scorer: BgeM3Reranking | None, policy: ExpansionPolicy) -> EvidenceBundle`.
- `pack_evidence(bundle: EvidenceBundle, *, budget: GenerationBudget, count_tokens: Callable[[str],int], base_prompt: str, render_context: Callable[[Sequence[RetrievedDocument]],str]) -> PackedContext`.
- Available evidence capacity is context minus counted base prompt, output reserve, format reserve. `base_prompt` contains actual system/question/bounded history. Count full rendered evidence on each insertion. Exact final payload recheck is mandatory in adapter before HTTP call.

- [ ] **RED tests:** Use synthetic DS/catalog and deterministic scorer. Test `test_neighbor_not_in_authorized_catalog_is_never_read`, `test_explicit_metadata_filter_excludes_neighbor_before_read`, `test_neighbor_lookup_reads_at_most_two_ids`, `test_same_unit_wrong_version_is_rejected`, `test_nonreciprocal_or_wrong_ordinal_pointer_is_rejected`, `test_legacy_metadata_skips_expansion`, `test_scorer_missing_skips_expansion`, `test_neighbor_below_lowest_seed_score_is_rejected`, `test_neighbor_score_equal_to_seed_floor_is_accepted`, `test_full_seed_text_is_scored`, `test_oversized_neighbor_is_rejected_before_score`, `test_seed_first_packing`, `test_no_seed_fits_means_insufficient`, `test_rendered_header_counts_in_budget`.

```python
def test_no_seed_fits_means_insufficient():
    seed = RetrievedDocument(id_='s', text='x' * 100)
    neighbor = RetrievedDocument(id_='n', text='ok')
    bundle = EvidenceBundle((seed,), (neighbor,), ())
    packed = pack_evidence(bundle, budget=GenerationBudget(20, 5, 0),
        count_tokens=len, base_prompt='base',
        render_context=lambda docs: ''.join(d.text for d in docs))
    assert packed.status == 'insufficient_evidence'
    assert packed.documents == ()
```

- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_expansion.py libs/kotaemon/tests/test_knowledge_context_budget.py -q`.
- [ ] **Implement:** Follow only the two persisted pointer IDs. Check each pointer against the hard allowed chunk set before fetching and recheck authoritative catalog ownership through the existing SQL reverse lookup, reciprocal pointer, version/unit/ordinal, and explicit metadata constraints on the fetched Document. Missing, duplicate, stale, or inconsistent pointers are rejected; legacy records skip expansion. Score full seeds to establish relative floor; finite score required. Reject oversized neighbors rather than cutting them; no scorer skips all expansion. Deduplicate real IDs/text/overlaps and apply evidence caps. Pack all seed candidates in rerank order before neighbors, skipping too-large units; emit exact IDs/omission reasons. Never synthesize parent text or attach neighbor body to seed ID.
- [ ] **Run GREEN/regressions:** Repeat RED command plus `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py -q`.
- [ ] **Acceptance/review:** Zero unauthorized reads/context, correct relative gate, whole units, no expansion-only generation, exact citation/context ID set. Commit named files with `feat: add authorized expansion and seed-first context budgets`.

### Task 6: Shared runtime and opt-in product/workbench entry points

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/runtime/__init__.py`, `runtime/index.py`, `libs/kotaemon/kotaemon/indices/knowledge/evaluation/snapshot_adapter.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_experiment.py` (compatibility wrappers only)
- Modify: `libs/ktem/ktem/local_qa_core.py`, `local_qa_playground.py`, `local_qa_ollama.py`
- Modify: `libs/ktem/ktem/index/file/pipelines.py`, `knowledge_service.py`, `libs/ktem/ktem/reasoning/simple.py`
- Modify: `docs/local-qa-playground.md`
- Test: `libs/ktem/ktem_tests/test_local_qa_pipeline_v3.py` **new**, existing `test_local_qa_playground.py`

**Interfaces:**
- Core `build_knowledge_runtime(documents: Sequence[Document], *, catalog: SourceCatalog, embedding: BaseEmbeddings, reranker: BaseReranking | None, policy: RetrievalPolicy, lexical: bool=False) -> KnowledgeRuntime` lives in `knowledge/runtime/index.py`. It imports neither `knowledge.evaluation` nor private `_make_bundle/_service` helpers.
- Snapshot adapter `build_snapshot_runtime(snapshot: LocalSnapshot, *, embedding: BaseEmbeddings, reranker: BaseReranking | None, policy: RetrievalPolicy, chunking_mode: Literal['token', 'registry']='token', lexical: bool=False) -> SnapshotRuntime` lives in `knowledge/evaluation/snapshot_adapter.py`. It converts reviewed snapshot units into Documents and a catalog, then calls the core builder. The workbench may depend on this adapter because its input is specifically an evaluation snapshot; the product path depends only on the core runtime/policies.
- `KnowledgeRuntime` exposes `service: KnowledgeService`, `docstore`, `catalog`, `documents`, `close()`. `SnapshotRuntime` additionally exposes `chunk_to_source`, `source_labels`, `locators`. Move snapshot document conversion from `_build_chunk_documents` into the adapter. Existing `_make_bundle(snapshot, embedding, chunking_arm)` maps `chunking_arm=False` to `chunking_mode='token'` and `chunking_arm=True` to `chunking_mode='registry'`; `_service` retains its supplied rerankers, vector-only mode, and legacy policy. This preserves all four frozen-v2 arm configurations, candidate IDs, fingerprints, and scores on rerun.
- Snapshot adapter stamps adjacency from existing reviewed SourceUnit/DraftChunk mappings in memory, using approved source hashes and the same real pointer IDs as Task 1; it does not reparse v2. Its snapshot catalog implements `source_ids_for_chunk_ids` with the same visibility semantics as the SQL catalog. Ambiguous offsets/unit mapping skips expansion. `chunking_mode='registry'` creates a separate in-memory index with mapped offsets; it never writes snapshot files. The mode is recorded in runtime config and drives Task 8 arm selection.
- `LocalQA.retrieve(question: str, *, user_history: Sequence[str]=(), generation_budget: GenerationBudget | None=None, count_tokens=None, base_prompt: str='') -> tuple[EvidenceCard,...]` remains compatible; internal result has `packed_context`, `trace`, `diagnostics`, `status`. Add `retrieve_result(...) -> LocalQAResult` so generation consumes exactly included cards. `LocalQAResult` fields: `cards`, `packed_context`, `trace`, `diagnostics`, `status`.
- Expansion authorization is the hard mandatory source/chunk intersection computed for the current request (visibility plus path/type/entity filters), not merely all user-visible chunks. Add `KnowledgeService.authorized_chunk_ids(*, path=None, source_types=None, filters=None, allowed_source_ids=None) -> frozenset[str]` using the same constraint resolution as search; reuse the internal resolution helper rather than duplicating rules. Both entry points pass this set to the resolver.
- Product explicit settings `v3_enabled=False`, `candidate_k=20`, `max_fused_candidates=40`, `query_enrichment=False`, `evidence_expansion=False`. Existing top_k remains chunk seed K; workbench K=5 distinct sources selects seed window before expansion. Trace both semantics.
- Ollama client supports budget/counter settings, matching Qwen tokenizer from already local files when available, conservative `len(text.encode('utf-8'))` counter otherwise and `estimated=True`; no tokenizer download. Set output limit/context options explicitly and validate final rendered request messages before send.

- [ ] **RED tests:** Spy public runtime instead of private experiment functions. Test `test_core_runtime_does_not_import_evaluation`, `test_snapshot_builder_token_and_registry_modes_are_distinct`, `test_frozen_v2_token_and_registry_wrappers_retain_candidate_ids`, `test_frozen_v2_reranker_wrapper_retains_candidate_order`, `test_workbench_uses_public_runtime_and_reranker`, `test_fts_unavailable_shows_degraded_stack`, `test_generator_receives_only_packed_cards`, `test_no_seed_fit_skips_ollama`, `test_estimated_budget_is_labeled`, `test_product_disabled_preserves_selected_file_contract`, `test_product_v3_empty_selection_skips_rewrite`, `test_agent_global_uses_visible_catalog`, `test_agent_allowlist_cannot_expand_visibility`. Last two test actual factory + service caller; do not invent deployment claims.
- [ ] **Run RED:** `uv run --package ktem pytest libs/ktem/ktem_tests/test_local_qa_pipeline_v3.py -q`.
- [ ] **Implement:** Put shared runtime construction in `knowledge/runtime/index.py`; keep snapshot-to-Document conversion in the evaluation adapter. Preserve the old evaluator's exact baseline chunk text, IDs, query order, and default retrieval config. The public builder invokes shared policies, uses FTS5 for local lexical storage and configured product backend in product. Workbench passes verified BGE reranker, displays route/fusion/rerank/expansion/packing diagnostics without persisting user data. Product prepares budgeted evidence only under explicit expansion setting; old formatting stays callable. Add loopback-only configuration validation for any new Ollama endpoint. Streaming and nonstreaming generation share one packing/request path. Clearly label source K versus chunk seed count.
- [ ] **Run GREEN/regressions:** `uv run --package ktem pytest libs/ktem/ktem_tests/test_local_qa_pipeline_v3.py libs/ktem/ktem_tests/test_local_qa_playground.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py libs/kotaemon/tests/test_knowledge_eval_local_experiment.py -q`.
- [ ] **Acceptance/review:** Both entry points use common services/policies; workbench has real rerank and lexical diagnostics; disabled product behavior compatible; citation evidence equals generation payload; no private source writes. Commit named files with `feat: wire shared v3 retrieval into product and local workbench`.

### Task 7: Bounded per-session multi-turn retrieval

**Files:**
- Create: `libs/ktem/ktem/local_qa_conversation.py`
- Modify: `libs/ktem/ktem/local_qa_playground.py`, `local_qa_core.py`, `local_qa_ollama.py`, `libs/ktem/ktem/reasoning/simple.py`
- Test: `libs/ktem/ktem_tests/test_local_qa_conversation.py` **new**, `libs/kotaemon/tests/test_query_enrichment.py`

**Interfaces:**
- `ConversationState(user_turns: tuple[str,...]=())` immutable; `.append_user(question: str, *, max_turns: int, token_limit: int, count_tokens) -> ConversationState`; `.clear() -> ConversationState`.
- `OllamaQueryRewriter(client: OllamaLocalClient, *, timeout: float=10.0)` callable `(query: str, user_turns: tuple[str,...]) -> str`; loopback validation and bounded request, original fallback handled by QueryEnricher.
- Default UI limits: last 3 user turns, 1024 history counter units, max 3 total variants. Use Gradio session State, never module global history. Default rewriting remains opt-in. Clear removes state plus existing outputs.
- Topic changes use current question; only clear follow-up markers/ellipsis trigger history rewrite. Rewriter response is a bounded plain question, no scope fields. Prior assistant outputs may remain generation history in product, but are not supplied as rewrite evidence/hard scope.

- [ ] **RED tests:** `test_followup_receives_bounded_user_history`, `test_topic_switch_uses_original_question`, `test_two_gradio_sessions_are_isolated`, `test_clear_drops_history`, `test_failed_generation_does_not_create_assistant_evidence`, `test_rewrite_timeout_uses_original`, `test_history_budget_uses_same_generator_counter`, `test_followup_cannot_override_current_source_selection`.

```python
def test_two_sessions_are_isolated():
    first = ConversationState().append_user('VPN resets?', max_turns=3,
        token_limit=100, count_tokens=len)
    second = ConversationState()
    assert first.user_turns == ('VPN resets?',)
    assert second.user_turns == ()
    assert first.clear().user_turns == ()
```

- [ ] **Run RED:** `uv run --package ktem pytest libs/ktem/ktem_tests/test_local_qa_conversation.py -q`.
- [ ] **Implement:** Bind state to Ask/Clear and streaming callbacks; read history before appending current turn, append nonempty user turn once. Apply bounded history consistently to enrichment and generation budget. Product retrieval uses QueryEnricher on user turns extracted from existing history, keeping original question for generator and QA trace. No persistence to snapshot/log and no assistant-as-evidence shortcut.
- [ ] **Run GREEN/regressions:** `uv run --package ktem pytest libs/ktem/ktem_tests/test_local_qa_conversation.py libs/ktem/ktem_tests/test_local_qa_pipeline_v3.py libs/ktem/ktem_tests/test_local_qa_playground.py libs/kotaemon/tests/test_query_enrichment.py -q`.
- [ ] **Acceptance/review:** Isolated sessions, clear reset, bounded follow-up retrieval, safe topic switch, original question preserved and current authorization enforced. Commit named files with `feat: add bounded session-local retrieval history`.

### Task 8: Versioned combination/ablation and conversation evaluations

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/combination_eval.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_cli.py`, `source_metrics.py`
- Create: `libs/kotaemon/tests/test_knowledge_combination_eval.py`, `libs/ktem/ktem_tests/test_knowledge_conversation_eval.py`
- Create: `docs/superpowers/reports/agent-rag-pipeline-v3-evaluation.md` only after measured run; otherwise create `docs/superpowers/reports/agent-rag-pipeline-v3-validation.md` with implementation checks and explicit unavailable measurements.
- Modify: `docs/local-qa-playground.md` with actual flags and degraded configurations.

**Interfaces:**
- `run_combination_experiment(snapshot: LocalSnapshot, *, model_paths: LocalModelPaths, artifact_dir: Path, conversation_fixture: Path | None=None) -> CombinationReport`.
- `CombinationReport` contains snapshot/model/config fingerprints, arm configurations, per-arm source metrics and denominators, candidate recall, final-context anchor coverage, stage durations, p50/p95, token usage, route statuses, invariants, artifact digest manifest. Generation metrics nullable with explicit `not_run` reason; no numbers inferred from retrieval-only runs.
- New CLI `combination-experiment` accepts `--local-root`, `--snapshot`, `--embedding-model-dir`, `--reranker-model-dir`, `--artifact-dir`, optional `--conversation-fixture`. Reject destination overwrite, path escape/symlinks, unreviewed fixture, or unknown/label-leaking source metadata.
- Conversation fixture schema: version, reviewed flag, immutable case IDs, user turn sequence, per-turn allowed sources, expected relevant sources/anchors, topic-switch/no-answer labels. Synthetic test fixture uses synthetic text only; real reviewed fixture lives under ignored local root.

- [ ] **RED tests:** `test_v2_inputs_unchanged_after_combination`, `test_arm_configurations_express_only_declared_changes`, `test_ablations_disable_exactly_one_final_component`, `test_candidate_recall_precedes_rerank`, `test_anchor_coverage_uses_final_packed_context`, `test_generation_not_run_has_no_answer_score`, `test_source_k_not_confused_with_expanded_chunks`, `test_evidence_allowlist_preserves_explicit_metadata_filters`, `test_trace_context_ids_equal_payload`, `test_rejects_artifact_overwrite`, `test_conversation_fixture_is_separate_and_reviewed`. Use fake BGE/FTS/generator and temporary synthetic approved snapshot; record input file hashes before/after.
- [ ] **Run RED:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_combination_eval.py libs/ktem/ktem_tests/test_knowledge_conversation_eval.py -q`.
- [ ] **Implement fixed arms:** dense baseline using token chunks/BGE-M3; registry chunking; registry + lexical/RRF; preceding + BGE rerank; preceding + enrichment; preceding + expansion. All arms share source/judgment/query order, model manifest, candidate K=20 per route, final source K=5, seed/counter budgets. Final-config leave-one-out arms disable chunking, lexical/RRF (dense-only), rerank (expansion gate explicitly unavailable), enrichment, and expansion. Record coupled dependencies: removing rerank also removes expansion scoring, so that ablation is not an isolated rerank-only causal estimate. Include an expansion scorer supplied independently arm if an isolated rerank effect is needed.
- [ ] **Implement reporting:** Reuse public runtime and existing source scorer. Measure candidate recall at the actual candidate cutoff; include final-context coverage and eligible/unresolved anchors. For human answer/citation judgments, export local answer records plus a reviewed judgment template; compute answer support/citation precision only after those judgments exist. Separate no-answer correctness from model failure. Write new artifact staging directory then atomic publish with digests. Publish aggregate metrics only, never query text/traces into tracked report.
- [ ] **Run GREEN/regressions:** `uv run --package ktem pytest libs/kotaemon/tests/test_knowledge_combination_eval.py libs/ktem/ktem_tests/test_knowledge_conversation_eval.py libs/kotaemon/tests/test_knowledge_eval_local_experiment.py libs/kotaemon/tests/test_knowledge_eval_source_metrics.py libs/kotaemon/tests/test_knowledge_eval_local_snapshot.py -q`.
- [ ] **Measured local run:** Resolve actual approved/model paths from local manifest without printing private source content. Set task-specific shell variables `rag_v3_local_root`, `rag_v3_snapshot`, `rag_v3_embedding`, `rag_v3_reranker`, `rag_v3_run` to those verified absolute paths. Run:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli combination-experiment --local-root "$rag_v3_local_root" --snapshot "$rag_v3_snapshot" --embedding-model-dir "$rag_v3_embedding" --reranker-model-dir "$rag_v3_reranker" --artifact-dir "$rag_v3_run"
```

Expected: new artifact directory, unchanged v2 hashes, all zero-violation invariants, per-arm measured metrics/statuses. For a separately reviewed conversation fixture run add `--conversation-fixture "$rag_v3_conversation_fixture"`; do not fabricate review or metrics if unavailable. CPU latency may be large; record actual device and sample count. Pair comparisons per question; bootstrap intervals may be added but never characterize an unmeasured interval as significant.
- [ ] **Acceptance/review:** New run identity, no gold edits/label leakage, metrics use their defined stage/K, manifests reproducible, combination deltas labeled incremental/combined, no enterprise performance claim from mini corpus. Commit named source/tests and aggregate docs with `feat: evaluate v3 combinations and conversation fixtures`.

## Final review and handoff

- [ ] Inspect `git diff --check` and named changed files; ensure private data/model artifacts are absent from staged files.
- [ ] Run the named v3 test suite once after final integration, plus existing scope/chunking/snapshot/local-model/workbench regression commands above. Broaden only if a changed path or failure justifies it.
- [ ] Confirm zero unauthorized candidates/expansions/context, budget adherence under the selected counter, citation map identity, disabled compatibility, and snapshot file hashes.
- [ ] Record measured versus unavailable checks separately. An estimated tokenizer budget guarantees the configured counter limit, not an exact Qwen token count; label this in UI/report.
- [ ] Obtain the requested final reviewer gate before integrating the development branch. Neither factory creation nor a workbench demo proves deployment of an Agent tool or an enterprise ACL provider.

## Design coverage/self-review

Parsing/provenance/structure: Task 1. FTS5: Task 2. Enrichment/multi-query/RRF: Tasks 3–4. Public BGE: Task 4. Relative evidence gate/adjacency/budget/citations: Task 5. Product/workbench/common runtime: Task 6. Multi-turn: Task 7. Combination, ablation, anchors, answer/citation judgments and immutable artifacts: Task 8. All new behavior has a disabled/legacy path; hard authorization precedes enrichment and is rechecked after rerank and expansion. The only prerequisite not supplied by code is reviewed real conversation/answer judgments; tests and retrieval evaluations remain executable independently and must state that those quality measurements are unavailable until supplied.
