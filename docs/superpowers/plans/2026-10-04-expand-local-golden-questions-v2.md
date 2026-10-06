# Local Golden Question Set v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to execute each code task task-by-task. The user has already selected Luna Max implementation and Sol Medium review.

**Goal:** Build a local-only v2 golden candidate containing 80 questions over the unchanged 22-source v1 corpus, with valid source evidence anchors and a reviewable coverage breakdown.

**Architecture:** Add a small tracked Python builder/validator and synthetic tests. Keep source-derived question additions and anchors in the existing ignored local fixture area; the builder copies the frozen v1 records and judgments, then appends new rows and derived anchor metadata without changing v1.

**Tech Stack:** Python 3, pytest, Python standard-library JSON, SHA-256, and pathlib. No network calls or new dependencies.

## Global Constraints

- The approved v1 snapshot under `libs/kotaemon/tests/fixtures/knowledge_eval/local/snapshots/v1/` remains byte-for-byte unchanged.
- The v2 candidate uses the same 22 source documents and exact source hashes as v1.
- v2 contains the 26 v1 questions unchanged plus 54 new questions (`q-027` through `q-080`), for exactly 80 total.
- The 54 additions target 16 direct lookup, 14 procedure/condition, 12 comparison/synthesis, 8 exception/scope, and 4 multi-hop questions; at least 16 additions require two or more distinct source documents.
- Each source must appear in at least one new relevant judgment when the corpus supports a clear answerable question; any unsupported source quota is recorded as a reviewable exception.
- Each relevant query/source pair has at least one hash-verified anchor into a normalized source unit.
- Source-derived files stay under the Git-ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/` directory. Do not commit local question labels, anchors, parsed source text, model files, or run artifacts.
- Subagents receive no source text or evidence spans. Root authors and checks source-derived questions locally; subagents handle generic code and metadata-only review.
- Do not freeze v2 or run the four-arm benchmark until the user approves the candidate labels and anchors.

---

## File Structure

- Create `libs/kotaemon/tests/fixtures/knowledge_eval/local_candidate.py` — deterministic local candidate builder and validator; contains no corpus data.
- Create `libs/kotaemon/tests/fixtures/knowledge_eval/test_local_candidate.py` — synthetic TDD tests for byte-preservation, counts, schema, IDs, anchors, and rejection cases.
- Create `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/additions.jsonl` — 54 locally authored new questions, scope topics, type labels, relevant source IDs, and anchor offsets.
- Create `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/legacy_metadata.jsonl` — type/topic labels for the unchanged 26 v1 questions.
- Create `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/` candidate outputs — copied records, 80 judgments, anchors, `question_metadata.jsonl`, `manifest.json`, and review notes.

## Task 1: Build and validate v2 candidates with TDD

**Files:**
- Create: `libs/kotaemon/tests/fixtures/knowledge_eval/local_candidate.py`
- Test: `libs/kotaemon/tests/fixtures/knowledge_eval/test_local_candidate.py`

**Interfaces:**
- `build_candidate(v1_dir: Path, additions_path: Path, legacy_metadata_path: Path, output_dir: Path) -> dict[str, int]` builds the draft.
- `validate_candidate(v1_dir: Path, additions_path: Path, legacy_metadata_path: Path, output_dir: Path) -> dict[str, int]` verifies it and returns counts without printing source text.
- CLI: `python libs/kotaemon/tests/fixtures/knowledge_eval/local_candidate.py build --v1 PATH --additions PATH --legacy-metadata PATH --output PATH`; command `validate` accepts the same arguments.
- Addition row fields: `id`, `query`, `topic`, `query_type`, `relevant_ids`, `scope_source_ids`, and `anchors`; each anchor has `source_id`, `unit_id`, `char_start`, and `char_end`. `scope_source_ids` lists the fixed corpus sources permitted for that question; the builder derives `disallowed_source_ids` as the complement of that list.
- Allowed `query_type` values are `direct_lookup`, `procedure_condition`, `comparison_synthesis`, `exception_scope`, and `multi_hop`. Allowed topic values are the existing labels `Climate`, `LLM`, `Rice`, and `Environmental-health`; source scope is validated from `scope_source_ids`, independently of the reporting label.
- A legacy metadata JSONL row has exactly `query_id`, `topic`, and `query_type`; there must be exactly one for each v1 query.
- Each addition and metadata input is JSONL (one JSON object per non-empty line); the builder does not accept JSON arrays.
- Output `question_metadata.jsonl` has one row per query with exactly `query_id`, `topic`, `query_type`, and `relevant_source_count`; the count is derived from the judgment `relevant_ids`.
- Output `manifest.json` has `snapshot_version: "v2-draft"`, `review_status: "draft"`, `review_date: null`, `parent_manifest_sha256`, counts including `new_queries`, and `payload_sha256` entries for `records.json`, `judgments.jsonl`, `anchors.jsonl`, and `question_metadata.jsonl`.

- [x] **Step 1: Write failing tests first.** Build temporary synthetic v1 data with 22 sources, 26 judgment rows, 44 valid anchors, and normalized source units; write 54 synthetic additions matching the stated type quotas and at least 16 multi-source cases; create 26 metadata rows. Assert `build_candidate(...)` returns `{"documents": 22, "queries": 80, "new_queries": 54}` and writes v1 judgments/anchors as byte-identical prefixes. Add focused negative tests for duplicate IDs/prompts, unknown sources, missing relevant-pair anchors, invalid offsets, mismatched source/evidence hashes, wrong quotas, and a modified v1 parent. Create an empty `local_candidate.py` module only after the test file so pytest can collect the tests; do not define the requested functions yet.
- [x] **Step 2: Verify RED.** Run `pytest libs/kotaemon/tests/fixtures/knowledge_eval/test_local_candidate.py -q`; confirm the tests fail by calling the missing `build_candidate`/`validate_candidate` API, with no import or fixture errors.
- [x] **Step 3: Implement the smallest builder and validator.** Copy `records.json` bytes; retain the exact v1 JSONL bytes as prefixes in v2 judgments and anchors; append schema-valid rows; derive disallowed IDs as the complement of each row's `scope_source_ids`; derive each anchor locator and hashes from the referenced v1 source unit; write deterministic `question_metadata.jsonl` and `manifest.json` with hashes for the four payload files. The validator must reject any changed v1 prefix, changed 22-source hash set, invalid count/ID/type quota, duplicate normalized prompt, a relevant source outside its declared scope, missing anchor, or offset/hash mismatch. Build twice from identical inputs and compare output hashes to prove deterministic output.
- [x] **Step 4: Verify GREEN.** Re-run the focused pytest command and require all synthetic tests to pass with no warnings.
- [x] **Step 5: Commit only the tracked generic helper and synthetic tests.** Do not force-add or commit anything under `local/`.
- [x] **Step 6: Sol Medium reviews the task diff** for contract compliance and quality; fix and re-review any Critical or Important finding before proceeding.

## Task 2: Author and assemble local question additions

Root performs this source-reading step locally; no subagent receives raw source text or anchor spans. This keeps source-derived content within the local workspace while Luna Max remains responsible for the builder/validator implementation and Sol Medium for code and metadata-only review.


**Files:**
- Create: ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/additions.jsonl`
- Create: ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/legacy_metadata.jsonl`
- Create: ignored v2 candidate outputs from Task 1

- [x] **Step 1: Assign 54 distinct questions to the approved five query types and the existing four source-scope topics.** Each question must be answerable from cited source material, not just its title or filename.
- [x] **Step 2: Cover every supported source in at least one new relevant judgment and create 16 or more multi-source additions where the corpus supports the relationship.** Keep the multi-source questions within a valid source-scope topic.
- [x] **Step 3: Select one or more concise evidence spans per relevant source from the correct normalized source unit; store only unit IDs and offsets.**
- [x] **Step 4: Classify all 26 legacy questions by topic and query type without changing their judgment rows.**
- [x] **Step 5: Run the builder, then run the validator.** Require 22 source documents, 80 queries, 54 additions, complete relevant-pair anchors, approved type quotas, and no v1 changes.
- [x] **Step 6: Locally inspect all new questions and anchors for answerability, scope, ambiguity, near-duplicates, and source support.** No source text is sent to external services.
- [x] **Step 7: Sol Medium reviews the non-source-bearing structural report and coverage totals.** Root verifies every anchor against local source text; reviewer output cannot replace this local grounding check.

## Task 3: Prepare v2 for user review

**Files:**
- Modify ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/REVIEW.md`
- Modify ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v2/manifest.json` only through the builder

- [x] **Step 1: Produce a review table for all 54 new questions** with question ID, topic, query type, relevant document display labels, and a concise evidence-location description; do not include raw source spans.
- [x] **Step 2: Record exact source/query/anchor counts, type coverage, multi-source count, build command, validation output, and SHA-256 manifest.** Mark status as `draft` and leave approval fields empty.
- [x] **Step 3: Confirm the v1 snapshot manifest and payload hashes are unchanged.**
- [x] **Step 4: Present the v2 candidate for user review.** Stop before freezing v2 or rerunning any retrieval arm.

## Task 4: Freeze the approved v2 set and run the four-arm evaluation

The user approved the 80-question candidate and the frozen source-level metrics on 2026-10-04. Source-derived data, the frozen snapshot, model files, per-query report, and traces remain in the Git-ignored local fixture tree.

- [x] **Step 1: Close the freeze integration gaps with TDD.** The candidate builder now validates and carries forward the v1 manifest's safe `source_root`; the freeze command constructs the exact strict snapshot manifest schema and drops draft-only fields. Synthetic candidate tests: 37 passed. Synthetic freeze tests: 3 passed; broader local CLI tests: 32 passed, 1 protected-fixture test deselected.
- [x] **Step 2: Revalidate the v2 candidate and preserve reviewed content.** Validation reported 22 documents, 80 queries, and 54 additions. A byte comparison found only the candidate `manifest.json` stale; `records.json`, `judgments.jsonl`, `anchors.jsonl`, and `question_metadata.jsonl` matched the reviewed inputs unchanged.
- [x] **Step 3: Freeze v2 and load it independently.** The approved snapshot loaded with 22 documents, 80 questions, and 139 anchors; its fingerprint is recorded in `docs/superpowers/reports/local-knowledge-eval-v2.md`.
- [x] **Step 4: Run baseline, chunking, embedding, and reranker arms offline.** K=5 distinct sources, candidate pool K=20; local BGE-M3 and BGE-reranker-v2-M3 assets are pinned by the revisions in the aggregate report. Verify every artifact listed in the run sidecar by size and SHA-256.
- [x] **Step 5: Record aggregate metrics and limits.** The result table and one-factor changes are in `docs/superpowers/reports/local-knowledge-eval-v2.md`; no per-query or source-derived content is tracked.

## Self-review

- Coverage: the plan preserves v1, creates exactly 54 additions, builds hash-backed evidence, validates deterministic output, waits for explicit approval, then freezes and evaluates the approved set.
- TDD order: synthetic tests and observed failures precede implementation; local candidate generation only begins after the helper review passes.
- Privacy: tracked changes include generic code, synthetic tests, and an aggregate-only result summary; source-derived questions, evidence, models, the frozen snapshot, and per-query artifacts remain in the ignored local fixture area.
- Scope: no production retriever, model, or scoring rule is changed; the approved local snapshot and its four-arm benchmark are recorded as this plan's final task.
