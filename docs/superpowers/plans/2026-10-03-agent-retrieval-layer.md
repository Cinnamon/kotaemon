# Agent Knowledge Retrieval Layer: Phase 3–6 TDD Plan

**Status:** design proposal for the remaining work after ingestion Task 4. Implement tasks in order. For each task, a GPT-6 Luna Max implementer writes a failing behavior test, records RED, makes the smallest change, records GREEN, and reports the commit and evidence. A separate GPT-6 Sol Medium reviewer checks the committed diff against the task contract before the next task begins. The parent coordinates design and final end-to-end review.

## Evidence and corrected premises

- `VectorRetrieval` already owns vector/text/hybrid recall, reranking, and final top-k. It only calls `doc_store.query` in text/hybrid mode when `scope` is truthy. Its hybrid merge currently compares a `Document` object to vector ID strings, so duplicate IDs can enter the candidate list. Rerankers are configurable; Cohere is not guaranteed.
- `DocumentRetrievalPipeline` resolves selected file IDs through the SQL Index table and returns `[]` when none are selected. Preserve that UI contract. An Agent-facing global entry point must be explicit and must not be achieved by removing this guard.
- The SQL `Source.note["knowledge"]` contains file-level `source_type`, `virtual_path`, `document_name`, and `entity` for newly indexed files. `Index` maps a source ID to chunk IDs. Old `Source` and chunks can lack these fields. `Source.user` and the index's `private` setting matter for source visibility.
- The vector adapter now stores chunk metadata. Chroma projects lists/maps, including `entity`, into JSON strings; the docstore has the original structures. Use Source/Index mapping or docstore metadata for deterministic scope resolution, and use vector filters only for supported scalar fields. Do not assume every backend honors `node_ids` or `filters` identically.
- A global lexical branch is not presently wired through `VectorRetrieval`; `InMemoryDocumentStore.query` returns `[]`, while LanceDB/Elasticsearch implement full-text search. Report actual lexical availability per backend. A global hybrid call cannot honestly be described as BM25+vector on every backend.
- `PrepareEvidencePipeline` currently token-splits a combined HTML context and retains the first split, which can cut a chunk. `SimplePipeline.retrieve` deduplicates IDs before calling that pipeline; `CitationPipeline` extracts exact quote substrings from the evidence, and citation display maps them against retrieved documents. Preserve original text, IDs, `file_name`, and `page_label` through context construction.
- This repository has no enterprise Wiki connector, enterprise corpus, or labeled judgments. Synthetic results test routing and metric mechanics only; they cannot establish production recall improvement.

## Binding constraints

- Do not change Kotaemon's `Document` or `RetrievedDocument` schema.
- Store canonical metadata in `Document.metadata` and preserve loader-specific keys such as `file_id`, `file_path`, `page_label`, and `sheet_name`.
- Supported source types are `wiki`, `markdown`, `pdf`, `faq`, `code`, `ppt`, `excel`, and `other`.
- `virtual_path` is a logical namespace; never expose a temporary absolute upload path as the default logical path and never access the filesystem through `virtual_path`.
- Keep the existing configured `TokenSplitter` as fallback for unsupported source types, malformed structure, parser failures, unsupported languages, missing slide boundaries, and oversized semantic units.
- Do not add a mandatory parser dependency, Wiki connector, parallel RAG pipeline, vector database, or schema migration.
- Older chunks without canonical metadata remain valid. New metadata is populated on new and reindexed chunks only.
- Preserve the existing ktem file selector, storage lifecycle, and citation compatibility.
- Scope is an *intersection* with caller-selected/visible source IDs. Never let a planner broaden a caller's source boundary. Do not log full private chunk text by default.

## Stable interfaces

The implementation may adjust names to fit current component conventions, but keep these contracts explicit:

```python
@dataclass(frozen=True)
class RetrievalPlan:
    query: str
    semantic_query: str
    source_types: tuple[str, ...] = ()
    virtual_paths: tuple[str, ...] = ()  # resolved real logical paths, no glob syntax
    metadata_filters: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""

class KnowledgeService:
    def search(self, query: str, *, path: str | None = None,
               source_types: list[str] | None = None,
               filters: dict | None = None, top_k: int = 10,
               allowed_source_ids: list[str] | None = None,
               trace: RetrievalTrace | None = None) -> list[RetrievedDocument]: ...
    def read(self, knowledge_id: str, *, allowed_source_ids: list[str] | None = None) -> Document | None: ...
    def list(self, path: str = "/", *, allowed_source_ids: list[str] | None = None) -> list[dict]: ...
```

