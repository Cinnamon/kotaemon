# Agent Retrieval K=5 Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven development to execute this plan task by task. The implementation uses TDD and receives a separate GPT-6 Sol Medium review.

**Goal:** Re-run the paired synthetic retrieval comparison at K=5 and report Hit@5, Recall@5, MRR@5, and Wrong-scope@5 against the same-K global baseline.

**Architecture:** Keep the existing five-query synthetic fixture, catalog, vector backend, and evaluation scorer. Set both service and request candidate limits to five in both arms; the only comparison variable remains `IdentityGlobalPlanner` versus `QueryPlanner`. Preserve the previous K=2 evaluation JSON and Zhang trace under K=2-specific filenames, then regenerate the canonical report and artifacts at K=5.

**Tech Stack:** Python 3, pytest, Kotaemon `KnowledgeService`/`VectorRetrieval`, JSON evaluation artifacts, Markdown report.

## Global Constraints

- Compare both arms with identical K, fixture, backend, filters, and other retrieval settings.
- Do not change production retrieval behavior or judgment labels for this evaluation update.
- Compute Wrong-scope over unique returned chunks in the raw top-five window, pooled only across the three queries with non-null disallowed-source labels; report the actual numerator and denominator.
- Describe all results as synthetic fixture measurements, not production performance.
- Attribute differences only to query-scope planning; the fixture uses vector-only retrieval, no rerankers, and disabled diversity.

---

### Task 1: Re-run and document the paired comparison at K=5

**Files:**
- Modify: `libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py`
- Modify: `docs/superpowers/reports/agent-knowledge-retrieval-evaluation.md`
- Preserve: current K=2 `docs/superpowers/reports/artifacts/agent-retrieval-evaluation.json` as `agent-retrieval-evaluation-k2.json`
- Preserve: current K=2 `docs/superpowers/reports/artifacts/agent-retrieval-zhang-trace.json` as `agent-retrieval-zhang-trace-k2.json`
- Regenerate: the canonical evaluation JSON and Zhang trace with K=5 observations
- Modify: `.superpowers/sdd/progress.md`
- Create: `.superpowers/sdd/task-13-report.md`
- Test: `libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py`

**Interfaces:**
- Consumes: the existing `compare_runs`, `KnowledgeService`, `QueryPlanner`, and fixed five-case fixture.
- Produces: equal baseline/planned K=5 configurations, observed candidate count five for each judged query, refreshed K=5 artifacts, and a report with per-query and aggregate deltas.

- [ ] **Step 1: Preserve K=2 artifacts and write the K=5 regression assertions.**

  Copy the existing two artifacts to their `-k2` filenames before regenerating canonical files. Update the integration test to require observed candidate counts of five in both arms and `candidate_k == 5` for every judged observation. Keep the five judged cases and the separate unjudged empty-allowlist parity check unchanged.

- [ ] **Step 2: Run the focused comparison test and verify RED.**

  Run: `uv run pytest libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py::test_synthetic_baseline_and_planned_retrieval_share_one_fixture_and_config -q`

  Expected: failure because the current harness still requests K=2.

- [ ] **Step 3: Set both service defaults and the paired request K to five.**

  Parameterize the fixture service helper so its `VectorRetrieval(top_k=...)` matches the paired request. Set `top_k = 5` once in `_run_synthetic_comparison`; continue deriving `candidate_k`, `compare_runs(k=...)`, shared configs, requests, and assertions from that value. Do not change planner, fixture, labels, query text, backend, or other retrieval settings.

- [ ] **Step 4: Run the focused test and verify GREEN.**

  Run: `uv run pytest libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py -q`

  Expected: all integration tests pass; each arm observes five candidate-K requests for the five judged queries, and the empty-allowlist check still makes zero vector calls.

- [ ] **Step 5: Regenerate artifacts and report observed K=5 results.**

  Run the evaluation integration test to regenerate canonical JSON and Zhang trace. Update the Markdown report with K=5 baseline/planned values, planned-minus-baseline deltas, per-query results, actual Wrong-scope numerator/denominator, and a separate historical K=2 table linking to the preserved artifacts. Explain that the isolated method change is deterministic query scope planning; note which routes remain global. Do not state an uplift for any metric unless the generated data shows it.

- [ ] **Step 6: Verify, record, and commit the task.**

  Run: `uv run pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py -q`

  Run Black, isort, flake8, and `git diff --check` on changed Python files. Record RED/GREEN commands, observed K=5 metrics, and review status in `task-13-report.md`; mark Task 13 complete in `progress.md`; commit the plan, test, artifacts, report, and progress record.
