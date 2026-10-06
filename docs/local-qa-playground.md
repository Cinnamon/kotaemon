# Local snapshot QA playground

The standalone workbench opens one approved frozen snapshot and builds an
isolated retrieval index in memory through the shared knowledge runtime. It
uses local BGE-M3 embeddings over the baseline token chunks, a local
cross-encoder when its verified weights are available, and an ephemeral FTS5
lexical route. The runtime gathers up to 20 vector candidates (plus lexical
candidates when FTS5 is available), selects the seed window from the top five
distinct sources, then considers authorized neighboring chunks. The evidence
panel labels these limits as chunk seed K=20 and source K=5. If FTS5 or the
local reranker is unavailable, the UI reports that degraded route and keeps
the usable retrieval paths.

The workbench keeps bounded user-question history in session memory: at most
three recent turns and 1,024 counted tokens. Retrieval and answer generation can
use this history; assistant answers and evidence are not added to it. The
optional “Resolve follow-ups with recent user turns” control asks the local
Ollama model to rewrite a follow-up query. Clear resets the history. Before
generation, complete evidence cards are packed against the configured model
budget. A matching cached Qwen tokenizer is used when present; otherwise the
client counts UTF-8 bytes and labels the budget estimated. If no seed card fits,
generation is skipped. The client also checks the final rendered system and
user messages against the budget before sending them. Route status, fusion IDs,
reranking, expansion, packing, and omitted-card diagnostics appear with the
evidence. The answer panel cites only cards in that final packed context.

## Prerequisites

- Use an approved snapshot under your Git-ignored local root and the local
  embedding and reranker model directories associated with that root.
- Install and start Ollama on the local machine, then download the configured
  model before asking questions:

  ```bash
  ollama pull qwen2.5:3b
  ```

The UI reports the snapshot version and configured generation model when it
starts. It binds to `127.0.0.1`; Gradio sharing and automatic browser opening
are disabled. The Ollama endpoint accepts only an HTTP loopback IP address.

## Launch

Run this from the repository root, replacing each placeholder with a path on
your machine:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m ktem.local_qa_playground \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker \
  --ollama-endpoint http://127.0.0.1:11434 --model qwen2.5:3b \
  --server-port 7860
```

Enter the current question for each Ask action. The evidence panel shows source
rank, candidate chunk rank, relative source label, locator, score, and the exact
retrieved chunk text. Clear removes the question, answer, evidence, and
session-local user-question history from the page.

When follow-up resolution is enabled and a recognized follow-up has recent user
turns, the current question and bounded history may be sent to the local Ollama
process for query rewriting before retrieval, even if no evidence is found.
Answer generation runs only for a non-empty question when at least one seed fits
the budget; it sends the current question, bounded user-question history, and
exactly the packed evidence cards over the loopback HTTP interface. Streaming
and non-streaming requests use the same packed cards. Empty questions, searches
without evidence, and requests where no seed fits skip answer generation.
Generation failures display an error instead of a generated answer. The
workbench does not write questions, answers, evidence, or traces to the snapshot
or its own files. It does not control Ollama's process-memory or retention
behavior.

## Combination, ablation, and conversation evaluation

The local-only evaluator compares the fixed dense, lexical/RRF, reranking,
query-enrichment, and evidence-expansion arms, followed by leave-one-component-
out arms. It uses the same reviewed snapshot and verified model manifest for
every arm. Candidate recall is measured on the pre-rerank fused pool, capped at
40 chunk IDs after each route contributes up to 20 candidates. Source metrics
use the top five distinct sources after reranking. Final-context anchor coverage
uses only chunk IDs in the exact packed payload.

The tracked [v3 aggregate validation report](superpowers/reports/agent-rag-pipeline-v3-validation.md)
contains the measured 11-arm aggregates, comparison denominators, stage timing
summaries, integrity checks, and the limits of the retrieval-only run. Query,
source, evidence, and per-query trace data remain in the ignored local run
directory.

Run it from the repository root with absolute paths under one Git-ignored local
root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli combination-experiment \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker-v2-m3 \
  --artifact-dir /path/to/git-ignored/local-root/runs/v3-combination
```

To include multi-turn retrieval, add the optional flag with a separately
reviewed fixture file stored under that same local root:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli combination-experiment \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker-v2-m3 \
  --artifact-dir /path/to/git-ignored/local-root/runs/v3-combination \
  --conversation-fixture /path/to/git-ignored/local-root/conversation-fixtures/reviewed-v1.json
```

The CLI verifies the approved snapshot sidecar and model-manifest digests, then
rejects path escapes, symlinked inputs, and an existing artifact destination.
The conversation fixture has its own strict schema and digest. This v2 snapshot
does not contain reviewed logical-path or entity metadata, so non-root path
constraints and metadata filters are rejected instead of being ignored.

Before retrieval starts, the CLI prints a hidden staging directory under
`local/runs/`. The checkpoint there binds the snapshot, reviewed judgments and
anchors, exact model-manifest bytes, retrieval configuration, arm definitions,
and ordered query IDs. Each completed query is saved with atomic trace and
summary files plus digests. If the process stops, pass the same inputs and the
printed staging path to `resume-combination-experiment`; it verifies every
fingerprint, query binding, digest, and path before skipping saved queries.
Only an uncommitted in-flight query is retried. A changed snapshot, gold file,
model manifest, configuration, symlink, or unlisted file makes resume fail
before query inference.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli resume-combination-experiment \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker-v2-m3 \
  --artifact-dir /path/to/git-ignored/local-root/runs/v3-combination \
  --staging-dir /path/to/git-ignored/local-root/runs/.v3-combination.staging-<id>
```

The evaluator never calls an answer generator. Answer support, citation
precision, no-answer correctness, and model-failure metrics remain null with a
`not_run` reason; a private local judgment template is written for later human
review. A matching cached Qwen tokenizer is used to pack context when available.
Otherwise the report marks its UTF-8 byte counter as an estimate. If FTS5 is
unavailable, route status records the lexical route limitation. The BGE model
directories remain required and manifest-verified for a complete run.
Per-query traces, prompts, and packed source text are stored only under the
ignored run directory; the tracked validation report contains aggregate checks
only.

The packer budgets the same serialized system and user messages that the final
request gate checks, after reserving output and format tokens. When an already
completed run has authenticated trace rankings but its packing-policy version
needs to be refreshed, use `repack-combination-experiment` to create a new
artifact directory. It verifies the source checkpoint, snapshot, gold,
model-manifest, arm-configuration, and trace digests before replaying packing
and aggregate metrics. It does not rerun retrieval or embedding/reranking
inference; it rejects incomplete or mismatched source staging directories.

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m kotaemon.indices.knowledge.evaluation.local_cli repack-combination-experiment \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker-v2-m3 \
  --source-staging-dir /path/to/git-ignored/local-root/runs/.v3-combination.staging-<id> \
  --artifact-dir /path/to/git-ignored/local-root/runs/v3-combination-repacked
```