`allowed_source_ids=None` means the caller explicitly selected the Agent/global API; `[]` means no accessible files and must return no results. File-index UI passes its selected IDs and retains its current empty-selection behavior. `read` accepts a stored chunk ID, resolves its Source relation, and checks visibility before returning it. `list` reports logical metadata and IDs only, never opens a local path. Reject unsupported arbitrary filter keys rather than silently weakening a caller's explicit constraint. A `RetrievalTrace` is an optional collector passed through the call; public return values stay compatible.

## Task 6 — Deterministic scope planner and catalog (Phase 3)

**Files:** new `libs/kotaemon/kotaemon/indices/knowledge/planning/{__init__,retrieval_plan,query_planner}.py`; new `libs/kotaemon/tests/test_knowledge_planner.py`. For SQL catalog: new `libs/ktem/ktem/index/file/knowledge_catalog.py`; new `libs/ktem/ktem_tests/test_knowledge_catalog.py`.

**Contract:** A catalog enumerates visible `Source` rows with `note["knowledge"]`, resolves exact logical path/source type/entity values to source IDs, and provides source-to-chunk IDs using existing `Index` relations. The planner takes a query and that catalog; it emits a high-confidence scope only for an unambiguous exact entity/path/document match, with token boundaries and normalized case where appropriate. For “张三实习期间做了什么工作？” and distinct 张三/李四/王五 paths, resolve only 张三; for ambiguous names, unknown names, or absent metadata, confidence is below threshold and the plan is global. `semantic_query` retains the original query unless a deterministic, tested rewrite is clearly safe. No LLM is required. The planner does not invent `person` from a file name as a guaranteed metadata field; it can record `person` only when that key exists in `entity` and matched exactly.

**TDD first:** tests for exact Chinese name and repository/path segment matching; false partial matches (`张三` vs `张三丰`), duplicate names in different branches, explicit path/source type intersection, missing/legacy note, empty catalog, malformed note, and private/allowed source visibility. Record a failing focused test before code. Use in-memory catalog unit fixtures and a small temporary SQL Source/Index fixture for adapter behavior.

**Acceptance:** The plan is serializable and deterministic; a valid high-confidence plan maps to actual source IDs, low confidence requests global search, `virtual_path` is never used for filesystem access, and no scope can include a Source outside the caller's visible set.

## Task 7 — Scoped hybrid execution in existing retriever (Phase 4)

**Files:** update `libs/kotaemon/kotaemon/indices/vectorindex.py`; add `libs/kotaemon/tests/test_knowledge_scoped_retrieval.py`; update `libs/ktem/ktem/index/file/pipelines.py`; add `libs/ktem/ktem_tests/test_knowledge_scoped_pipeline.py`. Keep SQL catalog from Task 6 as the single scope resolver.

**Contract:** Extend `VectorRetrieval.run` with an explicit optional scope/trace hook, reusing its embedding, existing docstore query, configured rerankers, and top-k. For a selected scope, map Source IDs to chunk IDs before entering `VectorRetrieval`; pass `ids=chunk_ids` to the vector branch and `doc_ids=chunk_ids` to lexical search. Apply post-retrieval ID/metadata filtering when the backend cannot guarantee filtering, after fetching an expanded candidate pool. Enforce scope after reranking too. Keep legacy no-plan invocation and existing `do_extend`, thumbnails, and extra-table behavior. Correct merge dedup by `doc_id`. Distinguish `scope=None` (global) from `scope=[]` (explicitly empty): empty returns `[]` before querying. Global calls may query lexical-capable docstores, but a backend returning no lexical results is recorded as unavailable rather than fabricated. A high-confidence planned scope with no candidates performs one bounded global retry, recorded as fallback; an ambiguous plan enters global directly. The global retry must still honor caller-visible IDs.

**TDD first:** fake vector/docstore implementations that capture query args and return out-of-scope bait; tests for both recall branches receiving the same chunk scope, duplicate ID once after merge, empty scope short circuit, filter-ignoring backend exclusion, candidate expansion, configured reranker ordering, zero-hit fallback, old metadata global retrieval, and no selected files in the UI pipeline. Add a small live in-memory vector fixture only if fake contracts leave backend behavior uncertain. Record RED and GREEN.

**Acceptance:** Zhang San's exact scope excludes Li Si/Wang Wu from selected evidence; global fallback can still find legacy records; no selected UI files still yields `[]`; vector-only backend is represented as such; the configured reranker remains in use. Do not claim backend-neutral BM25 unless the tested docstore implements it.

### Task 7 interface corrections and required regressions

The existing store interfaces use different argument names:

```python
BaseVectorStore.query(embedding, top_k=..., ids=chunk_ids, **kwargs)
BaseDocumentStore.query(query, top_k=..., doc_ids=chunk_ids)
```

