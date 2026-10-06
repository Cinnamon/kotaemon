# Task 10 implementation report

## Scope

Implemented request-local structured tracing across `KnowledgeService`,
`VectorRetrieval`, `PrepareEvidencePipeline`, the file retrieval pipeline, and
normal/decomposed Simple QA. Public retrieval and QA return shapes remain
unchanged. The caller passes a `RetrievalTrace`; no collector is stored on a
component or shared between requests. Existing dict trace hooks remain
supported.

The collector exports detached JSON-safe snapshots with schema version 1,
ordered events, a lock for concurrent recall workers, and conservative default
redaction. Source text, evidence HTML, image payloads, raw metadata, exception
messages, and physical paths are omitted by default. `include_content=True` is
the explicit opt-in for content fields.

Trace events now record original query and plan separately; explicit filters;
visible, mandatory, and planned source/chunk scopes; each bounded recall
attempt; lexical/vector status, candidate IDs and available scores; fallback
reason; merged order; reranker output; diversity exclusions; final chunk IDs;
and context IDs and token use. `DocumentRetrievalPipeline` records final UI IDs
after extra-table retrieval. Simple QA tags main and subquestion retrieval and
context events, and only injects the optional trace into retrievers when one was
supplied.

Compatibility follow-up: rerankers may return plain `Document` instances
without a score. Trace score extraction now records these scores as unavailable
instead of raising, and candidate serialization is skipped when tracing is
disabled.

Modified implementation and test files:

- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/__init__.py`
- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/diversity.py`
- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/knowledge_service.py`
- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/trace.py`
- `libs/kotaemon/kotaemon/indices/qa/format_context.py`
- `libs/kotaemon/kotaemon/indices/vectorindex.py`
- `libs/kotaemon/tests/test_knowledge_trace.py`
- `libs/ktem/ktem/index/file/pipelines.py`
- `libs/ktem/ktem/reasoning/simple.py`
- `libs/ktem/ktem_tests/test_knowledge_trace_integration.py`

## TDD evidence

- The initial trace integration run had 17 passing tests and two fixture errors:
  the fake answer pipeline was a plain object and TheFlow wrapped it in a
  `ProxyFunction`, which required an execution context not started by the
  generator fixture. Making the fake a `BaseComponent` matched production
  component behavior; the focused trace modules then passed 19/19 in 6.47s.
- Added a test that decomposed QA context events carry the same subquestion and
  main-query labels as retrieval events. RED: 1 failed in 6.45s because all
  context labels were `(None, None)`. GREEN: after passing scoped traces to each
  evidence call, 1 passed in 6.05s.
- The first affected-suite run found a compatibility regression in reranker
  score extraction: 115 passed and 3 failed in 6.53s. All failures were existing
  scoped-retrieval tests where rerankers returned plain `Document` objects.
- Added a scoreless-reranker trace test. RED: 1 failed in 2.69s with
  `AttributeError: 'Document' object has no attribute 'score'`. GREEN: after
  treating absent scores as unavailable and bypassing trace-only candidate
  extraction with no collector, 1 passed in 3.20s. The three previously failing
  tests plus the new regression then passed 4/4 in 2.67s.
- Added a deterministic full-chain integration test using actual
  `KnowledgeService`, `VectorRetrieval`, `PrepareEvidencePipeline`, and
  `AnswerWithContextPipeline.match_evidence_with_context`. Its JSON snapshot
  round-trips and preserves this order:
  `request → plan → recall_attempt → merged → reranker → diversity → final → context`.
  It checks authorized scopes, both available recall branches, vector scores
  (`chunk-a: 0.88`, `chunk-b: 0.72`), null lexical scores, merged and reranked
  order, the `group_cap` exclusion, final/context ID `chunk-a`, and context token
  use. Citation span offsets are verified against the original returned
  `RetrievedDocument.text`. The test passed in 6.06s.
- The throwing-sink integration test now drains the full QA stream. Retrieval,
  evidence construction, and answer streaming complete, and the answer is
  returned.
- Additional checks prove default serialization omits generated answers, raw
  metadata, image data, exception messages, and unsupported objects while
  normalizing NaN to `null`. A deferred group-cap document selected to fill
  `top_k` is recorded as selected, not excluded; these two tests passed 2/2 in
  4.65s.
