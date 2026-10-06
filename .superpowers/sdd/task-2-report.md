# Task 2 implementation report

Status: DONE

Implementation commit: `cc0dd0ef` — `feat: add markdown and faq chunk strategies`

## Changed files

- `libs/kotaemon/kotaemon/indices/knowledge/chunking/__init__.py`: exported strategy protocol, registry APIs and token fallback.
- `chunking/base.py`: strategy protocol and semantic-unit metadata/identity helper.
- `chunking/token.py`: delegates to the supplied existing BaseSplitter, preserves metadata and canonical IDs.
- `chunking/registry.py`: extensible factories; Wiki/Markdown share heading strategy; FAQ registered; unknown types use token fallback.
- `chunking/markdown.py`: ATX heading stack, preamble preservation, fenced-code awareness and malformed-fence fallback.
- `chunking/faq.py`: explicit metadata or marker-pair parsing, multiline answers, whole-document fallback for incomplete records.
- `libs/kotaemon/tests/test_knowledge_chunking.py`: eight plan cases plus preamble/fenced-code preservation, oversized FAQ parent IDs and source metadata, partial-record fallback, and registry extension coverage.

## RED/GREEN evidence

Before implementation, `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py -q` failed collection with `ModuleNotFoundError: No module named 'kotaemon.indices.knowledge.chunking'`. The test file was written first, including the additional behavioral cases, and the same expected RED was observed again.

After implementation: **12 passed**. After Black formatting: **12 passed in 3.39s**. `git diff --check` and `git diff --cached --check` passed.

## Self-review

- Changes are confined to Task 2; no Document schema, vector ingestion or app pipeline changes.
- Loader-specific metadata and original source document ID survive semantic subdivision. Each split result gets its own canonical chunk ID; pieces of a natural unit share its semantic parent ID and heading/question path.
- Wiki metadata keeps source_type=wiki.
- The caller's configured splitter controls token subdivision. Metadata is temporarily excluded from token accounting so small budgets such as the plan's eight-token case do not reject canonical metadata; its original exclusion lists are restored on output.
- Malformed/incomplete FAQ input uses whole-input fallback instead of emitting a partial set of records.
- No dependencies or filesystem access through virtual_path were added.

## Concerns

No blocking concerns. Markdown structure support here covers ATX headings, as represented by the approved task fixtures; heading-less or unterminated-fence text uses the existing splitter. Semantic units pass through that splitter even when short, retaining the caller's configured splitting behavior.

## Independent-review fix

Review identified an Important metadata exclusion regression: constructing semantic units dropped the source's `excluded_embed_metadata_keys` and `excluded_llm_metadata_keys`, so result chunks exposed metadata loaders had deliberately excluded.

Fix commit: `355cecf1be6d3e41d2ebc33ba1ff4df931b62c18` — `fix: preserve metadata exclusions in semantic chunks`.

Added parametrized regression coverage for both Markdown and FAQ with a large budget (one semantic chunk) and an eight-token budget (multiple fallback pieces), asserting both exclusion lists on every result and no mutation of the source lists. RED before the fix: **4 failed, 12 passed**; all four failures showed that the embedding exclusion list was lost. The smallest fix copies both source exclusion lists into each semantic unit; the existing token wrapper restores them onto each final result.

Focused GREEN after formatting: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py -q` → **16 passed in 4.07s**. Black completed; both working and staged `git diff --check` passed. No unrelated changes.
