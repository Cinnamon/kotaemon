# Task 13 Handoff: K=5 Offline Retrieval Evaluation

**Status:** Complete; GPT-6 Sol Medium review passed with no blocking findings.

## TDD record

- Archived the then-current K=2 machine report and Zhang trace before running the updated harness. The preserved files are [`agent-retrieval-evaluation-k2.json`](../../docs/superpowers/reports/artifacts/agent-retrieval-evaluation-k2.json) (SHA-256 `e5fe4e012085e4545d604a46fea3fc350234cc52abec3836ee78040bdcf4cd58`) and [`agent-retrieval-zhang-trace-k2.json`](../../docs/superpowers/reports/artifacts/agent-retrieval-zhang-trace-k2.json) (SHA-256 `3b3f70431998c5de73da4f0141fda23fe336d5adb52ad05b746a63bfc330fc6b`).
- Wrote the integration assertions for five judged observations per arm, five observed candidate-K requests, `candidate_k=5` in every observation and trace, and `top_k`/`candidate_k=5` in both configs. RED command: `uv run pytest libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py::test_synthetic_baseline_and_planned_retrieval_share_one_fixture_and_config -q` → **1 failed in 5.43s**. The expected failure showed both arms still observed `[2, 2, 2, 2, 2]` instead of five requests of size 5.
- Set the service's `VectorRetrieval(top_k=...)`, the paired search request, shared config, and `compare_runs(k=...)` from one `top_k=5` value. The next integration run confirmed the new K=5 candidate assertions and reached a stale K=2 Wang wrong-scope expectation (`0.5` versus the observed K=5 `0.4`); the assertion was updated from the generated fixture result, without changing labels or corpus data.
- GREEN command: `uv run pytest libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py -q` → **3 passed in 6.49s**. Final combined verification after the semantic-query and observation-count assertions: `uv run pytest libs/kotaemon/tests/test_knowledge_retrieval_eval.py libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py -q` → **21 passed in 5.04s**.

## K=5 results

The generated canonical artifact and report use the same two-arm K=5 comparison. Each arm has five judged queries and five vector requests with candidate K=5. The raw unique result counts may be less than five when explicit or planned scope contains fewer chunks.

| Metric | Identity/global baseline | Planned | Planned − baseline |
| --- | ---: | ---: | ---: |
| Hit@5 | 1.0000 | 1.0000 | 0.0000 |
| Macro Recall@5 | 0.9333 | 0.9333 | 0.0000 |
| MRR@5 | 0.7000 | 0.8000 | +0.1000 |
| Wrong-scope@5 | 0.3077 (4/13) | 0.1818 (2/11) | −0.1259 |

Wrong-scope pools actual unique returned chunks over the three labeled queries. Baseline contributions: Zhang `2/5`, Li `0/3`, Wang `2/5`, totaling `4/13`. Planned contributions: Zhang `0/3`, Li `0/3`, Wang `2/5`, totaling `2/11`. The two queries with null scope labels do not enter the pool.

The only comparison change was `IdentityGlobalPlanner` versus `QueryPlanner`; semantic query text, fixture records, judgments, filters, vector-only backend, first-round multiplier, context setting, no-reranker setting, and disabled diversity were held fixed. Zhang narrows from global to its three-chunk `source-zhang` scope while preserving the original semantic query. Li is constrained by the explicit path/type/metadata filter in both arms. Wang, ambiguous-team, and legacy-source remain global. Hit@5 and Recall@5 did not improve; MRR@5 rose, and Wrong-scope@5 fell. These are synthetic fixture measurements, not production performance claims.

## Files, scope, and checks

- Updated the ktem evaluation harness and K=5 canonical report/trace JSON.
- Preserved K=2 JSON and trace under versioned `-k2.json` filenames and linked them from the report.
- Updated [`agent-knowledge-retrieval-evaluation.md`](../../docs/superpowers/reports/agent-knowledge-retrieval-evaluation.md) with the observed K=5 main table, per-query top-five IDs and scores, pooled denominators, K=2 history, route attribution, vector-only limitations, and trace summary.
- No production retrieval or scorer logic changed. The synthetic records, judgment labels, query text, backend, and planner implementation were not edited.
- `uv run black --check libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py` → clean.
- `uv run isort --check-only --profile black libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py` → exit 0, no diagnostics.
- `uv run flake8 --max-line-length=88 --extend-ignore=E203 libs/ktem/ktem_tests/test_knowledge_retrieval_eval_integration.py` → exit 0, no diagnostics.
- `git diff --check` → exit 0, no diagnostics.
- No push or PR operation was performed.
- GPT-6 Sol Medium independently rechecked config parity, K=5 metric arithmetic, pooled Wrong-scope denominators, artifact consistency, and K=2 archive hashes; no blocker remains.
