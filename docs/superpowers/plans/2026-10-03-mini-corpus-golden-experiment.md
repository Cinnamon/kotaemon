# Mini-Corpus Golden Experiment Implementation Plan

> **For agentic workers:** Implement each task with GPT-6 Luna Max using TDD. After each task, request a GPT-6 Sol Medium review. Fix review findings with Luna Max and request another Sol Medium review before starting the next task.

**Goal:** Create a private, reviewed v1 golden snapshot from 20–24 local documents and measure one baseline plus controlled chunking, embedding, and reranker variants using four fixed K=5 metrics.

**Architecture:** Add local-only corpus preparation and immutable snapshot validation to Kotaemon's evaluation package. Run each retrieval arm through the existing knowledge retrieval service using source-level judgments, stable evidence anchors, vector-only retrieval, and a 20-chunk candidate pool; keep model weights and all source-derived artifacts out of Git.

**Tech Stack:** Python 3.10+, Kotaemon `DocumentIngestor` and chunk-strategy registry, `KnowledgeService`, `VectorRetrieval`, local BGE-M3 models via FlagEmbedding, pytest, JSON/JSONL, SHA-256.

## Global Constraints

- Select 20–24 unique documents for v1 and cover each usable file type and substantive content topic.
- Freeze source-level judgments and evidence anchors; never mutate frozen gold when a chunker produces new chunk IDs.
- The four main metrics are macro Hit@5, macro Recall@5, macro MRR@5, and pooled Wrong-scope@5 over distinct source results.
- Every arm requests M=20 vector candidates with `first_round_top_k_mult=1`, no result extension, and no parent/section cap; it scores the first five distinct sources after the same duplicate/diversity post-processing.
- Compare the main-branch token-only 1,024/256 baseline with this branch's source-aware chunker, BGE-M3 dense embeddings, and BGE reranker-v2-m3, one factor at a time.
- Do not send source text or queries to remote services.
- Keep all source-derived files under the Git-ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/` tree.
- CI tests use only generated fixtures and do not load user documents or model weights.
- Do not compute gold-based metrics until the user approves and freezes v1 labels.

---

### Task 1: Deterministic Local Corpus Inventory

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_corpus.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_corpus.py`
- Create: `libs/kotaemon/tests/knowledge_eval_test_fixtures.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/__init__.py`

**Interfaces:**
- `scan_sources(root: Path) -> tuple[SourceFile, ...]`
- `SourceFile` contains `source_id`, `relative_path`, `sha256`, `suffix`, `byte_size`, and `duplicate_of`.
- `source_id` is a stable SHA-256-derived identifier; duplicate files retain all relative paths but only one source is indexable.
- Create `libs/kotaemon/tests/knowledge_eval_test_fixtures.py` for `document(doc_id, text)` and `make_generated_corpus(root)`; later tests define their snapshot and fake-model fixtures beside the tests that use them.

- [ ] **Step 1: Add failing tests** for stable source IDs, deterministic ordering, exact-byte deduplication, and excluding `.DS_Store`, office `~$` locks, symlinks, and unsupported files.

```python
def test_scan_sources_deduplicates_bytes_and_excludes_lock_files(tmp_path):
    root = tmp_path / "sources"
    root.mkdir()
    (root / "a.md").write_text("same evidence", encoding="utf-8")
    (root / "b.md").write_text("same evidence", encoding="utf-8")
    (root / "~$draft.docx").write_bytes(b"lock")
    (root / ".DS_Store").write_bytes(b"metadata")

    rows = scan_sources(root)

    assert len(rows) == 2
    assert rows[0].source_id == rows[1].source_id
    assert {row.duplicate_of for row in rows} == {None, "a.md"}
```

