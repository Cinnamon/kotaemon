# Local mini-corpus Task 7 report

## Result

Implemented the local review-package CLI with `inventory`, `prepare-review`, `freeze`, `download-models`, and `run`. Writes are confined to the selected local root's `draft/`, `snapshots/`, `models/`, or `runs/` directories, including after resolving symlinks. The default `v1` draft selector deterministically proposes 20–24 usable unique documents using file-format coverage and content-derived topic candidates; it does not infer logical metadata from source directory names and leaves questions, judgments, and anchors empty for human review. `--all-sources` is limited to non-v1 drafts.

`freeze` requires an approver and date and writes an approval sidecar bound to the exact snapshot manifest bytes. `run` verifies that sidecar before accepting the snapshot. `download-models` checks the Hugging Face cache offline first, resolves an immutable full commit SHA before any download, downloads by that SHA, and atomically publishes the exact two-role model manifest with relative model paths, sorted weight hashes, a sorted complete regular-asset hash map, and `cached`/`downloaded` provenance. It excludes only Hugging Face download bookkeeping beneath `.cache/huggingface/`. `run` requires exactly one unambiguous manifest, validates role and model identities, full revisions, source labels and safe paths, rejects symlinked assets, rehashes the exact file set and all hashes, and forwards the four verified revision/source fields to the model factories. Each completed run bundle includes the exact verified manifest bytes and binds its SHA-256 and byte size in `artifact-manifest.json`; the bundle is published atomically.

Before model construction or run artifact creation, `run` calls the existing offline inference preflight and converts offline-state or optional-dependency failures into actionable CLI errors. The README and plan include a fresh-process invocation with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. In-checkout local roots must pass `git check-ignore` before any writes; external temporary roots remain supported. Default v1 reviews label omitted topic candidates as 24-source-cap omissions; explicit `--sample-id` reviews instead label candidates as not selected for that v1 sample. Explicit v1 IDs are checked against the full parse: at least 20 unique selected IDs must have usable chunks, and the selection must cover every format with usable documents in the full corpus. Rejections list unusable selected source paths and extraction diagnostics. `REVIEW.md` lists only the usable formats actually selected. The failed-source behavior remains in the existing Task 3 schema: source status and quality details are preserved, and `REVIEW.md` lists the failed path and diagnostic.

## TDD and verification

- **RED:** The initial synthetic CLI test module failed during collection because `local_cli` did not exist. Incremental RED cases also demonstrated failures for the default sample size, missing approval sidecar, redirected category symlink, `--all-sources` with `v1`, external symlinked model assets, and invalid approval-manifest binding.
- **Review-fix RED/GREEN:** Synthetic tests first failed for Git-ignore enforcement, omitted topic coverage, schema-v2 assets, offline preflight, and atomic run-manifest publication. The implementation passes those cases. A generated v1 source set with a simulated reader failure and byte-identical alias also confirms the failed source remains `status=failed`, the duplicate remains `duplicate_bytes`, and `REVIEW.md` reports the failed path and error type without changing Task 3's exclusion schema.
- **Explicit-sample RED/GREEN:** Synthetic tests failed when a 20-ID explicit v1 sample produced only 18 chunk-backed documents after one reader error and one empty result, and when the sample omitted a usable PDF format. The CLI now rejects both before publishing, with selected extraction diagnostics in the error; successful review text names only the formats actually selected.
- **Omission-reason RED/GREEN:** A generated explicit sample of 20 from 22 usable Markdown docs first failed because the two outside topic candidates were labeled as 24-source-cap omissions. Explicit-sample candidates now say `not selected for this v1 sample`; the automatic selector continues to label cap omissions clearly.
- **Focused GREEN:** `uv run --package kotaemon pytest libs/kotaemon/tests/test_knowledge_eval_local_cli.py -q --tb=short` — **32 passed**.
- **Combined synthetic suite:** the six local-evaluation modules plus `test_knowledge_eval_source_metrics.py` — **167 passed, 6 warnings**.
- **Style and diff:** Ruff and Black passed; `git diff --check` passed.
- `python -m kotaemon.indices.knowledge.evaluation.local_cli --help` previously exited successfully and listed the five commands.
- **Real-source candidate validation:** the ignored v1 draft contains **22 documents/paths, 306 source units, 473 chunks, 26 queries, 36 relevant query/source pairs, and 44 anchors**. Schema, payload/evidence hashes, scope complements, anchor coverage, and privacy checks passed; `load_local_snapshot(require_reviewed=False)` accepted the draft.

## Scope and review gate

The CLI implementation tests use generated synthetic fixtures. Separately, the real-source candidate package remains in the Git-ignored `local/draft/v1` tree with `review_status="draft"`; it has not been committed or frozen. GPT-6 Sol Medium's independent package review is **Ready (0 C/I/M)**. The candidate is ready for user review in this turn. Explicit user approval of the final labels remains a prerequisite for freezing gold, downloading or loading models, and running retrieval metrics. None of those gated actions has occurred.

## Files

- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_cli.py`
- `libs/kotaemon/tests/test_knowledge_eval_local_cli.py`
- `libs/kotaemon/tests/fixtures/knowledge_eval/README.md`
- `docs/superpowers/plans/2026-10-03-mini-corpus-golden-experiment.md`
- `.superpowers/sdd/progress.md`