`LlamaIndexVectorStore.query` maps `ids` to `VectorStoreQuery.node_ids`. Existing `VectorRetrieval` passes `doc_ids=scope` to vector queries, which is only forwarded as a backend kwarg and does not establish the node-ID constraint. Keep the public `scope` argument if needed for compatibility, but translate it to `ids=scope` for vector search and `doc_ids=scope` for full-text search. Never pass `doc_ids` to vector search.

Before implementation, tests must assert:

1. Vector-only and hybrid vector branches receive `ids=[...]` and never receive `doc_ids`; the hybrid docstore branch receives the same chunk IDs as `doc_ids`.
2. `scope=[]` returns immediately with no embedding, vector, or docstore calls in vector/text/hybrid modes; `scope=None` follows the global path.
3. A backend that ignores its ID/filter argument cannot leak out-of-scope results: post-filter by chunk ID before reranking and enforce again after reranking. A docstore fake that ignores `doc_ids` is covered too.
4. A test double verifies `ids` becomes `VectorStoreQuery.node_ids` at the LlamaIndex adapter boundary.
5. `doc_store.get(vs_ids)` may return documents in another order. Associate vector scores with IDs before fetching and reconstruct results by ID; test reverse-order `get`.
6. Hybrid merge de-duplicates by `doc_id` in deterministic order.
7. Global lexical search calls `doc_store.query(..., doc_ids=None)` only when available. An empty lexical result or unsupported backend is recorded as unavailable/empty, not claimed as BM25.
8. Any zero-hit retry remains inside the caller-visible/selected source IDs; empty caller visibility never broadens to global.
9. Worker-thread exceptions are captured and surfaced/recorded rather than silently treated as successful empty retrieval, while preserving usable results from the other branch when safe.

These requirements supplement Task 7's TDD and acceptance criteria; task ordering and file scope remain unchanged.

## Task 8 — Agent KnowledgeService and QA bridge (Phase 4)

**Files:** new `libs/kotaemon/kotaemon/indices/knowledge/retrieval/{__init__,knowledge_service}.py`; ktem assembly/adapter in `libs/ktem/ktem/index/file/pipelines.py` or a focused new `libs/ktem/ktem/index/file/knowledge_service.py`; update `libs/ktem/ktem/index/file/index.py` only if an explicit factory is needed; tests in `libs/kotaemon/tests/test_knowledge_service.py` and `libs/ktem/ktem_tests/test_knowledge_service_integration.py`.

**Contract:** Compose planner + catalog + existing `VectorRetrieval`; expose `search/read/list` without exposing vector/SQL implementation to the Agent caller. The existing file QA retriever calls `KnowledgeService.search` with its selected IDs; Agent callers use a separately named factory method with an explicit global/visible source catalog. Support explicit `path`, `source_types`, and supported scalar/entity filters as mandatory intersections with planned constraints. `read` checks Source relationship and authorization; `list` returns one row per visible logical source or immediate path child, documented consistently. A missing historical path can be listed by file name fallback, while `read` still works by ID. No new database table.

**TDD first:** service orchestration with stub planner/retriever/catalog, explicit filter precedence, selected-ID boundaries, read allowed/denied/missing, list normalized prefix semantics (`/team/a` does not include `/team/abc`), legacy source handling, and one QA adapter fixture proving the current selected-file path reaches the service and returns citation-ready `RetrievedDocument` objects.

**Acceptance:** A caller can search, read, and list through the service; current selected-file UI behavior is preserved; an Agent can request global visible search explicitly; no unauthorized source leaks through search/read/list.

## Task 9 — Diversity and whole-unit context budget (Phase 5)

**Files:** new `libs/kotaemon/kotaemon/indices/knowledge/retrieval/diversity.py`; update `libs/kotaemon/kotaemon/indices/vectorindex.py` at the post-rerank selection point; update `libs/kotaemon/kotaemon/indices/qa/format_context.py`; tests `libs/kotaemon/tests/test_knowledge_diversity.py` and `libs/kotaemon/tests/test_knowledge_context.py`.

**Contract:** Apply deterministic, bounded diversity after configured rerankers and before final top-k: exact ID/content dedup, high-overlap text dedup, and a configurable per-parent/section cap when enough alternate candidates exist. Preserve rank among survivors and do not starve a result set solely due to missing metadata. Reuse the existing MMR option if enabled; do not run a contradictory second MMR pass. Context builder accepts ranked documents, emits complete evidence units only, counts the complete formatted header + content against `max_context_length`, and skips a unit that cannot fit while considering later smaller units. Include escaped source name, logical path, section, and page when present. Keep table/image/chatbot modes and `Document(content=(mode, evidence, images))`. Ensure every included quote remains a substring of its source chunk for citation mapping. Expose selected chunk IDs and token use to optional trace.

