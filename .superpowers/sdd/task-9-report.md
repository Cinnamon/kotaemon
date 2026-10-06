# Task 9 — Diversity and whole-unit context budget

## TDD record

### RED

- The first run of the two new test files reported **16 failed**. The failures showed duplicate content occupying `top_k`, missing diversity and token-counter configuration, context truncation, absent metadata escaping/path/section fields, use of unrelated `window` content, wrong chatbot mode, and citation/context mismatch. Two test-fixture issues were corrected: a `BaseReranking` test double needed a private attribute, and the HTML-unit assertion needed to check complete opening/closing markers rather than count `<br>` against `<b>` tags.
- After the first GREEN, a new test exposed an actual grouping gap: chunks in the same section had distinct `parent_id` values, so the section cap did not apply. That test failed before the grouping fix and passed after counting both source+parent and source+section keys.
- GPT-6 Sol Medium review follow-up added three cases with source identity missing from the text chunk, the thumbnail, or both. All three failed before the fix because the image could replace citation-ready text; they pass after requiring both source IDs and equality.
- Tests also cover cap refill and stable reranker rank, short text and missing metadata, scoped/filter-safe thumbnail conversion order and bounds, later-small-unit inclusion after an oversized item, exact token boundary, full escaped header, source-substring `window`/`table_origin`, table/image/chatbot modes, skipped-image references, citation quote lookup, custom `trim_func` configuration, and optional trace fields.

### GREEN

Final new-test command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_diversity.py libs/kotaemon/tests/test_knowledge_context.py -q
23 passed
```

Related integration/regression command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_diversity.py libs/kotaemon/tests/test_knowledge_context.py libs/kotaemon/tests/test_knowledge_scoped_retrieval.py -q
59 passed in 10.77s (normal exit 0)
```

`libs/ktem/ktem_tests/test_qa.py` could not collect because its bare top-level `index` import was not resolvable from the test's collection path. The direct citation regression in the new context tests invokes `AnswerWithContextPipeline.match_evidence_with_context` and passes.

Formatting and static checks passed:

- `uv run black --check ...` — 5 files unchanged.
- `uv run isort --check-only --profile black ...` — passed.
- `uv run flake8 --max-line-length=88 --extend-ignore=E203,W503 ...` — passed.
- `git diff --check` — passed.

## Implementation

- Added deterministic diversity selection after configured rerankers and before the final result limit. It removes repeated IDs and NFKC/case/whitespace-normalized exact text, suppresses 5-gram Jaccard overlap of at least 0.85 within shared source-aware groups, and applies a default cap of two to each source+parent and source+section group. Candidates over the cap are deferred and refill short results in original rank order. Missing group metadata does not reject a result. Existing rerankers, including MMR, still run once with their existing order and cost bounds.
- Preserved linked-thumbnail rank by mapping docstore results back to the selected association order. Scope checks happen before fetching linked thumbnails; both source identities must be present and equal, and metadata filters are rechecked before replacing text. If identity cannot be confirmed, the citation-ready text remains. The returned list is bounded by `top_k`.
- Rebuilt context from complete formatted units. The pipeline counts the full accumulated context plus each candidate with the configured counter, includes a unit only at or below budget, skips oversized units, and checks later smaller units. It keeps the existing tuple output, five-table cap, image reference behavior, and distinct table/image/chatbot modes.
- Escaped file name, logical path, section, and page metadata. `window` and `table_origin` replace source text only when they are literal substrings of that chunk; body newlines and source text remain intact. Image alt text is escaped. Optional retrieval/context trace dictionaries receive selected IDs and accepted token count; trace-update errors are contained.
- Retained `trim_func` configuration compatibility without using it to split evidence: a readable `chunk_size` supplies the budget and a callable tokenizer is reused when available. Explicit `token_counter` takes precedence; otherwise the current GPT-3.5 tiktoken encoder is used.

## Files changed

- `libs/kotaemon/kotaemon/indices/knowledge/retrieval/diversity.py`
- `libs/kotaemon/kotaemon/indices/vectorindex.py`
- `libs/kotaemon/kotaemon/indices/qa/format_context.py`
- `libs/kotaemon/tests/test_knowledge_diversity.py`
- `libs/kotaemon/tests/test_knowledge_context.py`

## Limits

- Coverage uses deterministic synthetic documents and test counters. It validates ordering, scoping, citation lookup, and complete-unit budgeting, not production recall or answer quality.
- The pre-existing `test_qa.py` import issue remains outside this task; the direct citation lookup regression passed.
