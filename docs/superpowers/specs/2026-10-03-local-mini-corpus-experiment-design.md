# Local mini-corpus retrieval experiment

## Decision

Use a staged evaluation. First inventory and parse the current local source corpus
into ignored draft artifacts. Build a reviewed v1 from 20–24 unique documents,
stratified by content-derived topic and file format. After v1 is reviewed and
evaluated, expand to the complete byte-unique corpus in a separately reviewed
snapshot and report the expanded run as a second experiment.

Directory names are provenance only. They must not be copied into source topics,
virtual paths, planner entities, or judgments unless a person verifies that they
match the document contents. Do not rename or modify original files. Exclude
filesystem/Office lock artifacts from indexing, deduplicate byte-identical files
by SHA-256, and preserve their paths as local provenance.

## Data preparation

Read the four input formats through the existing default ingestion mapping:
normal `PDFReader` for PDF, `UnstructuredReader` for DOCX, `TxtReader` for
Markdown, and `ExcelRowReader` (with the configured pandas fallback) for XLSX.
Use the current normal PDF extraction mode first. Record per-source and
per-page extraction quality; do not silently accept empty or unusable pages.
Put low-quality sources in a local review queue. If OCR is needed, use it as a
separately recorded parser configuration and regenerate a new snapshot rather
than mixing parser outputs invisibly.

Create one source record per unique original file. Derive stable source and chunk
IDs from source content hashes and deterministic chunk positions. Preserve
relative source paths and hashes in the local manifest. Use content-derived
document names, topics, virtual paths, and entities as draft metadata; include a
human review status for every field that affects scoping. Chunk with the
existing configured splitter (the current default is 1,024 tokens with 256
tokens of overlap) and record its exact version and parameters.

All source-derived material stays under the Git-ignored `local/` directory:
source inventory, extraction report, draft records, candidate judgments, review
evidence, snapshots, traces, and result artifacts. CI tests use generated
fixtures only. No source text, query text, gold labels, or private-corpus metric
artifacts are added to tracked files or published in the existing PR without
explicit authorization.

## Fixed golden v1

Select 20–24 unique documents from the parsed corpus, covering each usable file
format and the substantive content topics found during extraction. Keep related
hard negatives in the same sample. Prepare roughly 20–30 candidate questions,
with the final count determined by evidence quality. Include explicit
document/entity/path questions, content questions, cross-document questions,
and ambiguous/global questions where the source material supports them.

Freeze the semantic gold at the source level so it remains unchanged when a
chunking arm produces different chunk boundaries and IDs. Every query records
stable content-hash-based `source_id` values for relevant and, where an
explicit scope is violated, disallowed sources. Preserve evidence anchors in
`anchors.jsonl`: query ID, source SHA-256, page/sheet/section locator,
normalized-text offsets, and a digest of the cited passage. Require at least one
anchor for every relevant query/source pair. Anchors establish that each source
judgment has concrete evidence and allow each chunking arm to report whether its
chunks cover that evidence; do not write arm-specific chunk IDs back into the
frozen gold.

Use the evaluator's `judgment_level="source"` for every v1 case. Score the
first five distinct source IDs in the ranked chunk results, in first-occurrence
order, so repeated chunks from one source do not consume multiple positions in
source-level Hit@5, Recall@5, MRR@5, or Wrong-scope@5. Keep evidence-anchor
coverage and same-source/wrong-passage diagnostics separate from the four main
metrics. Questions and labels must be created independently of retrieval
outputs; gold answers, evidence anchors, and judgment IDs must not be included
in indexed text or metadata. Set `disallowed_source_ids` only for sources that
clearly violate an explicit scope; irrelevance alone is not wrong scope. Use no
wrong-scope label for ambiguous or global questions. The current fixture schema
already supports source-level judgments and rejects mixed judgment levels.

Before freezing v1, present the user a local-only review package containing the
source-to-content-topic mapping, excluded/duplicate file list, extraction
quality summary, chunk previews, and per-question evidence, relevant IDs, and
wrong-scope IDs. Do not run or report gold-based metrics until the user approves
the labels. Freeze approved files under `local/snapshots/v1/` with exact-byte
SHA-256 hashes for `records.json`, `judgments.jsonl`, and `anchors.jsonl`,
source hashes, schema and parser/chunker versions, counts, and review
status/date.

For the later full-corpus snapshot, re-review relevance and scope labels against
the added sources. In particular, update `disallowed_source_ids` where new
sources clearly violate a query's explicit scope. Freeze it as a new version;
never mutate v1.

## Fixed K=5 experiment matrix