- [ ] **Step 2: Run the focused test** and confirm the missing API fails.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py -q`

Expected: FAIL because `scan_sources` is not implemented.

- [ ] **Step 3: Implement inventory with no writes to source files.** Hash each supported regular file, normalize the displayed path to a repository-relative path, order rows by normalized path, and pick the first path for each digest as the canonical source.
- [ ] **Step 4: Re-run the focused test** and confirm all generated-fixture assertions pass.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: inventory local evaluation corpus`.

### Task 2: Local Parsing, Chunk Drafts, and Evidence Anchors

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_ingest.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_ingest.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_corpus.py`

**Interfaces:**
- `build_local_draft(root: Path, output_dir: Path, *, sample_ids: Sequence[str] | None = None) -> DraftSummary`
- `DraftSummary` reports parsed source IDs, content-derived topic candidates, page/row extraction quality, baseline chunks, stable chunk IDs, and excluded inputs. Topic candidates come from extracted headings/text only; missing candidates stay empty and marked for review rather than being inferred from directories.
- Since this API has no query input, `DraftSummary.anchors_payload` is deterministically empty; do not invent query IDs or relevance labels during parsing. Query-linked anchors are created only after candidate questions and evidence spans exist, and Task 3 validates coverage for every relevant query/source pair.
- `DraftSummary.records_payload` and `DraftSummary.anchors_payload` are deterministic UTF-8 byte strings used by the test to compare separate output directories. The records contain root-relative provenance only, never absolute reader paths.
- `build_local_draft` writes only below its caller-supplied `output_dir`; production callers must pass a path under the ignored `local/draft/` tree. Synthetic CI tests may use pytest temporary directories.

- [ ] **Step 1: Add failing generated-fixture tests** for Markdown headings, generated PDF pages, DOCX paragraphs, and XLSX rows. Assert reader locators survive chunking, chunk IDs repeat across runs, empty/failed extraction is reported, chunk offsets resolve to normalized source-unit text, duplicate bytes are parsed once, and the query-linked anchor payload stays empty at this stage. Cover an empty PDF page and a blank spreadsheet row in quality counts.

```python
def test_build_local_draft_is_stable_and_reports_empty_pages(tmp_path):
    root = make_generated_corpus(tmp_path / "sources")

    first = build_local_draft(root, tmp_path / "draft-a")
    second = build_local_draft(root, tmp_path / "draft-b")

    assert first.records_payload == second.records_payload
    assert first.anchors_payload == second.anchors_payload
    assert first.quality.empty_locators
```

- [ ] **Step 2: Run the focused test** and confirm it fails at the first absent parser/draft function.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_ingest.py -q`

Expected: FAIL because `build_local_draft` is not implemented.

- [ ] **Step 3: Implement parsing with the existing normal PDF, Unstructured (`split_documents=True`), text, and Excel row readers.** Use the main-branch token-only splitter at 1,024/256 to store baseline chunks; retain reader locations and deterministic content offsets. Record parser/splitter configuration and objective extraction counts; report empty PDF pages and per-sheet extracted/blank row counts; flag empty or unusable locators for review without silently dropping nonempty sources. Do not invent a numeric low-quality threshold. Chunk IDs include a versioned configuration, source hash, locator/unit and chunk ordinals, and chunk-text digest. Put outputs only beneath the caller-supplied directory; the production CLI enforces that this resolves under ignored `local/draft/`, while generated-fixture tests use temporary paths.
- [ ] **Step 4: Re-run the focused test** and verify stable source/chunk IDs and quality reporting.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: prepare local corpus review drafts`.

### Task 3: Immutable Source-Level Snapshot Validation

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_snapshot.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_snapshot.py`
- Modify: `libs/kotaemon/tests/fixtures/knowledge_eval/README.md`

**Interfaces:**
- `load_local_snapshot(path: Path, *, require_reviewed: bool = True) -> LocalSnapshot`
- Required payloads: `records.json`, `judgments.jsonl`, `anchors.jsonl`, and `manifest.json`.
- `LocalSnapshot` contains `root`, verified source records, source-level `EvaluationFixture`, evidence anchors, and a snapshot fingerprint.

