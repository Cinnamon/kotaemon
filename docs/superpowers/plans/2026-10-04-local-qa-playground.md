# Local Golden Snapshot QA Playground Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only Gradio workbench where the user can ask arbitrary questions against the approved v2 snapshot and inspect the generated answer and exact retrieved evidence.

**Architecture:** Load and validate the approved snapshot once, then build the existing in-memory vector retrieval bundle with baseline token chunks and local BGE-M3. For each independent question, retrieve 20 vector candidates, rank distinct sources by first occurrence, show all retrieved chunks belonging to the top five sources, and pass only those displayed chunks to a loopback-only Ollama generator.

**Tech Stack:** Python 3.10+, existing Kotaemon retrieval abstractions, BGE-M3 local embedding adapter, `urllib`, Gradio 4, pytest, `uv` workspace.

## Global Constraints

- Read only the approved snapshot and local model assets; do not change the snapshot, gold questions, anchors, metric reports, run artifacts, or persistent Kotaemon index.
- Build and embed the corpus once at startup; embed only each submitted query after startup.
- Use exactly the snapshot's approved baseline splitter: `TokenSplitter(chunk_size=1024, chunk_overlap=256, separator="\n\n", backup_separators=["\n", ".", " ", "\u200b"])`.
- Use local BGE-M3 vector retrieval only, with candidate pool 20; do not instantiate a reranker or add query rewriting.
- Rank distinct sources by first occurrence among vector candidates; display every retrieved chunk from the first five distinct sources in candidate order.
- Generate from exactly the displayed evidence and use stable `[1]`–`[5]` citations that correspond to source ranks; no evidence means no generation request.
- Accept only `http://127.0.0.1` or `http://[::1]` Ollama endpoints; do not use environment proxy settings or follow redirects; reject cloud-tagged models before sending the question or evidence.
- Bind Gradio to `127.0.0.1`, call launch with `share=False`, `inbrowser=False`, and disable Gradio analytics with `gr.Blocks(analytics_enabled=False)`.
- Keep questions, answers, retrieved text, and traces in the active request/UI memory only; do not persist them or print them to logs.
- Use synthetic reviewed snapshot fixtures and fake/local HTTP servers for automated tests; never use the private corpus as test input or send it to a remote service.

---

### Task 1: Read-only snapshot retrieval core

**Files:**
- Create: `libs/ktem/ktem/local_qa_core.py`
- Create: `libs/ktem/ktem_tests/test_local_qa_core.py`

**Interfaces:**
- `open_playground(local_root: Path, snapshot_dir: Path, embedding_model_dir: Path, reranker_model_dir: Path, *, embedding_factory: Callable[..., BaseEmbeddings] | None = None) -> LocalQA`
- `LocalQA.retrieve(question: str) -> tuple[EvidenceCard, ...]`
- `EvidenceCard` is a frozen dataclass with `source_rank: int`, `chunk_rank: int`, `source_id: str`, `source_label: str`, `locator: Mapping[str, Any]`, `score: float | None`, and `text: str`.
- Validate the input paths without calling helpers that create directories. Require `snapshot_dir` to resolve beneath the existing `local_root/snapshots/` directory, matching `local_cli.run_command`; use the existing read-only ignored-root, containment, and symlink guards. `local_cli._local_root()` and `_category_dir()` are prohibited because they call `mkdir`.
- Validate approval with `local_cli._validate_snapshot_approval`, load with `load_local_snapshot`, validate the approved baseline splitter, resolve both manifest-bound model paths with `resolve_model_paths`, and require the already-offline HF process before constructing BGE-M3.
- Build exactly once using `local_experiment._make_bundle(snapshot, embedding=embedding, chunking_arm=False)` and `local_experiment._service(bundle, rerankers=())`.
- `retrieve` calls `service.search(question, top_k=20)`, projects the first five distinct source IDs using `source_ranked_chunks`, and returns all candidate chunks belonging to that source window in their original candidate order. Populate only relative display paths from the snapshot; never expose an absolute filesystem path.

