# Local mini-corpus Task 2 report

### TDD evidence

Added generated, multi-format fixtures under `tmp_path` before implementing the draft builder. The first focused run was:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_ingest.py -q
```

It exited 2 during collection with:

```text
ModuleNotFoundError: No module named 'kotaemon.indices.knowledge.evaluation.local_ingest'
```

That confirmed the absent implementation. Subsequent red runs exposed an `AttributeError` while checking reader diagnostics, `KeyError: 'ignored.py'` when the unsupported path was absent from exclusions, and propagation of `ValueError: Token splitter returned a segment outside its source unit` instead of a review issue. A later regression case also caught an invalid span endpoint (`char_end` could exceed the unit length even when Python slicing returned matching text); the implementation now derives the end from the final mapped part and validates both bounds and exact slice equality.

After implementation, the focused Task 1 inventory and Task 2 ingest suite passed:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py libs/kotaemon/tests/test_knowledge_eval_local_ingest.py -q
8 passed, 6 warnings in 4.66s
```

The six warnings are dependency deprecations from PyMuPDF bindings and the installed cryptography provider. Formatting and whitespace checks passed:

```text
uv run black --check libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_corpus.py libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_ingest.py libs/kotaemon/tests/test_knowledge_eval_local_ingest.py
3 files would be left unchanged.
git diff --check
exit 0
```

### Implementation

- Added `build_local_draft` with deterministic records and chunk IDs, root-relative source provenance, empty `anchors.jsonl`, and writes restricted to the caller-provided output directory.
- Normalizes CRLF and CR to LF and applies Unicode NFC while retaining paragraph and line boundaries. Blank extraction checks trim only for emptiness; offsets remain relative to the preserved normalized text.
- Reads only selected canonical supported sources. Byte duplicates remain in the exclusion/provenance report and have an observable test assertion that only the canonical path gets a reader diagnostic. Supported files are hashed by the inventory stage to establish content identity; unsupported files are listed by relative path without opening or hashing their contents.
- Added PDF, DOCX, Markdown, and XLSX generated fixtures covering reader locators, empty PDF pages, blank spreadsheet rows, malformed DOCX, duplicate bytes, unsupported files, and deterministic output in separate draft directories. The Task 1 Markdown-only `make_generated_corpus` contract remains unchanged.
- Records the selected parser and attempts in source configuration and quality diagnostics. In this environment, `UnstructuredReader(split_documents=True)` cannot initialize because `libmagic` is unavailable; a local `DocxReader` fallback is selected and explicitly reported as document granularity with `needs_review=True` because it coalesces paragraph text. No element locator is invented. Corrupt DOCX input remains in the report as an extraction failure.
- Records the token splitter configuration and version (`main-token-only-v1`, size 1024, overlap 256, separator, and backup separators) in the deterministic records. Chunk spans are checked for `0 <= start <= end <= len(unit)` and exact normalized-text equality. Unmappable offsets preserve the source unit and produce a review-needed quality issue rather than guessed chunks.
- Topic candidates come from extracted content only. Sources without a candidate are marked for topic review. `anchors_payload` is deterministic empty bytes because this API has no query input.
- Unsupported regular-file paths are listed without reading content. Office lock files, `.DS_Store`, and symlinks remain excluded.

### Changed files

- `docs/superpowers/plans/2026-10-03-mini-corpus-golden-experiment.md` — incorporated the Task 2 design amendment for queryless anchors, provenance, output boundaries, locators, extraction quality, and splitter configuration.
- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_corpus.py` — added canonical-source selection and safe unsupported-path listing.
- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_ingest.py` — added local parsing, chunk drafts, metadata, and quality reporting.
- `libs/kotaemon/tests/test_knowledge_eval_local_ingest.py` — added generated multi-format and regression tests.
- `.superpowers/sdd/local-mini-corpus-task-2-report.md` — this implementation report.

### Limitations

- The local review-draft API does not create query-linked evidence anchors; `anchors.jsonl` is empty until reviewed questions and spans exist.
- The production CLI that enforces containment under the ignored `local/draft/` tree is outside Task 2. This API writes only beneath the explicit `output_dir` argument, and tests use temporary directories.
- DOCX parsing uses the local fallback in this environment, which provides document-level granularity and requires human review because it coalesces paragraphs.
- The prohibited `libs/kotaemon/tests/fixtures/knowledge_eval/local/sources/` tree was not accessed; all ingestion tests use generated temporary files.

## GPT-6 Sol Medium review follow-up

### Finding 1: anchors artifact filename

Changed the generated-fixture assertion to require an empty `anchors.jsonl` and no `anchors.json`. Before changing the writer, the targeted test failed with `FileNotFoundError` while opening `draft-a/anchors.jsonl`. After the writer and report references were corrected, the same test passed: `1 passed, 6 warnings`.

### Finding 2: preserve line and paragraph structure

Added a generated Markdown regression with CRLF line endings, blank paragraphs, an intra-paragraph newline, decomposed Unicode, and enough text for overlapping chunks. Before changing normalization, the targeted test failed because `normalized_text` flattened `# Notes\r\n\r\n...` into space-separated text. The fix converts CRLF/CR to LF and applies NFC without collapsing whitespace. The test verifies paragraph and line boundaries, NFC output, exact equality with the existing configured `TokenSplitter.split_text` output, overlapping spans, in-bounds offsets, exact source slices, and repeatable chunk IDs. The targeted test passed: `1 passed, 5 warnings`.

Final focused verification after both fixes:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py libs/kotaemon/tests/test_knowledge_eval_local_ingest.py -q
9 passed, 6 warnings in 4.54s
```

The six warnings remain dependency deprecations from PyMuPDF bindings and the installed cryptography provider. Final checks passed: Black reported 3 files unchanged, and `git diff --check` exited 0.

### Commit

Implementation commit SHA: `25d5eadc3fc3683300bd8e0c2d4a3932fd582c10` (`feat: prepare local corpus review drafts`).
Follow-up fix commit SHA: `d4ec0f82a1716ddf589c1a469587225ad15fdf18` (`fix: preserve local review draft formats`).