- [ ] **Step 1: Add failing tests** for correct snapshot loading and rejection of a missing payload, mismatched payload hash, unreviewed manifest, mixed judgment levels, unknown source IDs, unknown evidence query/source pairs, missing anchor for a relevant query/source pair, duplicate anchor IDs, empty evidence spans, and wrong-scope sources that are also relevant.

The test module builds a valid `reviewed_snapshot` fixture with three canonical JSON payloads and a manifest containing exact SHA-256 values; each failure case mutates exactly one relation or payload after the valid fixture is created.

```python
def test_load_local_snapshot_rejects_changed_anchor_bytes(reviewed_snapshot):
    anchor_path = reviewed_snapshot / "anchors.jsonl"
    anchor_path.write_bytes(anchor_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="anchors.jsonl.*hash"):
        load_local_snapshot(reviewed_snapshot)
```

- [ ] **Step 2: Run the focused test** and confirm it fails because the loader is missing.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_snapshot.py -q`

Expected: FAIL because `load_local_snapshot` is not implemented.

- [ ] **Step 3: Implement fail-closed validation.** Hash exact payload bytes; validate every source, judgment, and anchor relation; require `review_status="approved"` for evaluation; do not change the tracked synthetic fixture default.
- [ ] **Step 4: Re-run the focused test** and confirm corrupt or unreviewed snapshots fail before retrieval.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: validate local evaluation snapshots`.

### Task 4: Distinct-Source K=5 Scoring and Anchor Coverage

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/source_metrics.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_source_metrics.py`
- Modify: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/__init__.py`

**Interfaces:**
- `source_ranked_chunks(ranked_chunks: Sequence[Document], chunk_to_source: Mapping[str, str], *, limit: int) -> tuple[Document, ...]`
- `score_source_run(cases, results_by_query_id, *, k: int, chunk_to_source) -> RunMetrics`
- `anchor_coverage(anchors, chunks) -> AnchorCoverage`
- `AnchorCoverage` contains `total_anchors`, `covered_anchors`, `unmapped_anchor_ids`, and `rate` (`None` when there are no anchors).

- [ ] **Step 1: Add failing tests** proving repeated chunks do not consume source ranks, MRR uses first distinct relevant source rank, Recall uses the number of relevant sources, and Wrong-scope numerator/denominator count distinct source results only for explicitly labeled queries. Add an anchor test for exact query/page/row/section mapping and an unmapped anchor.

```python
def test_source_window_deduplicates_sources_before_k5_metrics():
    chunks = [document("a-1"), document("a-2"), document("b-1")]
    mapping = {"a-1": "source-a", "a-2": "source-a", "b-1": "source-b"}

    window = source_ranked_chunks(chunks, mapping, limit=5)

    assert [item.doc_id for item in window] == ["a-1", "b-1"]
```

- [ ] **Step 2: Run the focused test** and confirm the source-level helper is absent.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_source_metrics.py -q`

Expected: FAIL because `source_ranked_chunks` is not implemented.

- [ ] **Step 3: Implement source projection before the existing `score_run`.** Pass one first-ranked representative chunk per source to the existing evaluator so its source-level MRR rank, Hit/Recall unit, and Wrong-scope denominator all use the same distinct-source window.

```python
def source_ranked_chunks(ranked_chunks, chunk_to_source, *, limit):
    selected, seen_sources = [], set()
    for chunk in ranked_chunks:
        source_id = chunk_to_source[chunk.doc_id]
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        selected.append(chunk)
        if len(selected) == limit:
            break
    return tuple(selected)
```

- [ ] **Step 4: Re-run the focused test** and verify metric numerators and denominators against hand-calculated values.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: score distinct source retrieval results`.