- [x] **Step 1: Write the failing core tests**

Create a reviewed synthetic snapshot using the small writer pattern from `libs/kotaemon/tests/test_knowledge_eval_local_experiment.py`; write its manifest-bound `approval.json` sidecar. Use fake model paths, a deterministic embedding implementation, and monkeypatch only model-path resolution/offline initialization. Keep actual snapshot loading, sidecar verification, splitter validation, in-memory indexing, and service search active.

```python
def test_open_playground_builds_index_once_and_does_not_write(tmp_path, monkeypatch):
    local_root, snapshot_dir, embedding_dir, reranker_dir = reviewed_fixture(tmp_path)
    before = snapshot_tree(local_root)
    embedding = CountingEmbedding()
    monkeypatch.setattr(local_qa_core, "resolve_model_paths", fake_model_paths)
    monkeypatch.setattr(local_qa_core, "_require_offline_inference_process", lambda: None)

    qa = open_playground(
        local_root, snapshot_dir, embedding_dir, reranker_dir,
        embedding_factory=lambda *args, **kwargs: embedding,
    )
    cards = qa.retrieve("alpha unique target phrase")

    assert embedding.document_batches == 1
    assert embedding.query_calls == 1
    assert [card.source_label for card in cards]
    assert snapshot_tree(local_root) == before


def test_retrieve_uses_first_five_sources_and_keeps_all_matching_chunks(fake_qa):
    # Candidate source order is A, B, A, C, D, E, F, B, ... .
    # The top-five source window is A-E; every A/B chunk remains visible.
    cards = fake_qa.retrieve("question")
    assert [card.source_rank for card in cards] == [1, 2, 1, 3, 4, 5, 2]
    assert [card.chunk_rank for card in cards] == [1, 2, 3, 4, 5, 6, 8]
```

Add separate tests proving an invalid approval sidecar, modified snapshot payload, snapshot outside `local_root/snapshots/`, symlinked snapshot path, and non-baseline splitter each fail before embedding/index construction. Add a retrieval assertion that no more than 20 candidates are requested, and that candidate ranking is unchanged when multiple chunks from one source occur before another source. Build an ambiguous repeated-text snapshot using `source0_text="alpha unique target phrase " * 1500`, retrieve one chunk recorded in `bundle["unresolved_offsets"]`, and assert its locator is displayed without a `KeyError`.

- [x] **Step 2: Run the core tests and confirm the intended RED result**

Run from repository root: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_core.py`.
Expected: collection fails because `ktem.local_qa_core` does not exist yet. After the module skeleton and API are introduced, the behavior tests must fail on the missing implementation/incorrect behavior rather than on fixture errors.

- [x] **Step 3: Implement the core types and startup path**

```python
@dataclass(frozen=True)
class EvidenceCard:
    source_rank: int
    chunk_rank: int
    source_id: str
    source_label: str
    locator: Mapping[str, Any]
    score: float | None
    text: str


def open_playground(
    local_root: Path,
    snapshot_dir: Path,
    embedding_model_dir: Path,
    reranker_model_dir: Path,
    *,
    embedding_factory: Callable[..., BaseEmbeddings] | None = None,
) -> LocalQA:
    root = local_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("local root must be an existing directory")
    _require_ignored_repo_local_root(root)
    snapshots_root = _ensure_contained(root / "snapshots", root, "snapshots")
    _reject_symlink_components(snapshots_root, stop=root)
    if not snapshots_root.is_dir():
        raise ValueError("local snapshots/ directory must already exist")
    snapshot_path = _ensure_contained(snapshot_dir, snapshots_root, "snapshot")
    _reject_symlink_components(snapshot_path, stop=snapshots_root)
    _validate_snapshot_approval(snapshot_path)
    snapshot = load_local_snapshot(snapshot_path, require_reviewed=True)
    _validate_baseline_splitter(snapshot)
    paths = resolve_model_paths(root, embedding_model_dir, reranker_model_dir)
    _validate_model_provenance(paths)
    _require_offline_inference_process()
    factory = embedding_factory or _create_embedding
    embedding = factory(
        paths.embedding_model_dir,
        revision=paths.embedding_revision,
        weight_source=paths.embedding_weight_source,
    )
    bundle = _make_bundle(snapshot, embedding=embedding, chunking_arm=False)
    service = _service(bundle, rerankers=())
    return LocalQA(snapshot=snapshot, bundle=bundle, service=service)