**TDD first:** overlapping siblings, same parent cap, diverse alternates, legacy missing metadata, stable ranking, a single too-large first chunk followed by a fitting second chunk, exact token boundary, HTML-sensitive source fields, table/image mode, and citation substring matching. The budget test must assert no partial chunk and no broken HTML unit; use the current tokenizer or a deterministic injected token counter.

**Acceptance:** Duplicate chunks no longer dominate top-k in the synthetic fixture; context stays within budget and contains only complete evidence units; citation lookup still resolves cited text to the original `RetrievedDocument`.

## Task 10 — Structured trace through plan, recall, rerank, and context (Phase 6)

**Files:** new `libs/kotaemon/kotaemon/indices/knowledge/retrieval/trace.py`; update `libs/kotaemon/kotaemon/indices/vectorindex.py`, `libs/kotaemon/kotaemon/indices/qa/format_context.py`, `libs/ktem/ktem/index/file/pipelines.py`, and `libs/ktem/ktem/reasoning/simple.py` only at trace handoff points; tests `libs/kotaemon/tests/test_knowledge_trace.py`, `libs/ktem/ktem_tests/test_knowledge_trace_integration.py`.

**Contract:** Optional per-query trace records original query, plan, chosen source/chunk scope, explicit filters, fallback reason, lexical/vector candidate IDs and scores, merged IDs, per-reranker output scores/order, diversity exclusions, final chunk IDs, and context token usage/IDs. Add backend availability and errors as data. Pass collector explicitly rather than through global state, so concurrent queries remain isolated. Debug log or JSON export uses IDs/paths/scores by default; any full content requires explicit opt-in. Trace failure must not interrupt retrieval. Existing return types are unchanged.

**TDD first:** a fake full chain yields a complete JSON-serializable trace in order; concurrent collectors do not mix; disabled trace has same retrieval output; lexical-unavailable and scope-fallback reasons appear; an injected trace sink error leaves answer flow functional. Record RED and GREEN.

**Acceptance:** One synthetic query can be followed from original query through scope, both available recall branches, rerank, diversity, context, and citation mapping. Missing stages are explicitly marked unavailable rather than assigned invented scores.

## Task 11 — Offline evaluator and end-to-end report (Phase 6)

**Files:** new `libs/kotaemon/kotaemon/indices/knowledge/evaluation/{__init__,retrieval_eval}.py`; synthetic fixtures under `libs/kotaemon/tests/fixtures/knowledge_eval/`; new `libs/kotaemon/tests/test_knowledge_retrieval_eval.py`; one focused integration test under `libs/ktem/ktem_tests/`; report `docs/superpowers/reports/agent-knowledge-retrieval-evaluation.md`.

**Contract:** A versioned JSONL fixture declares query, expected relevant chunk/document IDs (or document/path labels resolved before scoring), and disallowed scope IDs. Define denominators: Hit@K = queries with ≥1 relevant result / queries with judgments; Recall@K = mean per-query relevant IDs retrieved / relevant IDs; MRR = mean reciprocal rank of first relevant result; Wrong-scope Rate = out-of-scope returned chunks / returned chunks on queries with scope labels. Report both macro and per-query values, K, number of judged queries, zero-result behavior, and ambiguous-query fallback. Run the exact same indexed synthetic fixture with planner disabled as baseline and enabled as new; keep the same embedding, rerankers, candidate count, and top-k. Store a complete machine-readable trace for one Zhang San query plus a readable stage narrative. Include a Citation quote lookup check, not an LLM answer correctness claim.

**TDD first:** metric arithmetic on hand-worked examples, multiple relevant IDs, duplicate result IDs, no result, no scope label, fixture validation failure, and identical baseline/new configuration test. Then run an end-to-end in-memory fixture representing Zhang San (RAG/API), Li Si (frontend), Wang Wu (automation) plus an ambiguous and a legacy source case. If the in-memory docstore lacks lexical search, state vector-only for that run or use a deterministic test lexical adapter and name it. Do not call synthetic metrics production recall.

**Acceptance:** `uv run pytest` focused new/affected tests pass; the report includes modified files/modules, old vs new pipeline, config defaults and compatibility, test commands/results, numeric baseline/new fixture metrics, one complete trace, and remaining limits. If fixture results fail to show the expected scoped improvement without recall loss, fix the implementation or state the observed result; do not massage judgments or omit failed queries.

## Final review gate

After Task 11 review, a GPT-6 Sol Medium reviewer checks the full committed diff and the end-to-end report against the original request. Run the focused suite and repository-required checks once on the final committed branch, inspect output before claiming completion, then present the branch for integration. Do not merge or publish merely because unit tests pass.
