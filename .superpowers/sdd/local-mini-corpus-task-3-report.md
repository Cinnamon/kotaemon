# Local mini-corpus Task 3 report

## Result

Added fail-closed source-level snapshot loading with exact manifest-bound payload hashes, source/judgment/anchor relationship checks, validated evidence spans, and an exact-manifest-byte fingerprint. Documented the v1 manifest and anchor schemas in the fixture README.

## TDD evidence

The first focused run failed during collection because `local_snapshot` was missing, as expected. After the implementation, the suite passed at 53 cases. Sol Medium review then found an unchecked `topic_review_source_ids` relationship and mutable nested judgment filters. A focused review-fix subset first reported 11 expected failures and 2 expected-valid cases; after fixes, the final focused run passed:

```text
uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_snapshot.py -q
66 passed in 2.54s
```

Black reported the implementation and test files unchanged. Both staged and unstaged `git diff --check` passed. The independent Sol Medium re-review approved the task with no Critical, Important, or Minor findings. A focused integration check confirmed the new source-reference validation matches the existing Task 2 record shapes.

## Validation behavior

- Requires regular, non-symlink snapshot and payload files; verifies exact bytes for all three payloads before parsing.
- Requires an approved manifest by default; `require_reviewed=False` permits inspection of a fully populated draft snapshot while retaining semantic validation.
- Validates canonical source identities and duplicate-byte provenance; judgments resolve only to parsed canonical sources represented by at least one chunk.
- Checks source-unit, chunk, topic, quality, excluded-input, and manifest provenance relationships.
- Requires source-level judgments, rejects inconsistent allow/disallow scope, and validates evidence anchors against exact normalized-text slices and source locators.
- Requires at least one evidence anchor for every relevant query/source pair.
- Returns read-only record mappings and read-only nested judgment filters.

## Privacy and limits

All CI test payloads and source bytes are generated in pytest temporary directories. The ignored local source corpus was not enumerated or read, and no gold-based metric, model inference, or external service was used. The loader fingerprints the exact manifest bytes and validates the payload hashes it lists; Task 7 must prevent overwriting an existing snapshot version to preserve immutable version history.

## Commit

`2326e634` — `feat: validate local evaluation snapshots`