```

`LocalQA` stores the built service, chunk-to-source mapping, snapshot source rows, and the bundle locator maps. Its `_locator_for_chunk(chunk_id)` returns `draft_chunks[chunk_id].locator` when the chunk has a unique text span and otherwise returns `unresolved_offsets[chunk_id].locator`; both maps cover every indexed chunk. Implement it as:

```python
def _locator_for_chunk(self, chunk_id: str) -> Mapping[str, Any]:
    draft = self._bundle["draft_chunks"].get(chunk_id)
    if draft is not None:
        return draft.locator
    unresolved = self._bundle["unresolved_offsets"].get(chunk_id)
    if unresolved is None:
        raise ValueError(f"retrieved chunk {chunk_id!r} has no source locator")
    return unresolved.locator
```

It must not store or load the gold judgments as interactive filters. Preserve retrieval scores if they are finite numbers; otherwise set `score=None`. Read source labels from the matching snapshot row's repository-relative `relative_path`.

- [x] **Step 4: Implement source-window projection**

```python
def retrieve(self, question: str) -> tuple[EvidenceCard, ...]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must not be empty")
    candidates = self._service.search(question.strip(), top_k=20)
    representatives = source_ranked_chunks(
        candidates, self._chunk_to_source, limit=5
    )
    selected_sources = {
        self._chunk_to_source[document.doc_id] for document in representatives
    }
    source_ranks = {
        self._chunk_to_source[document.doc_id]: rank
        for rank, document in enumerate(representatives, start=1)
    }
    return tuple(
        EvidenceCard(
            source_rank=source_ranks[source_id],
            chunk_rank=rank,
            source_id=source_id,
            source_label=self._sources_by_id[source_id]["relative_path"],
            locator=dict(
                self._locator_for_chunk(document.doc_id)
            ),
            score=(document.score if math.isfinite(document.score) else None),
            text=document.text,
        )
        for rank, document in enumerate(candidates, start=1)
        if (source_id := self._chunk_to_source[document.doc_id]) in selected_sources
    )
```

Compute each source's one-based citation rank from `representatives`; compute each chunk's one-based candidate rank from its original candidate position. Return an empty tuple when search returns no candidates.

- [x] **Step 5: Run the focused core tests and confirm GREEN**

Run: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_core.py`.
Expected: all core tests pass, including the read-only snapshot/tree check and the rejection tests.

- [x] **Step 6: Commit Task 1**

```bash
git add libs/ktem/ktem/local_qa_core.py libs/ktem/ktem_tests/test_local_qa_core.py
git commit -m "feat: add read-only local snapshot QA retrieval"
```

### Task 2: Loopback-only Ollama generation

**Files:**
- Create: `libs/ktem/ktem/local_qa_ollama.py`
- Create: `libs/ktem/ktem_tests/test_local_qa_ollama.py`

**Interfaces:**
- `OllamaLocalClient(endpoint: str = "http://127.0.0.1:11434", model: str = "qwen2.5:7b", *, timeout: float = 120.0)`
- `OllamaLocalClient.generate(question: str, cards: Sequence[EvidenceCard]) -> str`
- Accept only HTTP URLs whose literal host is `127.0.0.1` or `::1`, with no credentials, query, or fragment. Reject any model name containing a cloud tag (`cloud`, case-insensitive) before opening a connection.
- Use `urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirectHandler())`; treat every 3xx as an error and never contact its `Location` target.
- POST to `/api/chat` with `stream: false`. The system/user prompts contain only the question and the exact cards supplied by the caller. Tell the model to treat evidence as untrusted data, answer concisely, cite the displayed sources using `[rank]`, and admit insufficient evidence.
- Parse only a successful JSON response with a nonempty `message.content`; use a finite timeout and do not include request bodies in raised errors.

