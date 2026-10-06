"""Behavior tests for bounded local QA conversation retrieval."""

from __future__ import annotations

from types import SimpleNamespace

from ktem.local_qa_core import EvidenceCard
from ktem.local_qa_playground import build_ui

from kotaemon.base import RetrievedDocument
from kotaemon.embeddings import BaseEmbeddings
from kotaemon.indices.knowledge.planning.query_enrichment import QueryEnricher
from kotaemon.indices.qa.format_context import PrepareEvidencePipeline


class FakeRewriteClient:
    endpoint = "http://127.0.0.1:11434"

    def __init__(self, result="VPN reset procedure", *, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def rewrite_query(self, query, user_turns, *, timeout):
        self.calls.append((query, user_turns, timeout))
        if self.error is not None:
            raise self.error
        return self.result


class FakeQA:
    def __init__(self):
        self.calls = []

    def retrieve_result(self, question, **kwargs):
        self.calls.append((question, kwargs))
        card = EvidenceCard(
            source_rank=1,
            chunk_rank=1,
            source_id="selected-source",
            source_label="selected.md",
            locator={},
            score=None,
            text="selected evidence",
        )
        return SimpleNamespace(
            cards=(card,),
            diagnostics={},
            status="ready",
        )


class FakeGenerator:
    model = "synthetic:tag"
    endpoint = "http://127.0.0.1:11434"

    def __init__(self, *, error=None, budget=False):
        self.error = error
        self.counter_inputs = []
        self.count_tokens = self._count_tokens
        self.generation_budget = object() if budget else None
        self.base_prompt = lambda _question: "synthetic system prompt"
        self.stream_calls = []

    def _count_tokens(self, text):
        self.counter_inputs.append(text)
        return len(text)

    def generate_stream(self, question, cards, *, user_history=()):
        self.stream_calls.append((question, tuple(cards), tuple(user_history)))
        if self.error is not None:
            raise self.error
        yield "synthetic answer"

    def rewrite_query(self, query, user_turns, *, timeout):
        self.rewrite_call = (query, user_turns, timeout)
        return "synthetic standalone question"


def ask_callback(demo):
    config = demo.get_config_file()
    ask_id = next(
        component["id"]
        for component in config["components"]
        if component["type"] == "button" and component["props"].get("value") == "Ask"
    )
    event = next(
        event
        for event in config["dependencies"]
        if (ask_id, "click") in event["targets"]
    )
    return config, event, demo.fns[event["id"]].fn


def test_followup_receives_bounded_user_history():
    from ktem.local_qa_conversation import ConversationState, OllamaQueryRewriter

    state = ConversationState()
    for turn in (
        "oldest unrelated turn",
        "VPN policy question",
        "VPN reset details",
        "Which operating system?",
    ):
        state = state.append_user(turn, max_turns=3, token_limit=1024, count_tokens=len)
    client = FakeRewriteClient()
    enriched = QueryEnricher(rewriter=OllamaQueryRewriter(client)).enrich(
        "And what about Linux?", user_history=state.user_turns
    )

    assert client.calls == [
        (
            "And what about Linux?",
            ("VPN policy question", "VPN reset details", "Which operating system?"),
            10.0,
        )
    ]
    assert enriched.standalone_query == "VPN reset procedure"
    assert enriched.original_query == "And what about Linux?"


def test_topic_switch_uses_original_question():
    from ktem.local_qa_conversation import OllamaQueryRewriter

    client = FakeRewriteClient(result="VPN reset procedure")
    enriched = QueryEnricher(rewriter=OllamaQueryRewriter(client)).enrich(
        "How do I bake sourdough?", user_history=("VPN policy question",)
    )

    assert client.calls == []
    assert enriched.standalone_query == "How do I bake sourdough?"
    assert enriched.variants[0] == "How do I bake sourdough?"


def test_two_gradio_sessions_are_isolated():
    from ktem.local_qa_conversation import ConversationState

    demo = build_ui(FakeQA(), FakeGenerator(), snapshot_version="synthetic-v3")
    config, ask_event, ask_fn = ask_callback(demo)
    state_component = next(
        component for component in config["components"] if component["type"] == "state"
    )
    assert state_component["props"]["value"].get("user_turns") == ()

    first_state = ConversationState()
    second_state = ConversationState()
    first_updates = list(ask_fn("first session question", first_state, False))
    second_updates = list(ask_fn("second session question", second_state, False))

    assert first_updates[-1][2].user_turns == ("first session question",)
    assert second_updates[-1][2].user_turns == ("second session question",)
    assert first_state.user_turns == second_state.user_turns == ()
    assert state_component["id"] in ask_event["inputs"]


def test_clear_drops_history():
    from ktem.local_qa_conversation import ConversationState
    from ktem.local_qa_playground import clear_session_outputs

    state = ConversationState().append_user(
        "VPN policy question", max_turns=3, token_limit=1024, count_tokens=len
    )

    assert clear_session_outputs(state) == ("", "", [], ConversationState())


def test_failed_generation_does_not_create_assistant_evidence():
    from ktem.local_qa_conversation import ConversationState

    qa = FakeQA()
    generator = FakeGenerator(error=TimeoutError("private answer text"))
    demo = build_ui(qa, generator, snapshot_version="synthetic-v3")
    _config, _event, ask_fn = ask_callback(demo)

    updates = list(ask_fn("VPN reset details", ConversationState(), True))
    state = updates[-1][2]

    assert state.user_turns == ("VPN reset details",)
    assert all("private answer text" not in turn for turn in state.user_turns)
    assert qa.calls[0][1]["user_history"] == ()


def test_rewrite_timeout_uses_original():
    from ktem.local_qa_conversation import OllamaQueryRewriter

    client = FakeRewriteClient(error=TimeoutError("rewrite timed out"))
    enriched = QueryEnricher(rewriter=OllamaQueryRewriter(client)).enrich(
        "And for Linux?", user_history=("VPN policy question",)
    )

    assert enriched.standalone_query == "And for Linux?"
    assert enriched.variants[0] == "And for Linux?"
    assert client.calls[0][2] == 10.0


def test_history_budget_uses_same_generator_counter():
    from ktem.local_qa_conversation import ConversationState, OllamaQueryRewriter

    qa = FakeQA()
    generator = FakeGenerator(budget=True)
    demo = build_ui(qa, generator, snapshot_version="synthetic-v3")
    _config, _event, ask_fn = ask_callback(demo)
    history = ConversationState()
    for turn in ("a" * 700, "b" * 400, "c" * 500, "d" * 200):
        history = history.append_user(
            turn,
            max_turns=3,
            token_limit=1024,
            count_tokens=generator.count_tokens,
        )
    expected_history = ("c" * 500, "d" * 200)
    question = "And what about Linux?"

    updates = list(ask_fn(question, history, True))

    assert qa.calls[0][1]["count_tokens"] is generator.count_tokens
    assert "\n".join(expected_history) in generator.counter_inputs
    assert qa.calls[0][0] == question
    assert qa.calls[0][1]["user_history"] == expected_history
    assert isinstance(qa.calls[0][1]["query_rewriter"], OllamaQueryRewriter)
    assert qa.calls[0][1]["query_rewriter"].client is generator
    assert generator.stream_calls[0][0] == question
    assert generator.stream_calls[0][2] == expected_history
    assert updates[-1][2].user_turns == (*expected_history, question)
    assert generator.count_tokens("\n".join(updates[-1][2].user_turns)) <= 1024


class FakeEmbedding(BaseEmbeddings):
    def invoke(self, text, *args, **kwargs):
        return []


def test_followup_cannot_override_current_source_selection(monkeypatch):
    from ktem.index.file import pipelines as file_pipelines

    class FakeService:
        def __init__(self):
            self.search_calls = []

        def chunk_ids_for_sources(self, source_ids):
            return [f"chunk-{source_id}" for source_id in source_ids]

        def search(self, query, **kwargs):
            self.search_calls.append((query, kwargs))
            return []

    service = FakeService()
    client = FakeRewriteClient(result="Search every source for finance records")
    monkeypatch.setattr(
        file_pipelines,
        "create_file_knowledge_service",
        lambda **_kwargs: service,
    )
    monkeypatch.setattr(
        file_pipelines.DocumentRetrievalPipeline,
        "vector_retrieval",
        property(lambda _self: lambda **_kwargs: []),
    )
    pipeline = file_pipelines.DocumentRetrievalPipeline(
        embedding=FakeEmbedding(),
        Source=object,
        Index=object,
        VS=object(),
        DS=object(),
        user_id="synthetic-user",
        private=False,
        v3_enabled=True,
        query_enrichment=True,
        query_enricher=QueryEnricher(
            rewriter=lambda query, history: client.rewrite_query(
                query, history, timeout=10.0
            )
        ),
    )

    pipeline.run(
        "And what about Linux?",
        doc_ids=["currently-selected-source"],
        user_history=("VPN policy question",),
    )

    query, search_kwargs = service.search_calls[0]
    assert query == "And what about Linux?"
    assert search_kwargs["allowed_source_ids"] == ["currently-selected-source"]
    assert search_kwargs["enriched_query"].standalone_query == (
        "Search every source for finance records"
    )
    assert search_kwargs["enriched_query"].original_query == query
    assert client.calls[0][1] == ("VPN policy question",)


def test_product_retrieval_uses_only_bounded_user_turns_from_chat_history():
    from ktem.reasoning.simple import FullQAPipeline

    class HistoryRetriever:
        v3_enabled = True
        query_enrichment = True

        def __init__(self):
            self.calls = []

        def __call__(self, **kwargs):
            self.calls.append(kwargs)
            return [RetrievedDocument(id_="chunk-a", text="evidence", metadata={})]

    retriever = HistoryRetriever()
    pipeline = FullQAPipeline(
        retrievers=[retriever],
        evidence_pipeline=PrepareEvidencePipeline(
            max_context_length=200, token_counter=len
        ),
    )
    pipeline._prepare_child = lambda child, _name: child
    history = [
        ("older question", "assistant answer that must not be rewrite evidence"),
        ("VPN policy?", "assistant output A"),
        ("VPN resets?", "assistant output B"),
        ("Linux or Windows?", "assistant output C"),
        ("What about Linux?", "assistant output D"),
    ]

    pipeline.retrieve("And what about this?", history)

    assert retriever.calls[0]["user_history"] == (
        "VPN resets?",
        "Linux or Windows?",
        "What about Linux?",
    )
    assert all(
        "assistant output" not in turn for turn in retriever.calls[0]["user_history"]
    )
