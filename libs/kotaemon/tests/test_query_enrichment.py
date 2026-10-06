from __future__ import annotations

from dataclasses import fields

import pytest

from kotaemon.indices.knowledge.planning.query_enrichment import QueryEnricher


def test_enrichment_retains_original_and_exact_code_path_and_version():
    query = "How do I configure `BGE-M3` using docs/models/v1.2/config.yaml?"

    enriched = QueryEnricher().enrich(query)

    assert enriched.original_query == query
    assert enriched.standalone_query == query
    assert enriched.variants[0] == enriched.standalone_query
    assert query in enriched.variants
    lexical_variants = [variant for variant in enriched.variants if variant != query]
    assert lexical_variants
    lexical_variant = lexical_variants[0]
    assert "BGE-M3" in lexical_variant
    assert "docs/models/v1.2/config.yaml" in lexical_variant
    assert "v1.2" in lexical_variant
    assert len(enriched.variants) <= 3


@pytest.mark.parametrize("rewritten", ["   ", None, 42])
def test_invalid_rewriter_output_falls_back_to_original(rewritten):
    enriched = QueryEnricher(rewriter=lambda _query, _history: rewritten).enrich(
        "And what about Linux?", user_history=("VPN reset policy?",)
    )

    assert enriched.standalone_query == "And what about Linux?"
    assert enriched.variants[0] == "And what about Linux?"
    assert "And what about Linux?" in enriched.variants


def test_rewriter_exception_falls_back_to_original():
    def broken_rewriter(_query, _history):
        raise RuntimeError("rewrite failed")

    enriched = QueryEnricher(rewriter=broken_rewriter).enrich(
        "And what about Linux?", user_history=("recent user turn",)
    )

    assert enriched.standalone_query == "And what about Linux?"
    assert enriched.variants[0] == "And what about Linux?"


def test_rewriter_receives_only_bounded_user_turns():
    calls = []

    def rewriter(query, user_turns):
        calls.append((query, user_turns))
        return "standalone follow-up"

    enriched = QueryEnricher(rewriter=rewriter).enrich(
        "and what about Linux?",
        user_history=(
            "older user turn",
            "user turn one",
            "user turn two",
            "user turn three",
        ),
    )

    assert calls == [
        (
            "and what about Linux?",
            ("user turn one", "user turn two", "user turn three"),
        )
    ]
    assert enriched.original_query == "and what about Linux?"
    assert enriched.standalone_query == "standalone follow-up"
    assert enriched.variants[0] == enriched.standalone_query
    assert enriched.original_query in enriched.variants


def test_enrichment_contract_has_no_authority_or_scope_fields():
    enriched = QueryEnricher().enrich("question")

    assert {field.name for field in fields(enriched)} == {
        "original_query",
        "standalone_query",
        "variants",
        "reason",
    }


def test_rewritten_and_original_routes_are_unique_under_normalization():
    enriched = QueryEnricher(
        rewriter=lambda _query, _history: "  AND WHAT ABOUT LINUX?  ", max_variants=2
    ).enrich("And what about Linux?", user_history=("VPN reset policy?",))

    assert enriched.variants == ("And what about Linux?",)


@pytest.mark.parametrize(
    "question", ["And what about Linux?", "What about Linux…", "那 VPN 呢？"]
)
def test_rewriter_runs_for_explicit_follow_up_markers(question):
    calls = []

    def rewriter(query, user_turns):
        calls.append((query, user_turns))
        return "standalone follow-up"

    enriched = QueryEnricher(rewriter=rewriter).enrich(
        question, user_history=("VPN reset policy?",)
    )

    assert calls == [(question, ("VPN reset policy?",))]
    assert enriched.standalone_query == "standalone follow-up"


@pytest.mark.parametrize(
    "question",
    ["How do I configure Linux VPN?", "What does the VPN policy require?"],
)
def test_standalone_topic_does_not_use_history_rewriter(question):
    calls = []
    enriched = QueryEnricher(
        rewriter=lambda query, turns: calls.append((query, turns)) or "wrong topic"
    ).enrich(question, user_history=("VPN reset policy?",))

    assert calls == []
    assert enriched.original_query == question
    assert enriched.standalone_query == question
