# Task 5 Report: Local BGE Model Adapters

## Result

Implemented `BgeM3Embeddings`, `BgeM3Reranking`, and `LocalModelPaths` using the pinned optional dependency `FlagEmbedding==1.4.2`. The adapters route scalar inputs to query encoding and list inputs to corpus encoding, preserve document metadata and identity, validate finite vectors and scores, and keep reranker ties stable.

Production model loading requires explicit local paths and process-start offline flags. Before constructing FlagEmbedding, the adapter verifies the environment, Hugging Face Hub and Transformers offline states, and cached Hub session adapters. An online-initialized process fails closed with instructions to start a fresh offline process. Constructor errors identify the model ID and local path while preserving the original cause. Preflight checks required asset presence and valid JSON configuration; it does not claim to prove model loadability.

## TDD and review

- Initial RED: adapter module absent (`1 failed, 19 skipped`).
- First GREEN: 20 synthetic fake-backend tests; later expanded to 21 for missing shard detection.
- Sol Medium review found that changing offline flags after import did not update Transformers' cached state or an existing Hub session. Added subprocess tests for stale online state rejection and fresh offline state validation.
- Review also found that file presence was described as full model completeness. Documentation now distinguishes presence checks from loadability, and a synthetic corrupt-model test verifies actionable errors with preserved causes.
- Sol Medium re-review approved with no remaining blocking findings.

## Verification

- `NLTK_DATA=/tmp/kotaemon-nltk-data uv run pytest libs/kotaemon/tests/test_knowledge_eval_local_models.py -q` — 24 passed.
- Ruff — passed.
- `git diff --check` — passed.
- `uv lock --check --offline` — passed (440 packages resolved).

Commit: `53e982ec feat: add local bge evaluation adapters`.

## Dependency and scope notes

The optional extra is scoped to the `kotaemon` package and is not part of default runtime dependencies. Lock resolution adds nine packages and changes `fsspec` from 2025.9.0 to 2025.3.0 because the selected `datasets==4.0.0` requires `fsspec<=2025.3.0`; FlagEmbedding 1.4.2 requires `datasets>=2.19.0`. The lock format moves from revision 1 to 3 and adds artifact upload-time metadata, causing substantial regenerated lock churn; current uv 0.12.9 and uv 0.8.22 both produced this format.

All tests used synthetic files and fake constructors. No model weights were downloaded, no private corpus files or derived artifacts were accessed, and no retrieval metrics were run. Loading and inference with actual local model weights remain unverified until the user-approved experiment stage.
