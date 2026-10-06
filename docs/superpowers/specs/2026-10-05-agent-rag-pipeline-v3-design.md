# Agent RAG Pipeline v3 Design

## Decision and scope

Extend Kotaemon's existing file-index `KnowledgeService -> VectorRetrieval ->
PrepareEvidencePipeline` path. Reuse the same retrieval and evidence policies in
the read-only local QA workbench. The file UI keeps its selected-file contract;
the Agent service continues to use the SQL-visible catalog and an optional
caller allowlist. This work does not connect an enterprise Wiki or add an ACL
provider: callers must provide logical paths, metadata, and visibility.

The frozen v2 mini corpus, judgments, anchors, and four single-factor reports
remain immutable. New combination and conversation evaluations get a new run
identity and write only under the Git-ignored local fixture tree. Query text,
source text, generated answers, and per-query traces stay local. No remote model
call is permitted by the local workbench.

The corpus is general enterprise material. Paper-specific bibliography routing,
author extraction, and a paper reading workspace are outside this upgrade.

## Existing behavior and design alternatives

The product path already has optional PDF/DOCX/Excel/Markdown readers,
source-aware chunking, vector/text/hybrid modes, configurable rerankers, and
citation formatting. Its hybrid path currently concatenates lexical then vector
candidates and deduplicates by ID; it does not run rank fusion. `do_extend`
multiplies recall depth; it is not context expansion. The local workbench uses
PDFReader/UnstructuredReader/TxtReader/ExcelRowReader to form its approved
snapshot, then indexes baseline token chunks with BGE-M3. It searches 20 vector
candidates with no reranker and shows chunks from the first five distinct
sources. It imports private evaluation helpers and has no explicit generation
context budget or conversation state.

Three approaches were considered:

1. Add a separate RAG implementation behind the workbench. This is fast to
   demonstrate but duplicates scope and citation behavior.
2. Replace the product index and loaders. This makes migrations, access rules,
   and existing saved configurations the dominant risk.
3. **Selected:** add small, testable policies to the current retrieval and
   evidence abstractions, then adapt both entry points. Existing readers and
   indexes stay usable, and each new stage is visible in the retrieval trace.

## Data flow and boundaries

```text
source readers -> normalized metadata -> source-aware chunks -> index
question + optional session history
  -> hard caller visibility and exact metadata scope
  -> soft query enrichment (original retained)
  -> dense / lexical recall batches
  -> weighted rank fusion -> optional cross-encoder rerank
  -> duplicate and section diversity -> ranked seed chunks
  -> authorized same-unit evidence expansion
  -> seed-first context packing and citation map
  -> local/product answer generation
