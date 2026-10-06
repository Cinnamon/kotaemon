# RAG pipeline v3 aggregate validation

**Scope:** offline retrieval and context-packing validation on the approved v2 snapshot. This is an aggregate report; it contains no query text, source names, evidence text, identifiers, or per-query rows.

## Run and validation method

- Dataset: 80 reviewed source-judgment queries; 11 arms; 880 complete arm/query trace-summary pairs.
- The first full checkpointed execution completed all 880 pairs but failed the old context-budget gate with 510 violations. The cause was a counting mismatch: packing budgeted a raw prompt plus user payload separately, while the final gate counted the serialized system/user message envelope.
- The packer and final gate now count the same serialized full-message form (`serialized-full-message-v1`). The complete checkpoint was authenticated against the approved snapshot, gold judgments, local model manifest, global and per-arm configuration fingerprints, and trace/summary hashes. The repack replayed persisted ranked trace IDs and scores, reconstructed packed contexts, and recomputed context metrics; it did not rerun retrieval, embedding, or reranking inference.
- An earlier unbound partial staging tree was preserved locally and excluded from this report.
- Snapshot file hashes remained unchanged. The completed repack artifact manifest contains 1,774 entries; all 1,774 file sizes and SHA-256 digests verified. The artifact contains 880 traces across 11 arms.

## Retrieval metrics

Hit@5, Recall@5, and MRR@5 are macro averages over 80 judged queries, using the first five distinct sources after reranking. Wrong-scope@5 is pooled over returned distinct source slots across all 80 scope-labeled queries; its exact numerator and denominator are shown. Values are descriptive; no significance or causal claim is made.

| Arm | Hit@5 | Recall@5 | MRR@5 | Wrong-scope@5 (wrong / returned distinct sources) |
|---|---:|---:|---:|---:|
| `dense_baseline` | 100.00% | 99.17% | 0.9244 | 7/306 (2.29%) |
| `registry_chunking` | 100.00% | 98.96% | 0.9150 | 7/311 (2.25%) |
| `registry_lexical_rrf` | 100.00% | 99.58% | 0.8515 | 13/338 (3.85%) |
| `registry_reranking` | 100.00% | 99.58% | 0.9344 | 9/338 (2.66%) |
| `registry_enrichment` | 100.00% | 99.58% | 0.9354 | 11/349 (3.15%) |
| `registry_expansion` | 100.00% | 99.58% | 0.9354 | 11/349 (3.15%) |
| `ablation_no_chunking` | 100.00% | 99.17% | 0.9406 | 11/345 (3.19%) |
| `ablation_dense_only` | 100.00% | 99.58% | 0.9271 | 9/330 (2.73%) |
| `ablation_no_reranker` | 100.00% | 98.33% | 0.8869 | 16/349 (4.58%) |
| `ablation_no_enrichment` | 100.00% | 99.58% | 0.9344 | 9/338 (2.66%) |
| `ablation_no_expansion` | 100.00% | 99.58% | 0.9354 | 11/349 (3.15%) |

Candidate recall is measured before reranking at a cutoff of up to 40 fused chunk IDs, then scored as relevant distinct source IDs. Its denominator is the 109 relevant source judgments over 80 queries. Final-context anchor coverage is measured only over the exact packed context; the rate is covered / (covered + uncovered), excluding unresolved anchors. This run had 139 eligible anchors and zero unresolved anchors.

| Arm | Candidate source recall@40 | Final-context anchor coverage |
|---|---:|---:|
| `dense_baseline` | 107/109 (98.17%) | 111/139 (79.86%) |
| `registry_chunking` | 108/109 (99.08%) | 102/139 (73.38%) |
| `registry_lexical_rrf` | 108/109 (99.08%) | 97/139 (69.78%) |
| `registry_reranking` | 108/109 (99.08%) | 109/139 (78.42%) |
| `registry_enrichment` | 108/109 (99.08%) | 110/139 (79.14%) |
| `registry_expansion` | 108/109 (99.08%) | 109/139 (78.42%) |
| `ablation_no_chunking` | 108/109 (99.08%) | 119/139 (85.61%) |
| `ablation_dense_only` | 108/109 (99.08%) | 109/139 (78.42%) |
| `ablation_no_reranker` | 108/109 (99.08%) | 93/139 (66.91%) |
| `ablation_no_enrichment` | 108/109 (99.08%) | 110/139 (79.14%) |
| `ablation_no_expansion` | 108/109 (99.08%) | 110/139 (79.14%) |

## Incremental comparisons

