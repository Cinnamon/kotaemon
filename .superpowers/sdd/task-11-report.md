# Task 11 Handoff: Offline Retrieval Evaluation

**Status:** Implementation complete; awaiting GPT-6 Sol Medium review.

## TDD record

- Tests were authored first. Initial RED: `uv run pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py -q` → **14 failed in 3.09s**, all at the explicit missing-evaluator-package guard before reaching behavioral assertions. After implementation, the first behavioral run was **13 passed, 1 failed** because the candidate-count diagnostic wording differed; the assertion was tightened around behavior and the pure suite passed.
- The hand-worked arithmetic oracle covers K-window duplicates and rank, source-level deduplication, pooled wrong-scope denominator, unknown chunk-to-Source mapping, schema validation, and baseline/planned config equality. A separate check confirms null scope differs from an empty disallowed-source list.
- The paired runner requires the two JSON configs to match except for planner identity. With traces enabled, it also rejects missing or unequal observed `candidate_k` values.
- GPT-6 Sol Medium review identified one minor coverage gap: explicit `allowed_source_ids=[]` needed parity coverage for both baseline and planned services. The supplemental check uses the same indexed fixture and service instances, runs after the five judged queries, and records an unjudged result. Both services return no documents, make zero vector queries, and record `search_status=not_run`, `no_search_reason=empty_visibility`, and a `no_search` event with reason `empty_visibility`. The five-query metrics and judged counts remain unchanged.
- Focused TDD evidence for the parity artifact: initial RED failed on missing `authorization_parity` (**1 failed in 4.73s**, `KeyError`); after adding the runner and artifact record, GREEN passed (**1 passed in 5.62s**).

## Implementation

- Added `load_fixture`, `resolve_judgments`, `score_case`, `score_run`, and `compare_runs` in `libs/kotaemon/kotaemon/indices/knowledge/evaluation/retrieval_eval.py`.
- Added `IndexedCatalog` for immutable canonical Source/chunk validation. Scoring applies raw K before deduplication, computes macro Hit/Recall/MRR, and pools wrong-scope counts over unique returned chunks. Source-level results deduplicate Source IDs. Unknown returned chunks without a Source relation raise an error.
- Added a version 1 JSONL judgment fixture separate from synthetic indexed records. The scorer uses only resolved judgment IDs; the integration harness rejects relevance-label keys in indexed chunk metadata and shared configs.
- Added the paired ktem integration through `KnowledgeService` and existing Task 10 `RetrievalTrace`. It indexes the same corpus once, compares identity/global and `QueryPlanner` arms, records candidate counts and backend status, checks explicit empty authorization, builds context, and verifies a literal citation span in the original chunk.
- Production retrieval APIs/defaults and Kotaemon document schemas were not changed.

## Synthetic fixture evaluation

See [`agent-knowledge-retrieval-evaluation.md`](../../docs/superpowers/reports/agent-knowledge-retrieval-evaluation.md) for full per-query results, config, ordered trace narrative, citation evidence, and limitations. Machine-readable artifacts:

- [`agent-retrieval-evaluation.json`](../../docs/superpowers/reports/artifacts/agent-retrieval-evaluation.json)
- [`agent-retrieval-zhang-trace.json`](../../docs/superpowers/reports/artifacts/agent-retrieval-zhang-trace.json)

The five-query synthetic fixture evaluation at K=2 produced:

| Metric | Baseline | Planned |
| --- | ---: | ---: |
| Hit@2 | 1.0000 | 1.0000 |
| Macro Recall@2 | 0.7667 | 0.8667 |
| MRR@2 | 0.7000 | 0.8000 |
| Pooled Wrong-scope@2 | 0.3333 (2/6) | 0.1667 (1/6) |

All five cases returned two candidates in each arm. The fixture docstore reports
`supports_lexical_search=False`; configured retrieval is vector-only, and trace
lexical status is `not_used`. Zhang scopes to its Source; Li is constrained by
the fixture's explicit logical path/type/entity filter; Wang remains global
under the current planner and retains wrong-scope rate 0.5; ambiguous and legacy
queries also enter global retrieval. The Wang result is reported unchanged and
visible in the machine artifact.

## Final-tree verification

The affected suite, including both Task 11 tests and KnowledgeService, scoped
retrieval, context, trace, and integration tests, passed:

```text
$ uv run pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py -q
18 passed in 3.21s

$ uv run pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py libs/kotaemon/tests/test_knowledge_service.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py libs/kotaemon/tests/test_knowledge_context.py libs/kotaemon/tests/test_knowledge_trace.py libs/ktem/ktem_tests/test_knowledge_service_integration.py libs/ktem/ktem_tests/test_knowledge_trace_integration.py -q
111 passed in 7.38s
```

Static checks on the three Task 11 Python files:

```text
$ uv run black --check libs/kotaemon/kotaemon/indices/knowledge/evaluation/retrieval_eval.py libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py
All done! ✨ 🍰 ✨
3 files would be left unchanged.

$ uv run flake8 --max-line-length=88 --extend-ignore=E203 libs/kotaemon/kotaemon/indices/knowledge/evaluation/retrieval_eval.py libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py
exit 0; no diagnostics

$ uv run isort --check-only --profile black libs/kotaemon/kotaemon/indices/knowledge/evaluation/retrieval_eval.py libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py
exit 0; no diagnostics

$ git diff --check
exit 0; no diagnostics
```

An intervening standalone run of the two Task 11 modules stopped during ktem
test collection: the installed LlamaIndex initialization found cached
`punkt_tab`, could not find `punkt`, and its NLTK downloader index response
failed XML parsing (`unclosed token: line 33, column 4`). The final aggregate
run above subsequently passed with both Task 11 modules included. No runtime
dependency or NLTK cache changes were made. The exact command and collection
output are recorded in the full report.

Task 11 implementation commit SHA: `6361601f999baaf4bb6ff8b74a74a4a444714577`.
The Task 11 review-fix commit SHA is recorded in the parent handoff after commit.