Load only an explicitly selected, hash-verified local snapshot. Use the same
reviewed query/source gold, evidence anchors, query order, filters, global
identity planner, vector-only retrieval mode, random seed, and source metadata in
all four arms. Keep final K=5 and request an M=20 vector candidate pool in every
arm; set `first_round_top_k_mult=1`, disable query rewriting and result
extension, and set the parent/section cap to `None`. Record the vector candidate
window before reranking and post-ranking duplicate/diversity processing. This
holds planning and candidate depth constant so the component experiments do not
confound retrieval changes with planner behavior.

Run these one-factor comparisons against one shared baseline. The baseline
chunker reproduces the token-only behavior in the main-branch version recorded
in the local snapshot manifest; the chunking arm uses this branch's registered
source-aware strategy with the same splitter parameters.

| Arm | Chunking | Embedding | Reranker |
| --- | --- | --- | --- |
| Baseline | pre-upgrade token splitter, 1,024/256 | deterministic hashed-feature offline baseline | none |
| Chunking | registered source-aware strategy, same 1,024/256 splitter | unchanged baseline embedding | none |
| Embedding | unchanged baseline chunking | `BAAI/bge-m3` dense embeddings | none |
| Reranker | unchanged baseline chunking | unchanged baseline embedding | `BAAI/bge-reranker-v2-m3` |

The hashed-feature baseline is a reproducible offline control, not a claim about
the user's current production embedding. Implement both model arms with local
inference only. Persist model identifiers and resolved revisions, model-file
hashes, runtime/library versions, tokenization and truncation parameters, and
whether model weights were cached or downloaded. Do not send source text or
queries to a remote service. Require the local models to be available before
running those arms; do not silently substitute a different model.

For the reranker comparison, assert that each query's reranker receives exactly
the same ordered pre-reranker vector candidate window as the baseline. Score the
baseline using the same candidates before reranking. If fewer than 20 candidates
exist, retain the query and record the actual count. After ranking and the same
post-processing, map results to first-occurrence source IDs and score the first
five distinct sources. Do not silently drop queries or tune model/chunk settings
against the frozen evaluation gold.

Report macro Hit@5, Recall@5, and MRR@5 across all judged queries. Compute
Wrong-scope@5 as the pooled count of disallowed distinct sources divided by the
number of distinct source results in the first-five window for queries with an
explicit wrong-scope label; report its numerator/denominator and show it as
undefined when the denominator is zero. For every arm, include its metric value,
baseline value, signed delta (`variant - baseline`), query count, and source-level
judgment unit. Higher Hit/Recall/MRR and lower Wrong-scope are improvements.
Also report evidence-anchor coverage and pre-rerank candidate counts as
diagnostics.
Include per-query results, run manifests, and traces in ignored local artifacts.
The existing synthetic planner comparison remains a separate experiment; it is
not mixed into these three retrieval component comparisons.

## Implementation and verification tasks

1. Add TDD-covered local inventory, artifact exclusion, content-hash dedup,
   parsing, quality reporting, deterministic IDs, and draft generation. Write
   only to the ignored local directory.
2. Add a snapshot loader/validator that requires a reviewed manifest, verifies
   exact payload hashes, checks all IDs/relationships, and accepts an explicit
   snapshot path without changing the synthetic default.
3. Add and test an offline experiment runner that supports the fixed
   source-level gold and the one-factor chunking/embedding/reranker arms. Tests
   must prove source-level rank deduplication, K=5/M=20 handling, stable-gold
   validation, reranker candidate identity, and configuration parity within
   each comparison.
4. Generate and present the local-only v1 review package. After user approval,
   freeze v1 and run the four-arm experiment, using only explicitly selected
   local models. Repeat for the expanded snapshot only after its labels are
   reviewed.

## Acceptance criteria

- The local source tree is unchanged and remains Git-ignored.
- Repeated inventory and parsing produce stable IDs and equivalent draft
  payloads under the same parser/chunker versions.
- Artifacts and duplicate source files are accounted for, and low-quality pages
  are surfaced rather than silently omitted.
- Snapshot hash mismatch, missing review status, unknown IDs, or invalid source
  relations fail before retrieval.
- The v1 fixture has one source-level judgment level, evidence anchors for
  every relevant source, and only explicit wrong-scope labels.
- Every report arm uses the same approved gold and query order and reports the
  four K=5 source-level metrics with denominators and signed deltas.
- The chunking arm records evidence-anchor coverage; the reranker arm proves
  candidate identity with the no-reranker baseline.
- Private source-derived data and results remain local unless the user later
  explicitly approves publication.