Each delta is the current arm minus its immediate predecessor in the fixed sequence. Rate deltas are percentage points (pp); MRR is the raw difference on a 0–1 scale. Each comparison uses the same 80 queries.

| Arm vs predecessor | Hit Δ (pp) | Recall Δ (pp) | MRR Δ | Wrong-scope Δ (pp) |
|---|---:|---:|---:|---:|
| `registry_chunking` vs `dense_baseline` | +0.000 | -0.208 | -0.0094 | -0.037 |
| `registry_lexical_rrf` vs `registry_chunking` | +0.000 | +0.625 | -0.0635 | +1.595 |
| `registry_reranking` vs `registry_lexical_rrf` | +0.000 | +0.000 | +0.0829 | -1.183 |
| `registry_enrichment` vs `registry_reranking` | +0.000 | +0.000 | +0.0010 | +0.489 |
| `registry_expansion` vs `registry_enrichment` | +0.000 | +0.000 | +0.0000 | +0.000 |

## Leave-one-component-out comparisons

Each ablation is compared with the fully combined `registry_expansion` arm. Rate deltas are percentage points; MRR is the raw difference. `ablation_no_reranker` also makes the expansion score gate unavailable, so that ablation includes this declared dependency.

| Ablation vs `registry_expansion` | Hit Δ (pp) | Recall Δ (pp) | MRR Δ | Wrong-scope Δ (pp) |
|---|---:|---:|---:|---:|
| `ablation_no_chunking` | +0.000 | -0.417 | +0.0052 | +0.037 |
| `ablation_dense_only` | +0.000 | +0.000 | -0.0083 | -0.425 |
| `ablation_no_reranker` | +0.000 | -1.250 | -0.0485 | +1.433 |
| `ablation_no_enrichment` | +0.000 | +0.000 | -0.0010 | -0.489 |
| `ablation_no_expansion` | +0.000 | +0.000 | +0.0000 | +0.000 |

## Timing and token-budget checks

Timings are per-query stage p50 / p95. Retrieval, enrichment, and expansion timings come from the completed source run; context-packing timings were measured again by the repack. Because these values span the original execution and a packing-only replay, no combined end-to-end latency is reported. A dash means that stage was disabled.

| Arm | Retrieval (s) | Enrichment (ms) | Expansion (s) | Repacked context packing (ms) |
|---|---:|---:|---:|---:|
| `dense_baseline` | 0.12 / 0.16 | — | — | 1.7 / 2.1 |
| `registry_chunking` | 0.12 / 0.16 | — | — | 1.7 / 2.1 |
| `registry_lexical_rrf` | 0.13 / 0.17 | — | — | 2.6 / 3.9 |
| `registry_reranking` | 21.50 / 23.27 | — | — | 2.5 / 4.1 |
| `registry_enrichment` | 22.89 / 34.14 | 0.0 / 0.1 | — | 2.9 / 4.2 |
| `registry_expansion` | 33.29 / 37.00 | 0.1 / 0.1 | 26.13 / 36.48 | 1.2 / 1.7 |
| `ablation_no_chunking` | 21.21 / 27.58 | 0.1 / 0.2 | 18.73 / 22.48 | 1.4 / 1.6 |
| `ablation_dense_only` | 11.83 / 19.17 | 0.0 / 0.1 | 11.62 / 17.97 | 1.2 / 1.7 |
| `ablation_no_reranker` | 0.15 / 0.28 | 0.0 / 0.0 | 0.00 / 0.00 | 1.2 / 1.6 |
| `ablation_no_enrichment` | 18.69 / 20.01 | — | 16.96 / 19.56 | 1.2 / 1.7 |
| `ablation_no_expansion` | 18.80 / 19.82 | 0.0 / 0.1 | — | 2.8 / 4.2 |

The request budget is 32,768 tokens with 2,048 reserved for output and 256 for format overhead, leaving 30,464 for the serialized system/user messages. Across 880 traces, full-message tokens were p50 29,809.5, p95 30,413, and max 30,464. Packed-context payload tokens were p50 28,435, p95 29,110, and max 29,297. Budget violations: 0; trace/payload context-ID mismatches: 0.

## Unmeasured evaluation stages

- Answer generation status: `not_run`. Answer support, citation precision, no-answer correctness, and generation failure metrics are unavailable because no answer generator or reviewed answer/citation judgments were supplied.
- Conversation evaluation: `not_run` (`conversation_metrics` is null); no reviewed conversation fixture was supplied.
- Retrieval metrics above do not support claims about generated-answer quality.