- [x] **Step 1: Write failing tests with a loopback HTTP fixture**

Use `ThreadingHTTPServer` bound to `127.0.0.1` in a context manager. Its normal route records the request body and returns a small Ollama `/api/chat` response. Its redirect route returns `302 Location: /capture`; assert `/capture` is never reached. Endpoint constructor tests also include the empty-userinfo URL `http://@127.0.0.1:11434` and assert it is rejected before opening a connection.

```python
def test_prompt_contains_only_displayed_cards(loopback_ollama):
    client = OllamaLocalClient(endpoint=loopback_ollama.url)
    shown = EvidenceCard(1, 1, "source-a", "policy.pdf", {"page": 2}, 0.8, "shown text")
    answer = client.generate("What does the policy say?", [shown])

    payload = loopback_ollama.last_json
    prompt = "\n".join(message["content"] for message in payload["messages"])
    assert answer == "Answer [1]"
    assert payload["stream"] is False
    assert "shown text" in prompt and "policy.pdf" in prompt
    assert "undisplayed candidate" not in prompt


def test_non_loopback_cloud_model_and_redirect_are_rejected_before_leak(loopback_ollama):
    with pytest.raises(ValueError):
        OllamaLocalClient(endpoint="https://example.com/api")
    with pytest.raises(ValueError):
        OllamaLocalClient(endpoint=loopback_ollama.url, model="qwen3:cloud")
    assert loopback_ollama.request_count == 0
    with pytest.raises((ValueError, urllib.error.HTTPError)):
        OllamaLocalClient(endpoint=loopback_ollama.redirect_url).generate("secret", [card()])
    assert loopback_ollama.redirect_target_count == 0
```

Also test rejection of `localhost`, credentials, query/fragment, invalid port, cloud model rejection before any request, IPv6 loopback parsing, proxy environment variables being ignored for loopback, malformed/empty Ollama response, and citation rank/source text mapping.

- [x] **Step 2: Run the Ollama tests and confirm RED**

Run: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_ollama.py`.
Expected: collection fails because `ktem.local_qa_ollama` does not exist; then each endpoint/prompt test must fail for the missing client rather than fixture setup.

- [x] **Step 3: Implement URL and model validation before transport**

```python
def _validate_endpoint(endpoint: str) -> str:
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}:
        raise ValueError("Ollama endpoint must use a loopback IP literal")
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Ollama endpoint contains unsupported URL fields")
    _ = parsed.port  # raises ValueError for malformed ports
    if parsed.path not in {"", "/"}:
        raise ValueError("Ollama endpoint must not include an API path")
    return endpoint.rstrip("/")
