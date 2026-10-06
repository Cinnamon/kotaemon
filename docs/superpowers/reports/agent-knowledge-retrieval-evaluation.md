# Agent Knowledge Retrieval Evaluation

> All metrics in this report are **synthetic fixture evaluation**. They do not
> estimate production recall, answer quality, or general retrieval performance.

## Scope and pipeline comparison

The comparison uses five version 1 JSONL judgments over four indexed synthetic
Sources and eleven chunks. Corpus text and logical metadata are stored in
[`records.json`](../../../libs/kotaemon/tests/fixtures/knowledge_eval/records.json);
canonical query judgments are stored separately in
[`judgments.jsonl`](../../../libs/kotaemon/tests/fixtures/knowledge_eval/judgments.jsonl).
All judgment IDs were validated against the fixture's immutable Source/chunk
catalog before either arm ran. Both arms indexed the same corpus once and ran
the same queries in the same order. The integration harness asserts that no
relevance-label key enters indexed chunk metadata or either shared run config.

The baseline injects an identity/global planner into `KnowledgeService`; the
planned arm injects `QueryPlanner`. Both call `KnowledgeService.search`, which
applies caller visibility and explicit path/type/metadata constraints before
the existing `VectorRetrieval` stage. The planner can narrow that mandatory
scope. An ambiguous or legacy query stays global within the visible catalog.
The existing file UI behavior is unchanged: an empty selected-source list
returns no results. A supplemental check exercises an empty allowlist through
both compared services without a vector-store call. No production planner
switch or schema change was added.

| Setting | Baseline | Planned |
| --- | --- | --- |
| Planner | identity/global | `QueryPlanner` |
| Retrieval mode | vector | vector |
| Top K | 5 | 5 |
| Configured candidate K | 5 | 5 |
| Observed candidate K per judged query | 5 for all five queries | 5 for all five queries |
| First-round multiplier / `do_extend` | 1 / false | 1 / false |
| Rerankers | none | none |
| Diversity cap / MMR | disabled (`null`) / false | disabled (`null`) / false |
| Context budget | 4096 characters (`len` counter) | 4096 characters (`len` counter) |
| Vector backend | deterministic synthetic cosine adapter | same indexed adapter |
| Document store | `InMemoryDocumentStore` | same store |
| Lexical capability | `supports_lexical_search=False`; lexical branch not used | same |

The fixture uses a fixed hashed character-bigram embedding and cosine ranking.
It is a deterministic synthetic vector adapter, not a production embedding or
backend. Retrieval is vector-only: the trace records lexical as `not_used`,
with no BM25 results or scores. The comparison has no reranker and no diversity
selection. Both configs match in every field except planner identity. K=5
shared config fingerprint:

```text
6ba28c30261f3f5588e5fbb241244ec7c13015baea8c2ac1bd1c12984cb5b85c
```

Fixture SHA-256:

```text
4150e95b07a1778db3dca01f816a31708c214f2ca4a9600178f0d310ce968998
```

The only comparison variable is deterministic query-scope planning. The
semantic query is passed through unchanged. `QueryPlanner` narrows the Zhang
query from global retrieval to `source-zhang`; the Li query has the same
explicit path/type/metadata filter in both arms; Wang, ambiguous-team, and
legacy-source remain global under the current planner.

## Supplemental empty-authorization parity

The empty-allowlist check runs after the five judged queries, using the same
indexed fixture and baseline/planned service instances. Both instances receive
the unjudged query `张三在哪实习？` with `allowed_source_ids=[]`; both return no
documents, and the vector query log is unchanged for each call. Each Task 10
trace records `search_status=not_run`, `no_search_reason=empty_visibility`, and
a `no_search` event with reason `empty_visibility`.

This check is supplemental and is not a sixth judgment. Both arms remain at
five judged queries, and their metrics, candidate observations, and config
fingerprint stay unchanged. The details are stored under
[`authorization_parity.empty_allowlist`](artifacts/agent-retrieval-evaluation.json).

## K=5 synthetic fixture results

