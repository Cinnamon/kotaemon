"""Standalone Gradio workbench for questions over an approved local snapshot."""

from __future__ import annotations

import argparse
import urllib.error
from collections.abc import Iterator, Sequence
from pathlib import Path
from time import monotonic
from typing import Any

import gradio as gr
from ktem.local_qa_core import LocalQA, open_playground
from ktem.local_qa_defaults import DEFAULT_LOCAL_MODEL
from ktem.local_qa_conversation import (
    DEFAULT_HISTORY_TOKEN_LIMIT,
    DEFAULT_MAX_TURNS,
    ConversationState,
    OllamaQueryRewriter,
)
from ktem.local_qa_ollama import OllamaLocalClient

_STREAM_UPDATE_INTERVAL = 0.1


def answer_question(
    qa: LocalQA,
    generator: OllamaLocalClient,
    question: str,
    *,
    user_history: Sequence[str] = (),
    query_rewriter=None,
) -> tuple[str, Any]:
    clean_question = question.strip()
    if not clean_question:
        return "Enter a question.", []

    cards, evidence, status = _retrieve_generation_evidence(
        qa,
        generator,
        clean_question,
        user_history=user_history,
        query_rewriter=query_rewriter,
    )
    if status == "insufficient_evidence":
        return "No seed evidence fits within the configured context budget.", evidence
    if not cards:
        return "No evidence was retrieved from the frozen snapshot.", []

    try:
        if user_history:
            answer = generator.generate(
                clean_question, cards, user_history=user_history
            )
        else:
            answer = generator.generate(clean_question, cards)
    except (OSError, ValueError, urllib.error.URLError):
        answer = (
            "Local answer generation failed. Start Ollama and run "
            f"`ollama pull {generator.model}`."
        )
    return answer, evidence


def stream_answer_question(
    qa: LocalQA,
    generator: OllamaLocalClient,
    question: str,
    *,
    user_history: Sequence[str] = (),
    query_rewriter=None,
) -> Iterator[tuple[str, Any]]:
    clean_question = question.strip()
    if not clean_question:
        yield "Enter a question.", []
        return

    cards, evidence, status = _retrieve_generation_evidence(
        qa,
        generator,
        clean_question,
        user_history=user_history,
        query_rewriter=query_rewriter,
    )
    if status == "insufficient_evidence":
        yield "No seed evidence fits within the configured context budget.", evidence
        return
    if not cards:
        yield "No evidence was retrieved from the frozen snapshot.", []
        return

    yield "Generating locally…", evidence
    answer = ""
    last_emitted_answer = ""
    last_update = monotonic()
    try:
        if user_history:
            stream = generator.generate_stream(
                clean_question, cards, user_history=user_history
            )
        else:
            stream = generator.generate_stream(clean_question, cards)
        for chunk in stream:
            answer += chunk
            now = monotonic()
            if (
                answer != last_emitted_answer
                and now - last_update >= _STREAM_UPDATE_INTERVAL
            ):
                yield answer, gr.skip()
                last_emitted_answer = answer
                last_update = now
    except (OSError, ValueError, urllib.error.URLError):
        yield (
            "Local answer generation failed. Check that Ollama is running and "
            "the configured model is available.",
            gr.skip(),
        )
        return

    if answer and answer != last_emitted_answer:
        yield answer, gr.skip()


def stream_session_answer(
    qa,
    generator,
    question: str,
    conversation_state: ConversationState | None = None,
    resolve_followups: bool = False,
) -> Iterator[tuple[str, Any, ConversationState]]:
    """Retrieve using old session history, then retain this user turn once."""
    state = (
        conversation_state
        if isinstance(conversation_state, ConversationState)
        else ConversationState()
    )
    clean_question = question.strip() if isinstance(question, str) else ""
    if not clean_question:
        for answer, evidence in stream_answer_question(qa, generator, ""):
            yield answer, evidence, state
        return

    count_tokens = getattr(generator, "count_tokens", None)
    if not callable(count_tokens):
        count_tokens = lambda text: len(text.encode("utf-8"))
    updated_state = state.append_user(
        clean_question,
        max_turns=DEFAULT_MAX_TURNS,
        token_limit=DEFAULT_HISTORY_TOKEN_LIMIT,
        count_tokens=count_tokens,
    )
    query_rewriter = OllamaQueryRewriter(generator) if resolve_followups else None
    for answer, evidence in stream_answer_question(
        qa,
        generator,
        clean_question,
        user_history=state.user_turns,
        query_rewriter=query_rewriter,
    ):
        yield answer, evidence, updated_state


