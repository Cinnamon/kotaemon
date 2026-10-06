# Local mini-corpus Task 4 report

## Result

Added source-level K scoring helpers and evidence-anchor coverage. Candidate chunk rankings are projected to the first representative chunk for each distinct source before calling the existing `score_run`, so the same distinct-source window determines Hit@K, Recall@K, MRR@K, and Wrong-scope@K.

Anchor coverage requires exact source, source unit, and locator match; one chunk must contain the entire nonempty half-open evidence span. Coverage split across adjacent chunks does not count. With no anchors, `rate` is `None`.

## TDD and verification

RED:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_source_metrics.py -q
ImportError during collection: AnchorCoverage was not present in the evaluation package
```

GREEN:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_source_metrics.py -q
19 passed
```

Cross-task verification after export integration:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_snapshot.py libs/kotaemon/tests/test_knowledge_eval_source_metrics.py -q
85 passed in 2.59s
```

Black check and staged/unstaged diff checks passed. A focused check of the existing evaluator confirmed source-level MRR follows the supplied ordering, Wrong-scope counts the unique window and is pooled only for cases whose disallowed IDs are not `None`. The GPT-6 Sol Medium task review approved the diff with no findings.

## Scope and privacy

Tests use generated Documents, EvidenceAnchors, and DraftChunks only. No local sources, gold labels, retrieval service, model weights, or metric runs were accessed.

## Commit

`226d5f06` — `feat: score distinct source retrieval results`
