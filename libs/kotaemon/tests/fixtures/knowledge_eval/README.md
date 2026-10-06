# Knowledge evaluation fixtures and local corpus

## Tracked default fixture

The public default fixture consists of the root-level `records.json` and
`judgments.jsonl`. It contains four synthetic sources (Zhang, Li, Wang, and a
legacy source), 11 chunks, and five synthetic judgments. There are no original
source documents in this fixture. Its content is synthetic data, not users'
documents.

The evaluation runner currently reads only these two root-level files. Keep
them as the unchanged default fixture; the runner does not discover or read
anything under `local/`.

## Optional local model runtime

Local BGE evaluation requires the `kotaemon[local-eval]` extra, pinned to
`FlagEmbedding==1.4.2`, and explicit local directories for `BAAI/bge-m3` and
`BAAI/bge-reranker-v2-m3`. Start the inference process with
`HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. Before importing
FlagEmbedding, the adapters check those environment flags, the Hub and
Transformers offline states, and the active Hub session's offline adapters. If
any library or session was initialized online, loading fails and asks for a
fresh offline inference process; the adapters do not change cached process
state after imports.

Preflight parses `config.json` and checks that the required tokenizer and
weight files are present. It cannot guarantee that the local tokenizer or
weights can be loaded. If model construction fails, the error identifies the
BAAI model ID and local path and recommends repairing or re-downloading that
snapshot. Inference never downloads models or sends queries and passages to a
remote service.

Adapter metadata includes model IDs, weight-file SHA-256 hashes, device,
FlagEmbedding version, and truncation lengths. Revision and cached/downloaded
origin are included only when supplied by the model-management flow; adapters
do not infer them from a directory.

## Local source drop-zone and draft outputs

Put user-provided original materials under
`libs/kotaemon/tests/fixtures/knowledge_eval/local/sources/`. A convenient
layout is one directory per stable source ID, with the original filename kept
inside it:

```text
local/
├── sources/
│   └── <source-id>/
│       └── <original-filename>
├── draft/
│   ├── inventory.json
│   └── v1/
│       ├── records.json
│       ├── judgments.jsonl
│       ├── anchors.jsonl
│       ├── manifest.json
│       └── REVIEW.md
├── snapshots/
├── models/
└── runs/
```

Run the local CLI from the repository root. Every generated path is resolved
under the selected `--local-root`, and command outputs are limited to its
`draft/`, `snapshots/`, `models/`, or `runs/` subdirectories. Symlink redirects
are rejected. A root inside the checkout must already be Git-ignored; temporary
roots outside the checkout are allowed.

```bash
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli inventory \
  --source-root libs/kotaemon/tests/fixtures/knowledge_eval/local/sources \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local

uv run python -m kotaemon.indices.knowledge.evaluation.local_cli prepare-review \
  --source-root libs/kotaemon/tests/fixtures/knowledge_eval/local/sources \
  --source-root-label libs/kotaemon/tests/fixtures/knowledge_eval/local/sources \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local \
  --version v1
```

The default `v1` preparation deterministically proposes 20–24 usable unique
documents. It covers supported file formats first, then content-derived topic
heading candidates, and fills remaining slots by stable source ID. It fails if
fewer than 20 usable documents are available. This selection is only a review
candidate: every topic candidate is marked unreviewed, and physical directory
names are retained only as provenance. Topic candidates omitted by the 24-source
cap are listed in `REVIEW.md` as unreviewed coverage gaps with their source IDs
and provenance paths. With explicit `--sample-id` selection, outside candidates
are labeled as not selected for that sample instead of as cap omissions.
`REVIEW.md` lists only the usable formats actually present in the selected
sample. `--sample-id` can select 20–24 explicit source IDs for
`v1`; the CLI parses the corpus and rejects the selection unless it yields at
least 20 chunk-backed unique documents and covers each format that is usable in
the corpus. The rejection lists unusable selected paths with their extraction
diagnostics. Use `--all-sources` with a non-v1 version for a small synthetic
review draft or a separate full-corpus review.

`prepare-review` creates chunk previews and extraction-quality summaries, but
does not make questions, relevance judgments, disallowed-source labels, or
query-linked anchors. The initial `judgments.jsonl` and `anchors.jsonl` are
empty by design. A person must author and review those files against the
source content before freezing. Source-level judgments use stable source IDs;
anchors identify query IDs, source hashes, and page, sheet, or section locations
plus normalized-text offsets and an evidence digest. Require at least one
anchor for every relevant query/source pair. Do not put per-arm chunk IDs in
the frozen gold.

## Review and fixed snapshots

Before freezing a snapshot, have a person review the content-derived source
topics, extracted text and chunk boundaries, source IDs, evidence anchors,
evaluation queries, relevant source IDs, and disallowed source IDs. Freeze a
completed draft with explicit approval identity and date:

```bash
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli freeze \
  --draft-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/draft/v1 \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local \
  --approved-by 'reviewer' \
  --approved-at 2026-10-04
