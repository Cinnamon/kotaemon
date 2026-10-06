# Local knowledge retrieval evaluation v2

Evaluation date: 2026-10-04

Frozen snapshot: v2

Snapshot fingerprint: `b9cee5c3d12d76c69ec04719bdc65b0b40c332f348b545560a4564c50ea5d6aa`

## Dataset and scoring

The frozen golden set contains 80 source-level questions over 22 documents, with 139 reviewed evidence anchors. The evaluator retrieves a candidate pool of 20 chunks and scores the first 5 distinct source documents. Hit@5, Recall@5, and MRR@5 are macro-averaged across all 80 questions. Wrong-scope@5 is the pooled share of returned distinct sources marked outside the question's allowed scope; lower is better. Its denominator varies because some queries return fewer than five distinct sources, so the table includes numerator and denominator.

Anchor coverage checks whether each reviewed evidence span is contained in a retrieved chunk for the same source, unit, and locator among the top five distinct sources. Its denominator is covered plus uncovered anchors; unresolved anchors are excluded. There were no unresolved anchors in this run.

## Experiment arms

Each arm changes one factor from the baseline:

- **Baseline:** token chunking at 1,024 tokens with 256 overlap; dependency-free `hashed_feature_v1` embeddings (256 dimensions); no reranker.
- **Chunking:** registry-selected chunk strategy by source type; same hashed embeddings and no reranker.
- **Embedding:** local `BAAI/bge-m3` embeddings; same token chunking and no reranker. Model revision: `5617a9f61b028005a4858fdac845db406aefb181`.
- **Reranker:** local `BAAI/bge-reranker-v2-m3` reranks the exact same baseline vector candidate list; same baseline chunking and embeddings. Model revision: `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.

Both model directories were verified from the local model manifest. Inference ran with Hugging Face and Transformers offline flags; no query or source text was sent to a remote model service.

## Results

All deltas are absolute percentage points versus the baseline. Positive deltas improve Hit, Recall, or MRR; negative deltas improve Wrong-scope.

| Arm | Hit@5 (Δ) | Recall@5 (Δ) | MRR@5 (Δ) | Wrong-scope@5 (n/N; Δ) |
|---|---:|---:|---:|---:|
| Baseline | 75.00% (—) | 67.08% (—) | 47.21% (—) | 12.02% (44/366; —) |
| Chunking | 86.25% (+11.25 pp) | 77.50% (+10.42 pp) | 62.60% (+15.40 pp) | 9.41% (35/372; −2.61 pp) |
| Embedding | 100.00% (+25.00 pp) | 99.17% (+32.08 pp) | 92.44% (+45.23 pp) | 2.29% (7/306; −9.73 pp) |
| Reranker | 82.50% (+7.50 pp) | 76.88% (+9.79 pp) | 79.38% (+32.17 pp) | 9.29% (34/366; −2.73 pp) |

| Arm | Anchor coverage | Covered / eligible | Unresolved |
|---|---:|---:|---:|
| Baseline | 36.69% | 51 / 139 | 0 |
| Chunking | 33.09% | 46 / 139 | 0 |
| Embedding | 86.33% | 120 / 139 | 0 |
| Reranker | 42.45% | 59 / 139 | 0 |

## Interpretation and limits

The embedding arm has the strongest measured scores across the four primary metrics and anchor coverage. Chunking and reranking also improve the primary metrics over this control, although their evidence-anchor coverage is lower than the embedding arm. The reranker result isolates reranking over the baseline candidate list; it does not measure reranking on top of the BGE-M3 embedding arm. Combined configurations and interaction effects were not evaluated.

The baseline is the experiment's dependency-free hashed-feature control, not a measurement of a deployed production configuration. These are descriptive results on this fixed 80-question set; no confidence interval or significance test was run.

The complete per-query report, traces, approval snapshot, and verified model manifest remain under the Git-ignored `libs/kotaemon/tests/fixtures/knowledge_eval/local/` tree. The run artifact sidecar lists 322 artifacts, and every listed size and SHA-256 digest was verified. This tracked summary contains aggregate metrics only.