### Task 5: Local BGE Model Adapters

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_models.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_models.py`
- Modify: `libs/kotaemon/pyproject.toml`
- Modify: `uv.lock`
- Modify: `libs/kotaemon/tests/fixtures/knowledge_eval/README.md`

**Interfaces:**
- `BgeM3Embeddings(BaseEmbeddings)` loads `BAAI/bge-m3` locally and implements Kotaemon query/document embedding calls; its constructor accepts optional `backend` injection for tests.
- `BgeM3Reranking(BaseReranking)` loads `BAAI/bge-reranker-v2-m3` locally and returns the same documents sorted by cross-encoder score; its constructor accepts optional `backend` injection for tests.
- Both accept a local model path and fail with an actionable error if weights or `FlagEmbedding` are unavailable; neither sends inputs to a remote service.
- `LocalModelPaths` has `embedding_model_dir: Path` and `reranker_model_dir: Path`; it is the same type used by `run_local_experiment` in Task 6.
- Query vectors use `BGEM3FlagModel.encode_queries`; chunk vectors use `encode_corpus`; reranker scores use `FlagReranker.compute_score` on `(query, chunk_text)` pairs.

- [ ] **Step 1: Add failing tests** using injected fake encoders/rankers to verify query-vs-passage calls, embedding dimension consistency, score ordering, stable input-document identity, and fail-fast behavior for absent local models.

The test module defines `fake_flag_embedding` with `encode_queries`, `encode_corpus`, and `compute_score`; patch the lazy backend loader to raise `ImportError` for the missing-package test.

```python
def test_bge_reranker_preserves_documents_and_sorts_by_score(fake_flag_embedding):
    reranker = BgeM3Reranking(model_path="local-model", backend=fake_flag_embedding)
    docs = [document("first", "low"), document("second", "high")]

    result = reranker.run(docs, query="query")

    assert [doc.doc_id for doc in result] == ["second", "first"]
    assert {doc.doc_id for doc in result} == {doc.doc_id for doc in docs}
```

- [ ] **Step 2: Run the focused test** and confirm model adapters are absent.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_models.py -q`

Expected: FAIL because `BgeM3Embeddings` and `BgeM3Reranking` are not implemented.

- [ ] **Step 3: Implement lazy FlagEmbedding wrappers** using only model paths supplied to the local runner. Disable half precision by default; record model revision, weight hashes, device, library version, truncation length, and whether weights were cached or downloaded.

Add a `local-eval = ["FlagEmbedding==1.4.2"]` optional dependency to the `kotaemon` package and refresh `uv.lock`; do not add the model runtime to the app's default dependency set. The `download-models` CLI subcommand uses Hugging Face `snapshot_download` for the two explicit model IDs and records each resolved commit revision before inference.

- [ ] **Step 4: Re-run the focused test** without downloading weights and verify the adapters never mutate input documents.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: add local bge evaluation adapters`.

### Task 6: Four-Arm K=5/M=20 Experiment Runner

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_experiment.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_experiment.py`
- Modify: `libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py`

**Interfaces:**
- `run_local_experiment(snapshot: LocalSnapshot, *, model_paths: LocalModelPaths, artifact_dir: Path) -> ExperimentReport`
- Arms are `baseline`, `chunking`, `embedding`, and `reranker`; each variant carries an explicit component config and signed deltas from baseline.
- The reranker arm shares the baseline index and proves exact ordered vector-candidate identity before reranking.
- `ExperimentReport` contains `k=5`, `candidate_k=20`, an `arms` mapping, per-metric baseline values and signed deltas, query counts, wrong-scope numerators/denominators, and an artifact manifest.
- Each arm report contains pre-reranker `vector_candidate_ids`, reranker `input_candidate_ids`, final ordered result IDs, source-level `RunMetrics`, and a configuration fingerprint.

- [ ] **Step 1: Add failing integration tests** with generated sources and fake models for all four arms. Assert the same reviewed query sequence and filters, K=5, M=20, source-level scoring, only one changed component per arm, and exact baseline/reranker input-list equality.

