"""Synthetic tests for the standalone local QA workbench."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import gradio as gr
import pytest

import ktem.local_qa_playground as playground
from ktem.local_qa_core import EvidenceCard
from ktem.local_qa_playground import (
    answer_question,
    build_ui,
    clear_outputs,
    clear_session_outputs,
    main,
)
from ktem.local_qa_conversation import ConversationState


class FakeQA:
    def __init__(self, cards=(), *, cards_by_question=None):
        self.cards = list(cards)
        self.cards_by_question = cards_by_question
        self.calls = []

    def retrieve(self, question):
        self.calls.append(question)
        if self.cards_by_question is not None:
            return tuple(self.cards_by_question[question])
        return tuple(self.cards)


class FakeGenerator:
    def __init__(self, answer="synthetic answer", *, error=None, model="synthetic:tag"):
        self.answer = answer
        self.error = error
        self.model = model
        self.calls = []
        self.stream_calls = []

    def generate(self, question, cards):
        self.calls.append((question, cards))
        if self.error is not None:
            raise self.error
        return self.answer

    def generate_stream(self, question, cards):
        self.stream_calls.append((question, cards))
        if self.error is not None:
            raise self.error
        yield self.answer


class ChunkedGenerator(FakeGenerator):
    def __init__(self, chunks, *, error_after_chunks=None):
        super().__init__()
        self.chunks = list(chunks)
        self.error_after_chunks = error_after_chunks

    def generate_stream(self, question, cards):
        self.stream_calls.append((question, cards))
        for chunk in self.chunks:
            yield chunk
        if self.error_after_chunks is not None:
            raise self.error_after_chunks


def card(
    *,
    source_rank=1,
    chunk_rank=1,
    source_id="synthetic-source",
    source_label="synthetic/doc.md",
    locator=None,
    score=0.75,
    text="synthetic evidence",
):
    return EvidenceCard(
        source_rank=source_rank,
        chunk_rank=chunk_rank,
        source_id=source_id,
        source_label=source_label,
        locator=locator if locator is not None else {"page": 2},
        score=score,
        text=text,
    )


def test_answer_question_generates_from_exact_retrieval_cards():
    evidence_card = card(text="evidence")
    qa = FakeQA(cards=[evidence_card])
    generator = FakeGenerator(answer="The answer is 42 [1].")

    answer, evidence = answer_question(qa, generator, "What is the answer?")

    assert answer == "The answer is 42 [1]."
    assert qa.calls == ["What is the answer?"]
    assert generator.calls == [("What is the answer?", (evidence_card,))]
    assert evidence == [
        {
            "source_rank": 1,
            "chunk_rank": 1,
            "source": "synthetic/doc.md",
            "locator": {"page": 2},
            "score": 0.75,
            "text": "evidence",
        }
    ]


def test_empty_retrieval_skips_generation_and_clear_resets_outputs():
    qa = FakeQA(cards=[])
    generator = FakeGenerator(answer="must not be used")

    answer, evidence = answer_question(qa, generator, "unknown")

    assert "no evidence" in answer.lower()
    assert evidence == []
    assert generator.calls == []
    assert clear_outputs() == ("", "", [])


def test_blank_question_is_rejected_before_retrieval_or_generation():
    qa = FakeQA(cards=[card()])
    generator = FakeGenerator()

    answer, evidence = answer_question(qa, generator, "  \n  ")

    assert answer == "Enter a question."
    assert evidence == []
    assert qa.calls == []
    assert generator.calls == []


def test_independent_asks_use_only_each_questions_own_cards():
    first_card = card(source_id="synthetic-a", text="first evidence")
    second_card = card(source_id="synthetic-b", text="second evidence")
    qa = FakeQA(
        cards_by_question={
            "first question": [first_card],
            "second question": [second_card],
        }
    )
    generator = FakeGenerator()

    first_answer, first_evidence = answer_question(qa, generator, "first question")
    second_answer, second_evidence = answer_question(qa, generator, "second question")

    assert first_answer == "synthetic answer"
    assert second_answer == "synthetic answer"
    assert [item["text"] for item in first_evidence] == ["first evidence"]
    assert [item["text"] for item in second_evidence] == ["second evidence"]
    assert qa.calls == ["first question", "second question"]
    assert generator.calls == [
        ("first question", (first_card,)),
        ("second question", (second_card,)),
    ]


@pytest.mark.parametrize("error", [OSError("secret question secret source")])
def test_generator_failure_preserves_evidence_without_echoing_private_text(error):
    evidence_card = card(
        source_label="secret/source.md",
        text="secret evidence text",
    )
    qa = FakeQA(cards=[evidence_card])
    generator = FakeGenerator(error=error, model="synthetic-model")

    answer, evidence = answer_question(qa, generator, "secret question")

    assert "start ollama" in answer.lower()
    assert "ollama pull synthetic-model" in answer
    assert "secret question" not in answer
    assert "secret/source.md" not in answer
    assert "secret evidence text" not in answer
    assert evidence[0]["source"] == "secret/source.md"
    assert evidence[0]["text"] == "secret evidence text"
    assert generator.calls == [("secret question", (evidence_card,))]


def test_generator_value_error_preserves_evidence_and_hides_error_details():
    evidence_card = card(text="synthetic visible chunk")
    qa = FakeQA(cards=[evidence_card])
    generator = FakeGenerator(error=ValueError("private prompt details"))

    answer, evidence = answer_question(qa, generator, "synthetic question")

    assert "private prompt details" not in answer
    assert evidence[0]["text"] == "synthetic visible chunk"


def test_stream_answer_yields_evidence_first_and_preserves_final_answer(monkeypatch):
    clock = iter([0.0, 0.01, 0.02, 0.03])
    monkeypatch.setattr(playground, "monotonic", lambda: next(clock), raising=False)
    evidence_card = card(text="synthetic streamed evidence")
    events = []

    class OrderedQA(FakeQA):
        def retrieve(self, question):
            events.append("retrieved")
            return super().retrieve(question)

    class OrderedGenerator(ChunkedGenerator):
        def generate_stream(self, question, cards):
            events.append("generation started")
            yield from super().generate_stream(question, cards)

    qa = OrderedQA(cards=[evidence_card])
    generator = OrderedGenerator(["The ", "answer", " is 42."])
    updates = playground.stream_answer_question(qa, generator, "synthetic question")

    status, evidence = next(updates)
    assert status == "Generating locally…"
    assert evidence[0]["text"] == "synthetic streamed evidence"
    assert events == ["retrieved"]
    assert list(updates) == [("The answer is 42.", gr.skip())]
    assert events == ["retrieved", "generation started"]
    assert generator.stream_calls == [("synthetic question", (evidence_card,))]


def test_stream_answer_coalesces_chunks_at_a_bounded_interval(monkeypatch):
    clock = iter([0.0, 0.04, 0.08, 0.12, 0.13])
    monkeypatch.setattr(playground, "monotonic", lambda: next(clock), raising=False)
    qa = FakeQA(cards=[card(text="synthetic evidence")])
    generator = ChunkedGenerator(["a", "b", "c", "d"])

    updates = list(
        playground.stream_answer_question(qa, generator, "synthetic question")
    )

    assert updates[0][0] == "Generating locally…"
    assert updates[0][1][0]["text"] == "synthetic evidence"
    assert updates[1:] == [("abc", gr.skip()), ("abcd", gr.skip())]


def test_stream_answer_failure_preserves_evidence_and_hides_error_details(monkeypatch):
    clock = iter([0.0, 0.01])
    monkeypatch.setattr(playground, "monotonic", lambda: next(clock), raising=False)
    evidence_card = card(text="synthetic evidence")
    qa = FakeQA(cards=[evidence_card])
    generator = ChunkedGenerator(
        ["partial"],
        error_after_chunks=ValueError("synthetic question; synthetic evidence"),
    )

    updates = list(
        playground.stream_answer_question(qa, generator, "synthetic question")
    )

    assert updates[0][0] == "Generating locally…"
    assert updates[0][1][0]["text"] == "synthetic evidence"
    failure, retained_evidence = updates[1]
    assert retained_evidence == gr.skip()
    assert "generation failed" in failure.lower()
    assert "synthetic question" not in failure
    assert "synthetic evidence" not in failure


def test_stream_answer_blank_and_no_evidence_inputs_yield_once():
    qa = FakeQA(cards=[])
    generator = FakeGenerator()

    assert list(playground.stream_answer_question(qa, generator, "  \n ")) == [
        ("Enter a question.", [])
    ]
    assert list(playground.stream_answer_question(qa, generator, "unknown")) == [
        ("No evidence was retrieved from the frozen snapshot.", [])
    ]
    assert qa.calls == ["unknown"]
    assert generator.stream_calls == []


def test_ui_wires_ask_and_clear_and_disables_analytics():
    evidence_card = card(text="synthetic UI evidence")
    qa = FakeQA(cards=[evidence_card])
    generator = FakeGenerator(answer="synthetic UI answer")
    demo = build_ui(qa, generator, snapshot_version="synthetic-v2")
    config = demo.get_config_file()
    components = {component["id"]: component for component in config["components"]}
    description = "\n".join(
        str(component["props"].get("value", ""))
        for component in config["components"]
        if component["type"] == "markdown"
    )

    assert config["analytics_enabled"] is False
    assert "synthetic-v2" in description
    assert "BGE-M3" in description
    assert "baseline token chunks" in description
    assert "20 vector candidates" in description
    assert "top five distinct sources" in description
    assert "synthetic:tag" in description
    assert not any(component["type"] == "chatbot" for component in config["components"])

    question_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "textbox"
        and component["props"].get("label") == "Question"
    )
    state_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "state"
    )
    rewrite_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "checkbox"
        and component["props"].get("label")
        == "Resolve follow-ups with recent user turns"
    )
    answer_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "textbox"
        and component["props"].get("label") == "Answer"
    )
    evidence_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "json"
        and component["props"].get("label") == "Retrieved evidence"
    )
    ask_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "button" and component["props"].get("value") == "Ask"
    )
    clear_id = next(
        component_id
        for component_id, component in components.items()
        if component["type"] == "button" and component["props"].get("value") == "Clear"
    )
    dependencies = config["dependencies"]
    ask_event = next(
        event for event in dependencies if (ask_id, "click") in event["targets"]
    )
    clear_event = next(
        event for event in dependencies if (clear_id, "click") in event["targets"]
    )
    cancel_event = next(
        event
        for event in dependencies
        if (clear_id, "click") in event["targets"] and event["types"]["cancel"]
    )

    assert ask_event["inputs"] == [question_id, state_id, rewrite_id]
    assert ask_event["outputs"] == [answer_id, evidence_id, state_id]
    ask_fn = demo.fns[ask_event["id"]].fn
    expected_evidence = [
        {
            "source_rank": 1,
            "chunk_rank": 1,
            "source": "synthetic/doc.md",
            "locator": {"page": 2},
            "score": 0.75,
            "text": "synthetic UI evidence",
        }
    ]
    updates = list(ask_fn("Which evidence?", ConversationState(), False))
    assert [update[:2] for update in updates] == [
        ("Generating locally…", expected_evidence),
        ("synthetic UI answer", gr.skip()),
    ]
    assert all(update[2].user_turns == ("Which evidence?",) for update in updates)
    assert generator.stream_calls == [("Which evidence?", (evidence_card,))]

    assert clear_event["inputs"] == []
    assert clear_event["outputs"] == [question_id, answer_id, evidence_id, state_id]
    assert cancel_event["cancels"] == [ask_event["id"]]
    clear_fn = demo.fns[clear_event["id"]].fn
    assert clear_fn() == ("", "", [], ConversationState())
    assert clear_session_outputs(ConversationState(("private turn",)))[3] == (
        ConversationState()
    )


@pytest.mark.parametrize(
    ("model_arguments", "expected_model"),
    [(["--model", "synthetic:tag"], "synthetic:tag"), ([], "qwen2.5:3b")],
)
def test_main_forwards_cli_model_or_defaults_to_qwen_3b(
    monkeypatch, model_arguments, expected_model
):
    import ktem.local_qa_playground as playground

    expected_paths = (
        Path("/synthetic/local-root"),
        Path("/synthetic/local-root/snapshots/v2"),
        Path("/synthetic/models/bge-m3"),
        Path("/synthetic/models/bge-reranker"),
    )
    open_calls = []
    generator_calls = []
    qa = object()
    generator = object()

    def fake_open(*args):
        open_calls.append(args)
        return qa

    def fake_generator(endpoint, model):
        generator_calls.append((endpoint, model))
        return generator

    class FakeDemo:
        def __init__(self):
            self.launch_kwargs = None

        def launch(self, **kwargs):
            self.launch_kwargs = kwargs

    demo = FakeDemo()
    build_calls = []

    def fake_build(actual_qa, actual_generator, *, snapshot_version):
        build_calls.append((actual_qa, actual_generator, snapshot_version))
        return demo

    monkeypatch.setattr(playground, "open_playground", fake_open)
    monkeypatch.setattr(playground, "OllamaLocalClient", fake_generator)
    monkeypatch.setattr(playground, "build_ui", fake_build)

    result = main(
        [
            "--local-root",
            str(expected_paths[0]),
            "--snapshot",
            str(expected_paths[1]),
            "--embedding-model-dir",
            str(expected_paths[2]),
            "--reranker-model-dir",
            str(expected_paths[3]),
            "--ollama-endpoint",
            "http://127.0.0.1:11435",
            *model_arguments,
            "--server-port",
            "7865",
        ]
    )

    assert result == 0
    assert open_calls == [expected_paths]
    assert generator_calls == [("http://127.0.0.1:11435", expected_model)]
    assert build_calls == [(qa, generator, "v2")]
    assert demo.launch_kwargs == {
        "server_name": "127.0.0.1",
        "server_port": 7865,
        "share": False,
        "inbrowser": False,
    }


def test_setup_page_defaults_ollama_to_qwen_3b(monkeypatch):
    import ktem.pages.setup as setup

    class FakeComponent:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    gradio_stub = SimpleNamespace(
        Markdown=FakeComponent,
        Radio=FakeComponent,
        Column=FakeComponent,
        Textbox=FakeComponent,
        HTML=FakeComponent,
        Row=FakeComponent,
        Button=FakeComponent,
    )
    monkeypatch.setattr(setup, "gr", gradio_stub)
    monkeypatch.setattr(setup, "config", lambda _key, *, default: default)

    page = setup.SetupPage(SimpleNamespace(app_name="Synthetic"))

    assert page.ollama_model_name.kwargs["value"] == "qwen2.5:3b"