```

The hard visibility boundary is computed from the original request and SQL
catalog before enrichment. A rewritten query can change recall text but cannot
enlarge `allowed_source_ids`, path/type/entity filters, or user visibility.
Branch failures are recorded distinctly from valid empty results. A failed
branch may degrade to the other; both failing returns an error.

### Parsing and chunk identity

Retain the format-specific readers already in use. Record parser name, version,
fallback, extraction granularity, and quality diagnostics for every local
source. The product's optional Docling reader remains optional; its page text,
tables, and figures are not represented as a verified scientific section tree.
Existing Markdown headings, FAQ pairs, Python AST units, PDF/PPT structural
metadata, Excel rows, and token fallback remain the chunking choices.

Newly indexed chunks also carry a stable source version, source-unit ID,
ordinal within that unit, and the real IDs of their immediate previous and
next chunks in that unit. They preserve the real chunk ID, page/row/section
locator, parent relation, and available source offsets. Neighbor lookup reads
only the at-most-two IDs recorded on a seed, after checking both IDs against
the caller's authorized chunk set; it then validates source, version, unit,
and ordinal on the fetched records. A parent ID is not treated as a readable
document unless the docstore actually stores it. Older chunks lacking
adjacency metadata remain searchable and simply skip expansion.
The v2 approved snapshot is never reparsed in place.

### Query enrichment and multi-turn retrieval

`QueryEnricher` returns an `EnrichedQuery` containing the original question, a
standalone retrieval question, bounded query variants, and an audit reason.
The default is the original question. Deterministic lexical extraction retains
exact names, paths, codes, versions, and quoted terms. An optional local Ollama
rewriter may resolve one follow-up against recent user turns; its output is
validated, deduplicated, and limited to a small number of routes. Failure or
timeout falls back to the original question. The answer generator still sees
the user's original question and the retrieved evidence.

Conversation history is per UI session, bounded by turn and token limits, and
never written to the frozen snapshot. Retrieval uses a standalone question for
clear follow-ups while topic changes use the current question. Prior generated
answers are not treated as evidence or hard scope. The product's existing
generation-history support is preserved; the new behavior addresses retrieval
history, which it currently lacks. No conversation metric is inferred from the
independent single-turn v2 gold.

### Recall, fusion, and reranking

Each recall route records query variant, branch, rank, candidate IDs, status,
and available backend score. The product can use its current lexical backend;
the local snapshot gains an ephemeral SQLite FTS5 index so the workbench can
exercise a real lexical route without changing its frozen source files. Its
index text uses deterministic Unicode normalization, Latin/code token
extraction, and overlapping Chinese character bigrams before FTS5 `unicode61`
indexing. A Chinese term inside a longer sentence and a Latin term adjacent
to Chinese text must both be retrievable in synthetic tests. This is a
bounded lexical baseline, not a claim that it matches a dedicated Chinese
segmenter. Where FTS5 or a product docstore cannot do lexical search, the trace says
`unavailable` and the dense route remains usable. BGE-M3 stays the local dense
model; model files and revisions continue to be verified offline.

Fuse valid batches with weighted Reciprocal Rank Fusion:
`fusion_score(d) = sum(route_weight / (60 + one_based_rank(d)))`.
Duplicate IDs contribute once per route. Dense and lexical each have a fixed
total vote weight, divided among variants of that branch, so adding a rewrite
does not multiply its branch's total influence. Stable ties use first-seen
route order and ID. Fusion score and branch ranks live in retrieval metadata;
raw backend scores retain their original meaning. Default weights are equal
until separately evaluated. The candidate pool size is distinct from final K.

Reranking receives only fused candidates that passed the hard scope. The local
cross encoder is `BAAI/bge-reranker-v2-m3`; its adapter moves from evaluation
internals to a public, optional runtime component. Its score, model revision,
and truncation configuration are traced. Existing configured product rerankers
remain supported. No absolute score is interpreted as a probability or used as
an uncalibrated reject threshold. After rerank, existing exact-text, overlap,
and per-section diversity rules produce ranked seed chunks.

### Evidence expansion, packing, and citation validity

The expansion unit is a real indexed chunk adjacent to a seed within the same
source version and semantic unit. At most one neighbor on either side is
eligible in v3. A resolver checks source ID, unit ID, ordinal, version, and
caller-visible chunk IDs against the catalog before reading a neighbor. Missing
or inconsistent metadata skips expansion. Expanded text is never relabeled
with the seed ID. The product's optional same-page table retrieval remains a
separate behavior, with its own trace status.

An evidence policy records each accepted or rejected neighbor and why. It
rejects empty text, duplicate/overlapping content, cross-scope material, and
excess per-source or total evidence. Seed chunks keep their reranked order;
neighbors are supporting context, not additional Top-K hits. When the local
cross encoder is configured, a neighbor is accepted only if its query/passage
score is no lower than the lowest scored seed retained in the Top-K window.
This is a relative gate, not a calibrated probability. Without a scorer,
expansion is skipped and traced as `scorer_unavailable`; the original seeds
remain usable. The scorer input must preserve the full seed text; an oversized
neighbor is shortened or rejected before scoring.

Context packing computes `available = model_context - system - question -
bounded_history - output_reserve - format_reserve` through a generator-specific
token-counter interface. The local Qwen adapter uses its matching tokenizer
when installed; otherwise it uses a conservative estimate and reports that
the budget is estimated. It inserts whole seed evidence first, then eligible
expansions with remaining capacity. Oversized units are skipped, never
silently cut. If no
seed fits, generation receives an explicit insufficient-evidence status rather
than a context made only of neighbors. The citation map contains exactly the
evidence units actually passed to generation. The trace records seed IDs,
expanded IDs, rejected IDs, final context IDs, token use, and omissions. The
existing product formatter continues to accept old records and tokenizer
configuration, but the local Ollama path uses an explicit model budget.

These checks guarantee authorization, provenance, complete-unit formatting,
and budget compliance. They do not by themselves guarantee factual relevance;
that is measured with final-context anchors and answer/citation judgments.

## Evaluation and rollout

The four existing v2 one-factor arms remain their own report. Add a versioned
combination run over the same approved source-level gold with a fixed parser,
query order, model manifest, and candidate/final K. Compare dense baseline,
lexical/RRF, rerank, query enrichment, and expansion incrementally; include a
final-config ablation. Report both the old source-level Hit@5, Recall@5,
MRR@5, Wrong-scope@5 and candidate recall, final-context anchor coverage,
context token use, unavailable routes, and per-stage latency. Combination
results cannot be described as a single-factor effect.

Create a separate reviewed conversation fixture for follow-up resolution,
topic switching, and no-answer behavior. Do not alter v2 questions or infer
multi-turn quality from them. Answer support, citation precision, and p95
latency require separately recorded runs; no target value is promised before
measurement. Zero unauthorized chunks, zero violations of the configured
token-counter budget, stable fingerprints, and trace-to-context identity are
hard acceptance conditions.

Enable new retrieval stages behind explicit settings in the product file UI;
the workbench displays branch ranks, fusion/rerank scores, seed/neighbor
decisions, and final included evidence. If a component is unavailable, show the
degraded configuration instead of claiming the full stack ran. The Agent
factory alone does not constitute a deployed Agent tool; wiring one requires a
caller and its own access-scope acceptance test.

## Risks

- Reader structure varies across formats. Missing structure uses the current
  token fallback; adjacency expansion never invents a section or page.
- SQLite FTS5 and backend tokenization may perform unevenly on Chinese text.
  The local experiment records lexical status and per-query misses.
- Cross-encoder and local rewrite latency may be large. Bound candidate depth,
  variant count, neighbor count, history, and token use, and report p50/p95.
- Scope planning and rewrite are distinct: rewriting cannot change a hard
  caller filter. Fallback to a broader planned scope stays inside the caller's
  visible catalog and is traced.