The integration module defines `fixture_snapshot` from generated documents, approved source-level cases, and evidence anchors. `fake_models` supplies two temporary model paths and patches only the local encoder/reranker factories, never retrieval, indexing, scoring, or trace collection.

```python
def test_reranker_receives_exact_baseline_candidates(fixture_snapshot, fake_models):
    report = run_local_experiment(
        fixture_snapshot,
        model_paths=fake_models.paths,
        artifact_dir=fixture_snapshot.root / "run",
    )

    assert report.arms["baseline"].vector_candidate_ids == report.arms["reranker"].input_candidate_ids
    assert report.k == 5
    assert report.candidate_k == 20
```

- [ ] **Step 2: Run the focused integration test** and confirm the runner is absent.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_experiment.py -q`

Expected: FAIL because `run_local_experiment` is not implemented.

- [ ] **Step 3: Build each arm through the existing chunk strategy, `KnowledgeService`, `VectorRetrieval`, and deterministic in-memory stores.** Baseline uses token-only 1,024/256 plus the existing hashed-feature control. Every retrieval uses `top_k=20`, `first_round_top_k_mult=1`, `do_extend=False`, and `max_per_parent_or_section=None`; compare pre-reranker vector-candidate trace IDs. Chunking changes only to `get_chunk_strategy`; embedding changes only to the local BGE-M3 adapter; reranker changes only to local BGE reranking over the identical baseline index/candidate lists.
- [ ] **Step 4: Re-run the integration test** and confirm report config fingerprints and candidate traces prove one-factor isolation.
- [ ] **Step 5: Request GPT-6 Sol Medium review, resolve findings, and commit** as `feat: run controlled local retrieval experiments`.

### Task 7: Review Package CLI and Private v1 Draft

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_cli.py`
- Create: `libs/kotaemon/tests/test_knowledge_eval_local_cli.py`
- Create locally only: `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/`
- Modify: `libs/kotaemon/tests/fixtures/knowledge_eval/README.md`

**Interfaces:**
- CLI commands: `inventory`, `prepare-review`, `freeze`, `download-models`, and `run`; `run` accepts only a reviewed snapshot and explicit local model paths.
- The v1 review package contains source/topic candidates, duplicates/exclusions, extraction quality, and chunk previews. Questions, judgments, scope labels, and evidence anchors start empty for a person to author and review; the CLI must never invent them.
- `freeze` requires both `--approved-by` and `--approved-at`; `run` requires `--embedding-model-dir` and `--reranker-model-dir`.
- All CLI outputs must resolve beneath the selected `local/` root: drafts under `draft/`, snapshots under `snapshots/`, downloaded weights under `models/`, and results under `runs/`.

**Implementation checkpoint:** The CLI, synthetic tests, and README are implemented. Default `v1` preparation proposes 20–24 usable unique documents by file format and content-derived topic candidates, without using directory names, and lists omitted candidate source/topic pairs as unreviewed coverage gaps. Explicit `--sample-id` selections are checked against the full parse for at least 20 usable chunk-backed documents and coverage of every format with usable documents; rejection errors retain selected extraction diagnostics, and review text lists only formats actually selected. `--all-sources` is available only for non-v1 drafts. In-checkout local roots must be Git-ignored. The schema-v2 model manifest hashes the full regular asset set, and `run` verifies exact filenames and hashes, performs the offline inference preflight before model construction, and publishes the verified manifest with the run artifact bundle. The real-source candidate is prepared in the Git-ignored `local/draft/v1` tree: 22 documents/paths, 306 units, 473 chunks, 26 queries, 36 relevant pairs, and 44 anchors. It remains `draft`. GPT-6 Sol Medium's independent package review is **Ready (0 C/I/M)**; schema, hash, scope, anchor, and privacy checks passed. The candidate is ready for user review. Explicit user approval of labels remains required before freezing gold, downloading or loading models, or running retrieval metrics; none of those actions has occurred.

