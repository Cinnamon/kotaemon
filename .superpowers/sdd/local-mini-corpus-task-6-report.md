# Local mini-corpus Task 6 report

## Result

Implemented `run_local_experiment` with four isolated arms: `baseline`, `chunking`, `embedding`, and `reranker`. The runner rebuilds from the immutable reviewed snapshot, uses source-level K=5 metrics and a vector candidate window of 20, preserves the same reviewed query/filter sequence across arms, and reports ordered candidate, reranker-input, and final IDs with per-arm configuration fingerprints and signed baseline deltas.

The report and manifest include actual per-query candidate counts, source metrics and wrong-scope numerators/denominators, evidence-anchor coverage, model/runtime metadata, and artifact hashes. Anchor coverage examines all retrieved chunks associated with each query's first five distinct sources. It uses exact offsets when a chunk maps uniquely to normalized source text; ambiguous offsets are recorded as unresolved and excluded from the covered/uncovered denominator.

The runner rejects path or metadata constraints when the reviewed snapshot has no approved logical metadata mapping, uses neutral logical virtual paths, and validates the recorded baseline splitter configuration (`main-token-only-v1`, 1024/256, `\n\n`). Its global identity planner preserves explicit caller constraints and does not infer source scope. Traces, report, and manifest are staged in a temporary sibling directory and published atomically only after the run succeeds.

## TDD and review

- **RED:** Synthetic tests first exposed the absent runner and missing handling for required model revision/acquisition fields, empty vector/no-search traces, all-chunk anchor coverage, and atomic artifact publication. A later integration test reproduced rejection of VectorIndex's optional reranker call with an empty candidate list.
- **GREEN:** The focused runner module passes all 17 tests. Coverage includes four-arm isolation and ordered candidate identity, provenance forwarding and fail-closed validation, zero-result scoring with and without an empty reranker call, later-chunk anchor matches, unresolved repeated-text offsets, and cleanup after a staged-run failure.
- GPT-6 Sol Medium approved Task 6 after the four review fixes: require nonempty model revisions and a `cached`/`downloaded` source label, then forward the supplied values into adapters; accept valid zero-candidate and explicit no-search results without requiring reranker work for empty windows; check all chunks in the first-five-source anchor window while reporting ambiguous offsets as unresolved; and atomically publish complete artifacts. Task 7 will verify the supplied model claims against its local manifest and rehash the weights.

## Verification

- Focused runner module: **17 passed**.
- Combined six-module evaluation suite: **135 passed, 6 warnings**.
- Ruff, Black check, and `git diff --check`: passed.

## Scope and Task 7 dependency

All runner tests use generated synthetic snapshots and fake model factories. No model weights were downloaded or loaded; no corpus data or derived corpus artifacts were accessed; no real-corpus metrics were run.

Task 7's CLI must record each model's resolved revision and whether its weights were cached or downloaded in the local manifest, verify those claims against the manifest, and rehash the weights. It must then populate `LocalModelPaths` with `embedding_revision`, `embedding_weight_source`, `reranker_revision`, and `reranker_weight_source`. The runner fails closed before model construction or artifact creation if any value is missing or invalid.

## Commit

Implementation and review fixes: `1a7b9d5a`.