Hit@5, Recall@5, and MRR@5 are macro means over all five judged queries,
including any zero-result query. Wrong-scope@5 is pooled over unique returned
chunks separately within each query, then summed across the three queries with
non-null `disallowed_source_ids` labels. A scope-labeled query with fewer than
five returned chunks contributes only its actual unique results. Queries with
a null scope label do not enter the numerator or denominator.

| Metric | Identity/global baseline | Planned | Planned − baseline |
| --- | ---: | ---: | ---: |
| Hit@5 | 1.0000 | 1.0000 | 0.0000 |
| Macro Recall@5 | 0.9333 | 0.9333 | 0.0000 |
| MRR@5 | 0.7000 | 0.8000 | +0.1000 |
| Wrong-scope@5 | 0.3077 (4/13) | 0.1818 (2/11) | −0.1259 |

Hit@5 and macro Recall@5 did not improve at K=5. MRR@5 improved by 0.1000,
and pooled Wrong-scope@5 fell by 0.1259. The Zhang query accounts for the
between-arm ranking and scope change: at K=5 the global baseline already
retrieves both judged Zhang chunks, while `QueryPlanner` ranks a relevant
chunk first and excludes other Sources from that query's candidate scope. The
Wang query remains global and retains its two wrong-scope chunks in both arms.
No query text, judgment, source metadata, or corpus text was changed to create
these outcomes.

The per-query table reports every judgment and the returned unique top-K IDs.
Each metric tuple is Hit / Recall / reciprocal rank / wrong-scope count and
rate; `—` means the query has no scope label, so wrong-scope is undefined.

| Query ID | Baseline top-5 IDs | Baseline H / R / RR / wrong-scope | Planned top-5 IDs | Planned H / R / RR / wrong-scope | Planned route |
| --- | --- | --- | --- | --- | --- |
| `zhang-internship` | `chunk-li-zhang-question`, `chunk-zhang-rag`, `chunk-li-wang-question`, `chunk-zhang-api`, `chunk-zhang-li-question` | 1 / 1 / 0.5 / 2/5 = 0.4 | `chunk-zhang-rag`, `chunk-zhang-api`, `chunk-zhang-li-question` | 1 / 1 / 1 / 0/3 = 0 | scoped to `source-zhang` |
| `li-frontend` | `chunk-li-frontend`, `chunk-li-wang-question`, `chunk-li-zhang-question` | 1 / 1 / 1 / 0/3 = 0 | `chunk-li-frontend`, `chunk-li-wang-question`, `chunk-li-zhang-question` | 1 / 1 / 1 / 0/3 = 0 | explicit path/type/metadata filter shared by both arms |
| `wang-automation` | `chunk-li-wang-question`, `chunk-wang-automation`, `chunk-wang-team-tech`, `chunk-wang-li-question`, `chunk-li-zhang-question` | 1 / 1 / 0.5 / 2/5 = 0.4 | `chunk-li-wang-question`, `chunk-wang-automation`, `chunk-wang-team-tech`, `chunk-wang-li-question`, `chunk-li-zhang-question` | 1 / 1 / 0.5 / 2/5 = 0.4 | global; wording not resolved by current planner |
| `ambiguous-team` | `chunk-li-wang-question`, `chunk-wang-team-tech`, `chunk-zhang-rag`, `chunk-li-zhang-question`, `chunk-zhang-api` | 1 / 2/3 / 0.5 / — | `chunk-li-wang-question`, `chunk-wang-team-tech`, `chunk-zhang-rag`, `chunk-li-zhang-question`, `chunk-zhang-api` | 1 / 2/3 / 0.5 / — | global for ambiguous query |
| `legacy-source` | `chunk-legacy-api`, `chunk-legacy-token`, `chunk-zhang-li-question`, `chunk-zhang-rag`, `chunk-zhang-api` | 1 / 1 / 1 / — | `chunk-legacy-api`, `chunk-legacy-token`, `chunk-zhang-li-question`, `chunk-zhang-rag`, `chunk-zhang-api` | 1 / 1 / 1 / — | global; legacy Source has no canonical planner metadata |

