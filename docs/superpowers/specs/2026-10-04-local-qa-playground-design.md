# Local Golden Snapshot QA Playground Design

## Goal

Let the user ask arbitrary questions against the frozen local v2 snapshot and inspect both the generated answer and the exact retrieved evidence, without changing the golden set, benchmark results, or Kotaemon's persistent application index.

## Current project context

The approved v2 snapshot contains 22 source documents, 80 golden questions, and 139 reviewed evidence anchors. The offline evaluator already builds an in-memory `KnowledgeService` using the same vector retrieval abstraction as Kotaemon. Its strongest individual retrieval arm was BGE-M3 over the baseline token chunks; it requested 20 vector candidates and scored the first five distinct sources. The current experiment did not evaluate BGE-M3 combined with the reranker, so this playground will not silently add that combination.

Kotaemon's main Chat page has an evidence panel, but it reads the application's configured indexes. The frozen snapshot is not loaded into that index. The evaluation environment has local BGE-M3 and reranker assets but no configured local answer-generation model or Ollama installation. The repository's first-setup page uses Ollama and defaults to `qwen2.5:7b`; the official Ollama model entry currently lists that variant at about 4.7 GB and describes multilingual support including Chinese: <https://ollama.com/library/qwen2.5%3A7b>.

## Options considered

1. **Load the snapshot into the existing Chat index.** This reuses the current chat UI, but writes into the app's persistent index and can mix the reviewed snapshot with existing user data or app-specific chunking settings.
2. **Run a separate local Gradio QA playground (selected).** It reads the exact approved snapshot, builds an ephemeral in-memory retriever, and displays the answer next to ranked evidence. It keeps the benchmark and regular Chat index independent.
3. **Add a terminal REPL.** This is smaller, but makes answer/evidence comparison and reading long chunks less convenient.

## Architecture and data flow

Add a standalone Gradio entry point under `libs/ktem`, where Gradio is already a declared dependency. At startup it accepts an explicit local root and snapshot path, verifies the snapshot with the existing loader and approval-sidecar checks, resolves the existing local BGE-M3 model through the verified model manifest, and creates the in-memory index once. The source data remains in the Git-ignored local fixture tree.

At startup, the backend uses the frozen snapshot's normalized source units to build baseline token chunks once, with the exact measured splitter configuration: 1,024-token size, 256-token overlap, separator `\n\n`, and backup separators `\n`, `.`, space, and zero-width space. It embeds and indexes those chunks with local BGE-M3 once. Each submission embeds only the new query and calls the existing vector-only `KnowledgeService` for 20 candidates. The source rank is the first-occurrence order of distinct source IDs among those candidates, matching the measured embedding arm's source ranking; the UI shows all retrieved chunks belonging to the top five sources, in chunk rank order, as evidence. No reranker or query rewriting is added.

The local answer generator receives the question plus the displayed chunks only. Chunks are grouped by source rank and labeled `[1]` through `[5]`, so repeated chunks from one source share a citation. The prompt treats chunk text as untrusted evidence, asks for a concise answer using those citations, and tells the model to say when the snapshot lacks enough evidence. Citation labels map directly to the displayed source cards.

## User interface

- One question textbox, an Ask action, and a Clear action. Each question is independent; there is no hidden chat history.
- An answer panel shows the local model response and its source citations.
- An evidence panel lists up to five distinct sources in retrieval order. Each card shows rank, document display label, available page/section/sheet locator, raw retrieval score when supplied by the retriever, and the exact chunk text passed to generation.
- A small configuration note identifies BGE-M3, baseline token chunking, candidate pool 20, top five sources, and the configured local generation model.
- Empty retrieval returns a clear no-evidence state instead of asking the generator to invent an answer.

## Local-only and data handling requirements

- The Gradio server binds to `127.0.0.1` by default and does not create a public share link.
- The generator endpoint uses a loopback IP literal only (`127.0.0.1` or `::1`); hostnames such as `localhost` are rejected so a DNS result cannot change the destination. Use an HTTP client configured to ignore environment proxy settings and not follow redirects; treat every 3xx response as an error. Reject non-loopback URLs and cloud-tagged model names before sending the question or source text, and never send that content to a redirect target.
- Use the local Ollama API at `http://127.0.0.1:11434` by default, with `qwen2.5:7b` as the initial model setting. Runtime and model setup may download software/model weights, but query text and corpus text are only sent to the pinned loopback model endpoint.
- Queries, answers, traces, and retrieval results stay in the active UI session memory. The playground does not append labels, questions, model outputs, or traces to v2, the benchmark run directory, or the persistent Kotaemon database.
- Snapshot validation or model integrity failure stops startup. A missing Ollama service or model produces an actionable local setup message. The user can clear the current answer/evidence state at any time.

## Testing and acceptance criteria

Use synthetic snapshots and a fake local generator for automated tests. Prove that startup refuses unapproved/tampered snapshots; the corpus is chunked and embedded once at startup; each query returns the same top-five distinct-source ordering as the measured source-ranking projection over at most 20 candidates; exact splitter settings are preserved; all retrieved chunks for those five sources appear in rank order; only displayed evidence reaches the answer prompt; citations map back to the correct source cards; empty results do not invoke generation; non-loopback IPs, hostnames, redirect responses, inherited proxy settings, and cloud model names fail or are ignored before any request can leave loopback; and a question never mutates snapshot or run artifacts. Run focused Python tests and inspect the rendered Gradio UI locally before presenting the playground.

## Non-goals

- Do not alter the frozen golden questions, anchors, metrics, or experiment artifacts.
- Do not write generated answers back into judgments or treat user questions as evaluation cases.
- Do not add a production retriever, modify the default Kotaemon Chat page, or write anything to its persistent document index.
- Do not claim the one-factor benchmark measured this answer-generation model or an embedding-plus-reranker combination.