```

Validate the model string in `__init__` before any request; reject empty names, whitespace-only names, URL-like model values, and case-insensitive cloud tags. Normalize the endpoint's base path only if the plan's endpoint validator explicitly accepts `/`; otherwise require no non-root path.

- [x] **Step 4: Implement evidence prompt and non-redirecting, proxy-free POST**

```python
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _NoRedirect(),
)
request = urllib.request.Request(
    endpoint + "/api/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
```

Serialize the question and cards into messages without adding other retrieved candidates or chat history. Read at most 2 MiB of response bytes, require `message.content` to be a nonempty string, and convert HTTP/JSON/schema failures into concise errors that do not contain the prompt or evidence.

- [x] **Step 5: Run focused Ollama tests and confirm GREEN**

Run: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_ollama.py`.
Expected: all URL, proxy, redirect, request-body, and response-validation tests pass without contacting any external host.

- [x] **Step 6: Commit Task 2**

```bash
git add libs/ktem/ktem/local_qa_ollama.py libs/ktem/ktem_tests/test_local_qa_ollama.py
git commit -m "feat: add loopback-only Ollama QA generation"
```

### Task 3: Standalone Gradio workbench and launch guide

**Files:**
- Create: `libs/ktem/ktem/local_qa_playground.py`
- Create: `libs/ktem/ktem_tests/test_local_qa_playground.py`
- Create: `docs/local-qa-playground.md`

**Interfaces:**
- `answer_question(qa: LocalQA, generator: OllamaLocalClient, question: str) -> tuple[str, list[dict[str, Any]]]`
- `clear_outputs() -> tuple[str, str, list[dict[str, Any]]]`
- `build_ui(qa: LocalQA, generator: OllamaLocalClient, *, snapshot_version: str) -> gr.Blocks`; `main` passes the selected snapshot path's name only after `open_playground` validates that snapshot.
- `main(argv: Sequence[str] | None = None) -> int`; flags are `--local-root`, `--snapshot`, `--embedding-model-dir`, `--reranker-model-dir`, `--ollama-endpoint`, `--model`, and `--server-port`.
- Build a standalone Gradio page with one independent question textbox, Ask and Clear buttons, an answer `Textbox`, and a JSON evidence panel. No conversation component, session history, cache, or file/database write is allowed.
- Each evidence object displays source rank, candidate chunk rank, relative source label, locator, score, and exact chunk text. The generator receives only the evidence cards returned for that same request.
- If retrieval is empty, show a no-evidence answer and do not call the generator. If local Ollama is unavailable, retain evidence and show an actionable message to start Ollama and run `ollama pull <model>`.
- Launch only with `server_name="127.0.0.1"`, `share=False`, and `inbrowser=False`.

- [x] **Step 1: Write failing callback and launch tests**

Use fake `LocalQA` and generator objects that record calls. Keep tests independent of snapshot/model files and do not call a real Ollama process.

```python
def test_answer_question_generates_from_exact_retrieval_cards():
    qa = FakeQA(cards=[card(text="evidence")])
    generator = FakeGenerator(answer="The answer is 42 [1].")

    answer, evidence = answer_question(qa, generator, "What is the answer?")

    assert answer == "The answer is 42 [1]."
    assert generator.calls == [("What is the answer?", qa.cards)]
    assert evidence[0]["text"] == "evidence"


def test_empty_retrieval_skips_generation_and_clear_resets_outputs():
    qa = FakeQA(cards=[])
    generator = FakeGenerator(answer="must not be used")

    answer, evidence = answer_question(qa, generator, "unknown")

    assert "no evidence" in answer.lower()
    assert evidence == []
    assert generator.calls == []
    assert clear_outputs() == ("", "", [])
```

Add tests that two Ask calls have no prior-question context, errors preserve evidence without echoing question/source text, UI wiring points Ask to the callback and Clear to `clear_outputs`, Gradio analytics are disabled, and `main` binds to `127.0.0.1` with `share=False` and forwards the configured port.

- [x] **Step 2: Run UI tests and confirm RED**

Run: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_playground.py`.
Expected: collection fails because `ktem.local_qa_playground` does not exist; after a module skeleton is added, callback tests must fail on missing behavior rather than Gradio import problems.

- [x] **Step 3: Implement pure request callbacks**

```python
def answer_question(qa, generator, question):
    clean_question = question.strip()
    if not clean_question:
        return "Enter a question.", []
    cards = qa.retrieve(clean_question)
    evidence = [
        {
            "source_rank": card.source_rank,
            "chunk_rank": card.chunk_rank,
            "source": card.source_label,
            "locator": dict(card.locator),
            "score": card.score,
            "text": card.text,
        }
        for card in cards
    ]
    if not cards:
        return "No evidence was retrieved from the frozen snapshot.", []
    try:
        return generator.generate(clean_question, cards), evidence
    except (OSError, ValueError, urllib.error.URLError):
        return (
            f"Local answer generation failed. Start Ollama and run `ollama pull {generator.model}`.",
            evidence,
        )
```

Keep the callback stateless: each call uses only its `question`, `cards`, and one local generation request. Do not write to the snapshot or a trace file.

- [x] **Step 4: Build UI, CLI, and launch guide**

```python
def build_ui(
    qa: LocalQA,
    generator: OllamaLocalClient,
    *,
    snapshot_version: str,
) -> gr.Blocks:
    with gr.Blocks(title="Local Snapshot QA", analytics_enabled=False) as demo:
        gr.Markdown(
            f"Snapshot {snapshot_version} · BGE-M3 · baseline token chunks · "
            "vector top-20 · top-five sources · "
            f"local generator {generator.model}"
        )
        question = gr.Textbox(label="Question", lines=3)
        with gr.Row():
            ask = gr.Button("Ask", variant="primary")
            clear = gr.Button("Clear")
        answer = gr.Textbox(label="Answer", lines=8, interactive=False)
        evidence = gr.JSON(label="Retrieved evidence")
        ask.click(
            fn=lambda question_text: answer_question(qa, generator, question_text),
            inputs=[question],
            outputs=[answer, evidence],
        )
        clear.click(clear_outputs, inputs=[], outputs=[question, answer, evidence])
    return demo
```

The page description identifies the frozen snapshot version, BGE-M3, baseline token chunks, vector candidate pool 20, top-five source window, and configured local generation model. Add an argparse entrypoint and a short guide with the exact launch form:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --package ktem python -m ktem.local_qa_playground \
  --local-root /path/to/git-ignored/local-root \
  --snapshot /path/to/git-ignored/local-root/snapshots/v2 \
  --embedding-model-dir /path/to/git-ignored/local-root/models/bge-m3 \
  --reranker-model-dir /path/to/git-ignored/local-root/models/bge-reranker \
  --ollama-endpoint http://127.0.0.1:11434 --model qwen2.5:7b
```

Document the prerequisite `ollama pull qwen2.5:7b` and explain that query, answer, and retrieved text remain in the local UI process memory. Do not put private fixture paths or corpus content in the guide.

- [x] **Step 5: Run focused tests and inspect the local UI**

Run: `uv run --package ktem pytest -q libs/ktem/ktem_tests/test_local_qa_core.py libs/ktem/ktem_tests/test_local_qa_ollama.py libs/ktem/ktem_tests/test_local_qa_playground.py`.
Run format check: `uv run black --check libs/ktem/ktem/local_qa_core.py libs/ktem/ktem/local_qa_ollama.py libs/ktem/ktem/local_qa_playground.py libs/ktem/ktem_tests/test_local_qa_core.py libs/ktem/ktem_tests/test_local_qa_ollama.py libs/ktem/ktem_tests/test_local_qa_playground.py`.
Run read-only retrieval regressions from `libs/kotaemon`: `uv run pytest -q tests/test_knowledge_eval_local_experiment.py tests/test_knowledge_eval_local_cli.py -k 'not git_ignore_guard_accepts_local_fixture_root_without_writes'`.
Start the UI once with a synthetic snapshot and fake local generator, inspect the rendered page and Ask/Clear behavior in a browser, then stop it. After review and if the local Ollama model is installed, start the approved v2 workbench against the ignored local data root for the user to enter their own questions. Do not enter a user question or save a transcript.

- [x] **Step 6: Commit Task 3**

```bash
git add libs/ktem/ktem/local_qa_playground.py libs/ktem/ktem_tests/test_local_qa_playground.py docs/local-qa-playground.md
git commit -m "feat: add local snapshot QA playground UI"
```

### Final review and PR update

- [x] Review the full branch diff against the PR base for spec compliance, private-data handling, URL restrictions, read-only behavior, and UI wiring; resolve the three Minor findings and obtain GPT-6 Sol Medium final approval (0 C/I/M).
- [x] Run all three focused test files and the specified read-only evaluator regressions; inspect `git diff --check` and `git status --short`.
- [x] Push the reviewed commits to the existing feature branch and update PR #874. Do not add any ignored fixture, source document, model weight, question, answer, or trace to Git.