For pooled Wrong-scope@5, baseline has 4 wrong chunks out of 13 unique returned
chunks across Zhang (2/5), Li (0/3), and Wang (2/5). Planned has 2 out of 11
across Zhang (0/3), Li (0/3), and Wang (2/5). The denominator changes because
the planned Zhang scope returns the three chunks from its Source; the Li and
Wang query result counts remain three and five. The two unlabeled queries do
not enter this pooled calculation.

## Historical K=2 comparison

The first evaluation run used K=2. This is preserved as history and is not
compared directly with K=5 to claim a planner effect; the fair comparison for
each K is baseline versus planned at that same K.

| Metric | K=2 baseline | K=2 planned | Planned − baseline |
| --- | ---: | ---: | ---: |
| Hit@2 | 1.0000 | 1.0000 | 0.0000 |
| Macro Recall@2 | 0.7667 | 0.8667 | +0.1000 |
| MRR@2 | 0.7000 | 0.8000 | +0.1000 |
| Wrong-scope@2 | 0.3333 (2/6) | 0.1667 (1/6) | −0.1667 |

The archived machine-readable K=2 pair and Zhang trace are
[`agent-retrieval-evaluation-k2.json`](artifacts/agent-retrieval-evaluation-k2.json)
and
[`agent-retrieval-zhang-trace-k2.json`](artifacts/agent-retrieval-zhang-trace-k2.json).
Their matching K=5 canonical outputs are
[`agent-retrieval-evaluation.json`](artifacts/agent-retrieval-evaluation.json)
and
[`agent-retrieval-zhang-trace.json`](artifacts/agent-retrieval-zhang-trace.json).

## Zhang trace and citation lookup

The complete default-redacted K=5 trace is
[`agent-retrieval-zhang-trace.json`](artifacts/agent-retrieval-zhang-trace.json).
The paired metrics, observations, candidate counts, and frozen resolved
judgments are in
[`agent-retrieval-evaluation.json`](artifacts/agent-retrieval-evaluation.json).
The trace records `candidate_k=5`, the original query
`张三实习期间做了什么工作？`, and a plan whose `semantic_query` is byte-for-byte
the original query. The plan resolves exact `person=张三` metadata to
`source-zhang` at confidence 1.0. The visible and mandatory scope contains all
four fixture Sources; the planned chunk scope contains the three Zhang chunks.

One vector recall attempt runs with observed `candidate_k=5`, returning the
three available chunks in that scoped Source: `chunk-zhang-rag` (0.3015),
`chunk-zhang-api` (0.0711), and `chunk-zhang-li-question` (0.0000). Lexical is
`not_used`; there are no lexical candidates, reranker outputs, or fallback
attempts. Merge and diversity keep those same three IDs. Evidence construction
retains all three chunks and records 496 characters against the 4096-character
budget. The default trace contains IDs, logical paths, scores, and stages, with
no full chunk text.

Citation lookup used the literal synthetic quote `负责构建检索 API`. It appears
in the evidence context; `AnswerWithContextPipeline.match_evidence_with_context`
returned span `[17, 27)` for `chunk-zhang-rag`, and slicing that span from the
original returned chunk produced the same quote. This checks string-to-source
mapping only; no LLM answer was generated or evaluated.

## Verification and limits

Task 13's integration assertions were written before changing the harness from
K=2. The focused comparison first failed as expected because both arms still
made five candidate requests of size 2. After the service retriever, request,
shared config, and `compare_runs` value were set from one K=5 value, the new
assertions passed. Pure scorer and integration test results, static checks, and
the detailed RED/GREEN record are in
[`task-13-report.md`](../../../.superpowers/sdd/task-13-report.md). The Task 11
scorer design and initial K=2 evaluation history remain in
[`task-11-report.md`](../../../.superpowers/sdd/task-11-report.md).

The fixture is synthetic and small; it contains no enterprise Wiki corpus or
human-labeled production judgments. Its cosine adapter uses character bigrams,
not the configured production embedding or reranker. QueryPlanner did not
scope the Wang wording, and ambiguous/legacy queries entered global retrieval.
No LLM answer quality, production citation precision, lexical/BM25 behavior, or
general retrieval performance is measured here.