def _retrieve_generation_evidence(
    qa,
    generator,
    question,
    *,
    user_history: Sequence[str] = (),
    query_rewriter=None,
):
    retrieve_result = getattr(qa, "retrieve_result", None)
    if callable(retrieve_result):
        options = {}
        generation_budget = getattr(generator, "generation_budget", None)
        count_tokens = getattr(generator, "count_tokens", None)
        base_prompt = getattr(generator, "base_prompt", None)
        options["user_history"] = tuple(user_history)
        if callable(count_tokens):
            options["count_tokens"] = count_tokens
        if query_rewriter is not None:
            options["query_rewriter"] = query_rewriter
        if generation_budget is not None:
            options["generation_budget"] = generation_budget
            options["base_prompt"] = (
                base_prompt(question) if callable(base_prompt) else ""
            )
        result = retrieve_result(question, **options)
        cards = tuple(result.cards)
        diagnostics = dict(result.diagnostics or {})
        evidence_cards = [
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
        if diagnostics or result.status == "insufficient_evidence":
            diagnostics["generation_budget"] = (
                "estimated"
                if diagnostics.get("budget_estimated") is True
                else (
                    "measured"
                    if diagnostics.get("budget_estimated") is False
                    else "not_configured"
                )
            )
            evidence = {
                "cards": evidence_cards,
                "diagnostics": diagnostics,
                "status": result.status,
            }
        else:
            evidence = evidence_cards
        return cards, evidence, result.status

    cards = tuple(qa.retrieve(question))
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
    return cards, evidence, "ready" if cards else "no_evidence"


def clear_outputs() -> tuple[str, str, list[dict[str, Any]]]:
    return "", "", []


def clear_session_outputs(
    _conversation_state: ConversationState | None = None,
) -> tuple[str, str, list[dict[str, Any]], ConversationState]:
    return "", "", [], ConversationState()


def build_ui(
    qa: LocalQA,
    generator: OllamaLocalClient,
    *,
    snapshot_version: str,
) -> gr.Blocks:
    description = (
        f"Frozen snapshot version: `{snapshot_version}`. "
        "Retrieval uses local BGE-M3 embeddings over baseline token chunks, "
        "a local cross-encoder when its verified weights are available, "
        "ephemeral FTS5 diagnostics, a pool of 20 vector candidates, and a "
        "seed window from the top five distinct sources (chunk seed K=20; source K=5). "
        "Evidence expansion is scope-checked and generation context is packed "
        "before Ollama receives it. Diagnostics report unavailable routes and "
        "estimated token budgets. "
        f"Answer generation uses the configured local model `{generator.model}`."
    )

    def ask_question(
        question_text: str,
        conversation_state: ConversationState,
        resolve_followups: bool,
    ):
        yield from stream_session_answer(
            qa,
            generator,
            question_text,
            conversation_state,
            resolve_followups,
        )

    with gr.Blocks(title="Local Snapshot QA", analytics_enabled=False) as demo:
        gr.Markdown(description)
        question = gr.Textbox(label="Question", lines=3)
        conversation_state = gr.State(value=ConversationState())
        resolve_followups = gr.Checkbox(
            label="Resolve follow-ups with recent user turns", value=False
        )
        with gr.Row():
            ask = gr.Button("Ask", variant="primary")
            clear = gr.Button("Clear")
        answer = gr.Textbox(label="Answer", lines=8, interactive=False)
        evidence = gr.JSON(label="Retrieved evidence")
        ask_event = ask.click(
            fn=ask_question,
            inputs=[question, conversation_state, resolve_followups],
            outputs=[answer, evidence, conversation_state],
        )
        clear.click(
            fn=clear_session_outputs,
            inputs=[],
            outputs=[question, answer, evidence, conversation_state],
            cancels=[ask_event],
        )
    return demo


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ask questions over an approved local snapshot with bounded "
            "session history."
        )
    )
    parser.add_argument("--local-root", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--embedding-model-dir", type=Path, required=True)
    parser.add_argument("--reranker-model-dir", type=Path, required=True)
    parser.add_argument(
        "--ollama-endpoint",
        default="http://127.0.0.1:11434",
    )
    parser.add_argument("--model", default=DEFAULT_LOCAL_MODEL)
    parser.add_argument("--server-port", type=int, default=7860)
    args = parser.parse_args(argv)

    qa = open_playground(
        args.local_root,
        args.snapshot,
        args.embedding_model_dir,
        args.reranker_model_dir,
    )
    generator = OllamaLocalClient(args.ollama_endpoint, args.model)
    demo = build_ui(qa, generator, snapshot_version=args.snapshot.name)
    demo.launch(
        server_name="127.0.0.1",
        server_port=args.server_port,
        share=False,
        inbrowser=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