```

The command validates the completed labels and anchors, refuses to overwrite an
existing version, and writes an `approval.json` sidecar containing the approver,
date, and SHA-256 of the exact snapshot manifest bytes. The frozen data lives in
`local/snapshots/<version>/`; the version 1 `manifest.json` schema remains
unchanged.

### Snapshot schema version 1

`records.json` uses the Task 2 schema version 1. Its source rows retain the
exact-byte SHA-256 `source_id`, a root-relative POSIX `relative_path`, byte
size, suffix, duplicate provenance, and reader/status fields. Duplicate-byte
rows may repeat a `source_id` only when they point to the one canonical
root-relative path and agree on source ID, SHA-256, and byte size. A source
unit and each chunk must map back to that canonical source path; chunk offsets
are half-open character offsets into the unit's `normalized_text`.

`topic_review_source_ids` must contain unique, valid SHA-256 IDs for selected
canonical source rows. A selected row may be `parsed` or `failed`; it need not
have a chunk because this list marks sources that still need topic review.
`topic_candidates` must resolve its source ID, unit ID, root-relative path, and
unit locator. A candidate may add locator detail such as a Markdown
`heading_line`, while preserving the unit locator fields and values. Source
references in quality diagnostics and excluded-input records must also map to
the corresponding source rows.

`judgments.jsonl` uses the existing retrieval-evaluation fixture schema version
1. Every judgment must have `judgment_level: "source"`; relevant, allowed,
and disallowed IDs refer to indexable canonical source IDs: the source row must
have `status: "parsed"` and at least one validated chunk. Failed,
not-selected, and chunkless source rows remain provenance only and cannot carry
judgment labels. A relevant ID must be in the allowed set when one is supplied,
and relevant/disallowed and
allowed/disallowed sets must not overlap.

`anchors.jsonl` is UTF-8 JSONL. Each row has exactly these fields:

```json
{
  "schema_version": 1,
  "id": "anchor-1",
  "query_id": "q-1",
  "source_id": "<64-character source SHA-256>",
  "source_sha256": "<64-character source SHA-256>",
  "unit_id": "<source-unit ID>",
  "locator": {"page_label": "1"},
  "char_start": 0,
  "char_end": 12,
  "evidence_sha256": "<SHA-256 of normalized_text[char_start:char_end]>"
}
```

Offsets are half-open and non-empty, and `evidence_sha256` hashes the exact
UTF-8 encoding of the selected normalized-text slice. The locator must equal
the referenced source unit's locator. Each anchor must name a known query and
canonical source relevant to that query. Every relevant query/source pair
needs at least one anchor. The span text is not duplicated in the anchor.

`manifest.json` is a JSON object with exactly these fields:

| Field | Version 1 meaning |
| --- | --- |
| `schema_version` | Manifest schema, integer `1`. |
| `snapshot_version` | Safe version name matching the snapshot directory name. |
| `schema_versions` | Exactly `{"records": 1, "judgments": 1, "anchors": 1}`. |
| `payload_sha256` | Exact map of the three payload filenames to lowercase SHA-256 of their exact bytes. |
| `review_status` | `approved` for evaluation or `draft` for inspection. |
| `review_date` | ISO `YYYY-MM-DD` approval date, or `null` for a draft. |
| `source_root` | Repository-relative root corresponding to the root passed to local preparation. |
| `source_provenance` | One ordered row per `records.json` source path: `source_id`, `repository_path`, and `sha256`. Each repository path must equal `source_root/relative_path`. |
| `parser_configuration` | Exact copy of `records.json`'s parser configuration. |
| `splitter_configuration` | Exact copy of `records.json`'s splitter configuration. |
| `counts` | Exactly `source_paths`, `documents`, `source_units`, `chunks`, `queries`, and `anchors`, matching the payloads; `documents` counts unique canonical sources with `status: "parsed"` and at least one chunk. |

For example, if `source_root` is
`libs/kotaemon/tests/fixtures/knowledge_eval/local/sources` and a record's
root-relative path is `<source-id>/<filename>`, its manifest path is
`libs/kotaemon/tests/fixtures/knowledge_eval/local/sources/<source-id>/<filename>`.
Never record machine-absolute paths. The payload hash map must contain exactly
`records.json`, `judgments.jsonl`, and `anchors.jsonl` with valid lowercase
64-character hex digests.

Before evaluating a snapshot, recompute the hashes for all three payload files
and compare them with the corresponding manifest entries before parsing. The
loader rejects symlink roots/payloads, missing or extra hash entries, unsafe
paths, source/unit/chunk mapping errors, invalid source-level judgments, and
invalid or incomplete anchors. Its snapshot fingerprint is SHA-256 of the exact
`manifest.json` bytes. A reviewed snapshot is immutable: any change to its
payloads, manifest, or documented source/loader/chunker inputs must be
published under a new `local/snapshots/<version>/` directory with an updated
manifest; do not overwrite an existing version. Task 7's freeze command enforces
the no-overwrite rule. The evaluation loader requires `review_status: "approved"`
by default; `require_reviewed=False` is only for inspecting a fully populated,
otherwise valid draft snapshot.

The synthetic fixture remains the runner's default. Local experiment runs must
explicitly select a reviewed snapshot path and enforce the hash check described
above.

## Local model manifest and run command

`download-models` first checks the Hugging Face cache in offline mode for each
fixed model ID. A cache hit is recorded as `cached`; only a miss triggers
revision resolution and download pinned to the resolved full commit SHA. The
command writes model copies beneath `local/models/` and publishes
`model-manifest.json` atomically after both model directories are complete.
The manifest records exact IDs (`BAAI/bge-m3` and
`BAAI/bge-reranker-v2-m3`), revisions, relative directories, sorted
weight-filename SHA-256 maps, a sorted SHA-256 map for every regular inference
asset, and `cached`/`downloaded` origin labels. The asset map includes
configuration, tokenizer, vocabulary, special-token, weight, and any other
regular model files. It excludes only Hugging Face download bookkeeping beneath
`.cache/huggingface/`. At run time the CLI checks the exact asset filenames and
hashes, so added, missing, or changed assets fail before model creation.

```bash
uv run python -m kotaemon.indices.knowledge.evaluation.local_cli download-models \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local
```

`run` accepts only an approved snapshot under `local/snapshots/`, explicit
model directories that match the single unambiguous model manifest, and all
model assets whose filenames and hashes still match that manifest. It also
requires the approval sidecar and checks that its approver/date and manifest
hash match. Before creating model instances or run artifacts, the CLI checks
the offline environment and Hub session. It copies the verified model manifest
into `local/runs/<snapshot-name>/model-manifest.json` and records its SHA-256 and
byte size in `artifact-manifest.json`. Run publication is atomic.

Start `run` in a fresh shell process with both offline flags set before Python
starts, for example:

```bash
env HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python -m kotaemon.indices.knowledge.evaluation.local_cli run \
  --snapshot libs/kotaemon/tests/fixtures/knowledge_eval/local/snapshots/v1 \
  --local-root libs/kotaemon/tests/fixtures/knowledge_eval/local \
  --embedding-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-m3 \
  --reranker-model-dir libs/kotaemon/tests/fixtures/knowledge_eval/local/models/bge-reranker-v2-m3
```

Do not freeze labels or run an experiment until the user has reviewed and
approved the candidate questions, judgments, scope labels, and evidence anchors.

## Local-data handling

Git ignores the entire `local/` directory as a convenience, so its contents
are not added to a PR by default. `.gitignore` is not a security boundary:
ignored files can still be force-staged or disclosed by other means. Do not
use `git add -f` for this data or publish original materials, drafts, or local
snapshots without explicit authorization.
