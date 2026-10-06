# Task 7 Implementation Report — Scoped Hybrid Retrieval

## Commits

- Implementation: `6da79a438b5be8ffae9d418116c83f6359b668db` — `fix: enforce scoped retrieval boundaries`
- Review-fix implementation: `8b7da5a437788292f766cc055112be0efa457879` — `fix: close scoped retrieval filter and thumbnail gaps`
- Base: `2eb35779111f89fce7e27d02b8524032d4636fc3`

## Changes

- `libs/kotaemon/kotaemon/indices/vectorindex.py`
  - Made `scope`, `fallback_scope`, and optional dict `trace` explicit `VectorRetrieval.run` arguments while preserving the existing `scope` call pattern and result type.
  - Vector queries now pass chunk IDs as `ids`; lexical queries pass the same IDs as `doc_ids`. A legacy `doc_ids` argument is consumed as a scope and is never forwarded to a vector backend.
  - `scope=[]` returns before embedding or store access. `scope=None` searches globally unless a caller-visible `fallback_scope` is supplied, in which case retrieval is constrained to that allowlist.
  - Scoped calls fetch a bounded expanded candidate pool, then filter by chunk ID before reranking and again after every reranker. Planned scope is intersected with caller-visible IDs. A zero-hit planned scope retries once against the caller allowlist, or globally when no allowlist was supplied; an explicit empty allowlist remains hard-empty.
  - Explicit `MetadataFilters` and Chroma `where` constraints are post-filtered before reranking and after each reranker. The supported subset is AND/OR with EQ/IN. Unsupported or ambiguous operations fail with `ValueError` before embedding or store access. The same predicate remains active during fallback.
  - Thumbnail expansion only fetches linked IDs inside the active chunk scope. It rejects cross-source links when both chunks carry `file_id`; rejected links keep the original text result. Valid expansions remap through Kotaemon's `id_` field.
  - Lexical status and candidate count describe lexical documents remaining after scope and metadata post-filtering.
  - Corrected score-to-ID association when `doc_store.get` reorders documents and made hybrid merging deterministic and unique by `doc_id`.
  - Global lexical search runs only when the docstore declares or implements lexical query support. Empty and unavailable lexical branches are reported distinctly. Hybrid worker exceptions are recorded; usable results from the other branch are retained, and failures are surfaced when no branch returns usable results.
- `libs/kotaemon/kotaemon/storages/docstores/in_memory.py` declares its lexical search unavailable.
- `libs/ktem/ktem/index/file/pipelines.py` forwards an optional trace, retains the selected-file early return, and constrains extra-table retrieval to the selected chunk IDs.
- Added `libs/kotaemon/tests/test_knowledge_scoped_retrieval.py` and `libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py`.

## TDD evidence

### RED

Before production changes, ran:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_scoped_retrieval.py libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py -q
```

Result: **14 failed, 3 passed**. Failures exposed the old vector `doc_ids` argument, empty-scope store work, absent global lexical retrieval, scope leaks, score/ID misalignment, missing dedup/fallback/trace handling, and swallowed worker errors. The adapter boundary and no-selected-files UI behavior already passed.

### GREEN

Final focused regression command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_scoped_retrieval.py libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py libs/kotaemon/tests/test_indexing_retrieval.py libs/kotaemon/tests/test_knowledge_planner.py libs/ktem/ktem_tests/test_knowledge_catalog.py -q
```

Result after review fixes: **57 passed**, with 4 existing Pydantic deprecation warnings from `kotaemon/embeddings/openai.py`.

Formatting and checks passed:

```text
uv run black --check libs/kotaemon/kotaemon/indices/vectorindex.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py
uv run isort --profile black --check-only libs/kotaemon/kotaemon/indices/vectorindex.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py
uv run flake8 --ignore=E501,E203,W503 libs/kotaemon/kotaemon/indices/vectorindex.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py
git diff --check
```

All four checks passed after the review fixes.

### Review-fix RED evidence

- Initial reviewer regressions: **12 failed, 20 passed**. Failures covered retry without an allowlist, metadata post-filtering and fail-closed parsing, post-filtered lexical status, and thumbnail scope/source boundaries.
- Added fallback-with-metadata-filter regression: **1 failed** against the original implementation; it now verifies that the explicit filter remains active in the global retry.
- Added MetadataFilters AND/OR and valid same-source thumbnail compatibility checks: **3 failed** against the original implementation. The thumbnail case also exposed that the existing code wrote `_id`, while Kotaemon's `Document.to_dict()` uses `id_`; the expansion now preserves the text chunk ID.

## Limits

- Lexical availability is explicit for the in-memory store. Other legacy stores with an overridden `query` method are attempted unless they set `supports_lexical_search = False`; empty output is recorded as `empty`, not treated as evidence of BM25 coverage.
- A missing caller allowlist permits the specified one-time global retry after a zero-hit planned scope. When a caller allowlist exists, both the retry and thumbnail expansion stay inside it; `fallback_scope=[]` never broadens.
- The trace is intentionally a small optional dict hook for scope, candidate count, lexical status, and branch errors. Task 10 remains responsible for the full structured trace collector.
- No `Document`/`RetrievedDocument` schema change, database migration, new retrieval stack, or production recall claim was added.