- The full service-to-context/citation chain, JSON-safe serialization and
  redaction, concurrent event histories, backend status/error reporting,
  diversity exclusions, zero-hit fallback-attempt retention, normal and
  decomposed stream handoffs, and the original extra-table final-ID test were
  first recorded as passing after implementation was present. The handoff has
  no captured pre-implementation RED for those groups, so this report does not
  claim one.
- Review follow-up: added a selected-scope extra-table regression using the
  actual `VectorRetrieval` class. The direct RED run was:

  ```text
  uv run pytest libs/ktem/ktem_tests/test_knowledge_trace_integration.py -k foreign_candidates_after_zero_scope_hits -q
  1 failed, 11 deselected in 6.58s
  ```

  The failing assertion was `assert "foreign-table" not in ["foreign-table"]`:
  the trace contained that candidate after the scoped query retried globally,
  although the file pipeline later filtered it from UI results. Passing
  `fallback_scope=chunk_ids` keeps the zero-hit attempt
  within the selected chunk allowlist. The GREEN version passes and confirms
  only the selected scope reaches the vector backend and final UI trace.
- Review follow-up: custom sinks whose `scoped()` method raises now fall back
  to the original sink through `trace_scoped`. The first focused RED run was:

  ```text
  uv run pytest libs/ktem/ktem_tests/test_knowledge_trace_integration.py -k 'foreign_candidates_after_zero_scope_hits or broken_scoped_trace' -q
  3 failed, 9 deselected in 7.24s
  ```

  The normal QA stream raised
  `RuntimeError: trace scope unavailable`, and extra-table retrieval silently
  stopped. The fallback-candidate test's more specific RED above confirmed the
  leaked foreign ID. After adding the helper at all Simple QA retrieval and
  evidence handoffs and at extra-table retrieval, the same selection passed
  3/3 in 6.39s.

## Verification

Final affected suite, after formatting and import cleanup (including the two
additional acceptance checks):

```text
uv run pytest \
  libs/kotaemon/tests/test_knowledge_planner.py \
  libs/ktem/ktem_tests/test_knowledge_catalog.py \
  libs/kotaemon/tests/test_knowledge_service.py \
  libs/ktem/ktem_tests/test_knowledge_service_integration.py \
  libs/kotaemon/tests/test_knowledge_scoped_retrieval.py \
  libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py \
  libs/kotaemon/tests/test_knowledge_diversity.py \
  libs/kotaemon/tests/test_knowledge_context.py \
  libs/kotaemon/tests/test_knowledge_trace.py \
  libs/ktem/ktem_tests/test_knowledge_trace_integration.py -q

123 passed in 5.79s
```

Static checks on all touched Python files:

```text
TASK10_PYTHON_FILES=(
  libs/kotaemon/kotaemon/indices/knowledge/retrieval/__init__.py
  libs/kotaemon/kotaemon/indices/knowledge/retrieval/diversity.py
  libs/kotaemon/kotaemon/indices/knowledge/retrieval/knowledge_service.py
  libs/kotaemon/kotaemon/indices/knowledge/retrieval/trace.py
  libs/kotaemon/kotaemon/indices/qa/format_context.py
  libs/kotaemon/kotaemon/indices/vectorindex.py
  libs/kotaemon/tests/test_knowledge_trace.py
  libs/ktem/ktem/index/file/pipelines.py
  libs/ktem/ktem/reasoning/simple.py
  libs/ktem/ktem_tests/test_knowledge_trace_integration.py
)
uv run black --check "${TASK10_PYTHON_FILES[@]}"                         PASS
uv run isort --profile black --check-only "${TASK10_PYTHON_FILES[@]}"  PASS
uv run flake8 --max-line-length=88 --extend-ignore=E203,W503 \
  "${TASK10_PYTHON_FILES[@]}"                                            PASS
git diff --check                                                       PASS
```

The unfiltered flake8 defaults report the repository's existing line-length
and Black-compatible whitespace conventions; the Task 7–9 project check above
passes without suppressing other lint categories.

## Limits

The full-chain proof uses deterministic synthetic stores and a fake planner; it
verifies trace mechanics and citation-span mapping, not production recall
quality or a live backend's availability. Full source content remains absent
from default snapshots. Task 11 evaluation was not started.
