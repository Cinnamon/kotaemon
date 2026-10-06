# Task 1: Deterministic Local Corpus Inventory — Implementation Report

## Result

Implemented a read-only inventory for the curated local evaluation corpus. The
supported suffixes are `.pdf`, `.docx`, `.md`, and `.xlsx`. Rows use root-relative
POSIX paths and sort lexically by that path. Each source ID is the full lowercase
SHA-256 digest of the exact file bytes. Byte-identical files retain separate rows;
the first sorted path is canonical and later rows identify it through
`duplicate_of`.

The inventory skips `.DS_Store`, Office lock files beginning with `~$`, symlinks,
and unsupported suffixes. Hashing and byte counting read one MiB chunks, so a large
source is not loaded fully into memory. No source files are written or changed.

The new test helpers build deterministic synthetic documents and a small generated
four-source Markdown corpus. All inventory test files were generated under pytest's
temporary directory; no user documents were enumerated or parsed.

## TDD Evidence

### Inventory RED

Command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py -q
```

Expected failure before implementation:

```text
ModuleNotFoundError: No module named 'kotaemon.indices.knowledge.evaluation.local_corpus'
1 error in 4.94s
```

### Generated-fixture RED

After adding the helper contract to the tests, the same focused command failed
because the fixture module was not yet present:

```text
ModuleNotFoundError: No module named 'tests.knowledge_eval_test_fixtures'
1 error in 2.86s
```

### Streaming-hash RED

Command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py::test_scan_sources_hashes_files_in_bounded_chunks -q
```

The new bounded-read regression test failed against the original whole-file read:

```text
AssertionError: assert 0 < -1
FAILED ...::test_scan_sources_hashes_files_in_bounded_chunks
1 failed in 2.84s
```

### Focused GREEN

Command:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_corpus.py -q
```

Final focused output:

```text
test_scan_sources_assigns_stable_ids_and_orders_paths PASSED
test_scan_sources_deduplicates_bytes_and_excludes_lock_files PASSED
test_scan_sources_excludes_symlinks PASSED
test_scan_sources_hashes_files_in_bounded_chunks PASSED
test_generated_corpus_and_document_fixtures_are_deterministic PASSED
============================== 5 passed in 2.45s ===============================
```

### Full core test suite

Command:

```text
uv run pytest libs/kotaemon/tests -q
```

Output summary:

```text
=========== 284 passed, 20 skipped, 94 warnings in 166.74s ===========
```

This was the single full-suite run required by the task. It completed before the
small streaming-hash follow-up; the focused suite was rerun after that change.
The full-suite warnings were emitted by unrelated optional integrations and
dependency deprecations, including Gradio/FastAPI, `pkg_resources`, and an async
mock warning.

### Formatting and diff checks

`uv run black --check` reported four files unchanged before the streaming-hash
follow-up. Black then reported the two follow-up files unchanged. `git diff --check`
completed with no output and exit code 0.

## Self-review and independent review

The initial GPT-6 Sol Medium review found no Critical or Important issues. It
identified one Minor memory concern: reading complete files into memory. The
follow-up changed hashing to bounded one MiB reads and added a regression test
that verifies the bound, exact digest, and byte count. The reviewer rechecked the
follow-up diff and reported no remaining issues; the bounded-read test was judged
sound.

## Changed files

- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/local_corpus.py`
- `libs/kotaemon/kotaemon/indices/knowledge/evaluation/__init__.py`
- `libs/kotaemon/tests/test_knowledge_eval_local_corpus.py`
- `libs/kotaemon/tests/knowledge_eval_test_fixtures.py`
- `.superpowers/sdd/task-1-report.md`

## Cleanup

The full test suite created three root-level directories named like
`<MagicMock name='create' id=...>`, each containing a generated Chroma database.
All three test artifacts were removed before commit. The pre-existing Task 15
section in `.superpowers/sdd/progress.md` was preserved and updated only to mark
Task 1 complete while leaving Tasks 2–7 pending.

## Commits

- `2e2bf9e1f2a553e63716c4a7af5edc59acc2565b` — `feat: inventory local evaluation corpus`
- `ca2f77b6` — `perf: stream local corpus hashing`

No blocking concerns remain. The full suite reported 94 warnings, but no failures.
