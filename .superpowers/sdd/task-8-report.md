# Task 8 — Agent KnowledgeService and QA bridge

## TDD record

### RED

- `uv run pytest libs/kotaemon/tests/test_knowledge_service.py -q` failed during collection with the expected `ModuleNotFoundError` for the not-yet-created `kotaemon.indices.knowledge.retrieval` package.
- `uv run pytest libs/ktem/ktem_tests/test_knowledge_service_integration.py -q` reported **2 failed, 1 passed**. One failure showed that `DocumentRetrievalPipeline` did not expose the file index's `private` setting. The other showed that selected-file retrieval still queried `Index` directly instead of going through the KnowledgeService adapter.
- During GPT-6 Sol Medium review, `uv run pytest libs/kotaemon/tests/test_knowledge_service.py::test_search_filters_retriever_results_to_mandatory_authorized_chunks -q` failed because an injected retriever's `other-chunk` result escaped the service boundary.
- The new assertions cover empty versus global visibility, selected-source intersection against planner output, mandatory path/type/entity filters, path segment boundaries, low-confidence fallback, SQL document relationships, forged chunk metadata, docstore result reordering, safe list output, private visibility, QA group IDs, citations, and extra-table scope.

### GREEN

Final focused command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_service.py libs/kotaemon/tests/test_knowledge_planner.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py libs/ktem/ktem_tests/test_knowledge_service_integration.py libs/ktem/ktem_tests/test_knowledge_catalog.py libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py libs/ktem/ktem_tests/test_knowledge_indexing.py -q
85 passed in 9.17s
```

Formatting and lint checks passed:

- `uv run black --check ...` — 11 files unchanged.
- `uv run isort --check-only --profile black ...` — passed.
- `uv run flake8 --max-line-length=88 --extend-ignore=E203,W503 ...` — passed.

The review correction filters every returned `doc_id` against the mandatory SQL-authorized chunk set. The targeted RED above became GREEN, and `test_search_keeps_mandatory_chunks_returned_by_approved_fallback` verifies that authorized fallback chunks remain eligible while an out-of-scope result is removed.

## Implementation

- Added SQLAlchemy-free `KnowledgeService.search/read/list` plus safe `chunk_ids_for_sources` for the existing file QA adapter.
- Search first enumerates catalog-visible sources, intersects explicit logical path (segment-aware), source type, and scalar entity filters, then intersects planner scope again. Planner chunks use `Index.relation_type='document'`; fallback chunks retain every mandatory caller constraint. Every returned chunk is post-filtered against that mandatory chunk set, including after a retriever fallback. An empty allowlist exits before planner, retriever, or docstore access.
- `read` authorizes only through SQL document relationships and current catalog visibility before reading by ID from the docstore. It does not trust `Document.metadata.file_id` and maps re-ordered docstore output by ID.
- `list` emits stable immediate directory/source children, uses a safe filename fallback for legacy sources, and does not read or return `Source.path`.
- Added separate ktem factories for file QA and explicit Agent/global access. The Agent factory's global view remains bounded by the catalog's private/user policy.
- Routed selected-file QA through the service, retained empty-selection `[]`, flattened group IDs, preserved returned citation documents, and kept extra-table lookup inside authorized selected chunk IDs, including a post-filter for a backend that ignores its scope.
- Passed `private` into configured file retrievers so their service catalog applies the same user boundary as indexing.
- Extended the SQL catalog with chunk-to-source lookup constrained to document relationships.

## Files changed

- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/__init__.py`
- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/knowledge_service.py`
- `libs/kotaemon/tests/test_knowledge_service.py`
- `libs/ktem/ktem/index/file/base.py`
- `libs/ktem/ktem/index/file/index.py`
- `libs/ktem/ktem/index/file/knowledge_catalog.py`
- `libs/ktem/ktem/index/file/knowledge_service.py`
- `libs/ktem/ktem/index/file/pipelines.py`
- `libs/ktem/ktem_tests/test_knowledge_catalog.py`
- `libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py`
- `libs/ktem/ktem_tests/test_knowledge_service_integration.py`

## Limits

- The Agent factory is available for an Agent caller to use; this task does not add a new Agent runtime/tool registration layer.
- Synthetic and in-memory coverage validates scope mechanics, not production retrieval quality. Evaluation remains Task 11.