- [x] **Step 1: Add CLI tests** for the synthetic generated local corpus: no source mutation, no writes outside the chosen ignored directory, deterministic review-package outputs, approval-sidecar validation, model-manifest tampering and ambiguity, `freeze` approval gating, and `run` rejection for a draft snapshot.

The CLI test module defines `make_draft_snapshot(tmp_path)` by writing a generated draft manifest with `review_status="draft"` and the exact payload hashes. It also creates a temporary `local/` tree so output containment is tested without writing into the repository.

```python
def test_run_refuses_a_draft_snapshot(tmp_path):
    draft_snapshot = make_draft_snapshot(tmp_path)
    result = CliRunner().invoke(main, ["run", "--snapshot", str(draft_snapshot)])

    assert result.exit_code != 0
    assert "approved snapshot" in result.output.lower()
```

- [x] **Step 2: Run the focused CLI test** and confirm commands fail because the CLI is absent.

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_cli.py -q`

Expected: FAIL because the CLI is not implemented.

- [x] **Step 3: Implement CLI wrappers over the tested inventory, parser, snapshot, and experiment modules.** The v1 selector proposes 20–24 usable unique documents by file format and content-derived topic candidates. It labels those candidates unreviewed and does not create questions or gold labels. Do not use directory labels as topic truth.

```bash
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli prepare-review --source-root libs/kotaemon/tests/fixtures/knowledge_eval/local/sources --source-root-label libs/kotaemon/tests/fixtures/knowledge_eval/local/sources --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local --version v1
```

- [x] **Step 4: Run the Task 7 synthetic verification suite** and inspect `git status`; 32 focused CLI tests and 167 tests across the seven local-evaluation modules pass, with no real source documents or ignored local artifacts created.
- [x] **Step 5: Request GPT-6 Sol Medium review and resolve findings.** Sol Medium approved after the explicit-sample validation, offline command, and review-wording fixes; code/docs/tests are ready for the root agent to commit and update in the existing PR.
- [x] **Step 6: Prepare, independently review, and present the real local-only v1 candidate package.** The Git-ignored draft contains 22 documents/paths, 306 units, 473 chunks, 26 queries, 36 relevant pairs, and 44 anchors. GPT-6 Sol Medium's independent review is **Ready (0 C/I/M)**, and schema, hash, scope, anchor, and privacy checks passed. The package is ready for user review; its status remains `draft`. Explicit user approval of the labels is still required before freeze, model download/load, or retrieval metrics.

After the user approves the labels, continue with the gated freeze, model, and experiment steps:
Before running the freeze command, replace `USER_APPROVAL_DATE` with the actual date the user approves the labels, in `YYYY-MM-DD` format. Do not use a guessed or fixed date.

```bash
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli freeze --draft-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v1 --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local --approved-by user --approved-at USER_APPROVAL_DATE
uv sync --package kotaemon --extra local-eval
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli download-models --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local
env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -m kotaemon.indices.knowledge.evaluation.local_cli run --snapshot libs/kotaemon/tests/fixtures/knowledge_eval/local/snapshots/v1 --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local --embedding-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-m3 --reranker-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-reranker-v2-m3
```

## Plan Self-Review

- Spec coverage: source inventory, parser quality, stable IDs, source-level gold, anchors, three payload hashes, local model variants, one-factor K=5/M=20 runner, private review package, and user approval gate are all assigned to Tasks 1–7.
- Privacy: all local data products are ignored; CI relies on generated fixtures; model inputs remain local; no source-derived file is staged.
- TDD: every implementation task starts with a failing test and verifies that failure before implementation.
- Review workflow: each task is implemented by GPT-6 Luna Max and reviewed by GPT-6 Sol Medium before the next task starts.
