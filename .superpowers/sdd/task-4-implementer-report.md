# Task 4 — Public BGE adapters and scope-safe retrieval integration

## Result

Implemented Task 4 on base `4d0cd89abf765c5746161e27ebf8061f49894ae9`.

The BGE adapters are importable from `kotaemon.models.local_bge` without importing FlagEmbedding or loading weights at module import time. `score_pairs()` preserves input order and validates exact score count and finite values. Public reranker `run()` returns cloned documents with rerank score and model/truncation provenance while preserving raw retrieval scores. The evaluation-local module remains a compatibility facade; its legacy reranker preserves the previous document identity and module-level loader monkeypatch behavior.

The v3 retrieval branch is gated by the opt-in retrieval policy. It plans hard authorization from the original query before retrieval, sends the same authorized scope and bounded fallback scope to every query variant and route, filters candidates before fusion and again after reranking, and keeps the legacy lexical-first path when the policy is disabled. Route status, candidate depth, fusion order/scores, rerank provenance, errors, and fallback are recorded in trace data. Empty authorization returns before enrichment or backend calls; branch errors do not broaden scope.

## RED evidence

The required RED command was run against the baseline before implementing production changes:

```text
uv run --package ktem pytest libs/kotaemon/tests/test_public_bge.py libs/kotaemon/tests/test_knowledge_pipeline_v3.py -q
```

The new public adapter test initially failed because `kotaemon.models.local_bge` did not exist (`ModuleNotFoundError`). After fixing a test-fixture import, the baseline pipeline behavior run produced 7 failures: `KnowledgeService.search()` did not accept the new `enriched_query` keyword required by the tests. These failures identified missing public API and behavior. Two additional pipeline assertions (fallback-scope parity and trace provenance) were added during implementation; they are covered by the final GREEN run below, but were not separately rerun against baseline.

## GREEN and regressions

All commands below were freshly run after the final code changes:

| Command | Result |
|---|---:|
| Task 4 acceptance suite: `test_public_bge.py`, `test_knowledge_pipeline_v3.py`, `test_knowledge_scoped_retrieval.py`, `test_knowledge_eval_local_models.py`, `test_knowledge_retrieval_eval.py` | 90 passed |
| Legacy experiment/CLI compatibility: `test_knowledge_eval_local_experiment.py`, `test_knowledge_eval_local_cli.py` | 50 passed, 6 dependency deprecation warnings |
| `libs/ktem/ktem_tests/test_local_qa_core.py` | 13 passed |
| `libs/kotaemon/tests/test_knowledge_service.py` | 16 passed |

The local tests use fake model backends and require no model weights or network access. No real-model evaluation was run.

Formatting and whitespace checks are recorded after the report is written and before commit.

## Files

Task 4 implementation and behavior tests are limited to the named files in the brief:

- `libs/kotaemon/kotaemon/models/__init__.py`
- `libs/kotaemon/kotaemon/models/local_bge.py`
- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_models.py`
- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_experiment.py`
- `libs/kotaemon/kotaemon/indices/vectorindex.py`
- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/knowledge_service.py`
- `libs/kotaemon/tests/test_knowledge_pipeline_v3.py`
- `libs/kotaemon/tests/test_public_bge.py`

`.superpowers/sdd/progress.md` has pre-existing user/task progress edits and is intentionally excluded from this commit.
