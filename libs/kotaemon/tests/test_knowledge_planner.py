"""Deterministic source scoping from canonical knowledge metadata."""

import json

import pytest

from kotaemon.indices.knowledge.planning.query_planner import (
    KnowledgeSource,
    QueryPlanner,
)


class MemoryCatalog:
    def __init__(self, sources):
        self.sources = tuple(sources)

    def list_sources(self, allowed_source_ids=None):
        if allowed_source_ids is None:
            return list(self.sources)
        allowed = set(allowed_source_ids)
        return [source for source in self.sources if source.source_id in allowed]


def source(
    source_id,
    *,
    source_type="markdown",
    virtual_path=None,
    document_name=None,
    entity=None,
):
    return KnowledgeSource(
        source_id=source_id,
        source_type=source_type,
        virtual_path=virtual_path,
        document_name=document_name,
        entity=entity or {},
    )


def test_exact_chinese_entity_scopes_to_one_document_and_is_serializable():
    catalog = MemoryCatalog(
        [
            source(
                "zhang-san",
                virtual_path="/RAG/API/张三.md",
                document_name="张三.md",
                entity={"person": "张三"},
            ),
            source(
                "li-si",
                virtual_path="/Frontend/李四.md",
                document_name="李四.md",
                entity={"person": "李四"},
            ),
            source(
                "wang-wu",
                virtual_path="/Automation/王五.md",
                document_name="王五.md",
                entity={"person": "王五"},
            ),
        ]
    )

    plan = QueryPlanner().plan("张三实习期间做了什么工作？", catalog)

    assert plan.source_ids == ("zhang-san",)
    assert plan.virtual_paths == ("/RAG/API/张三.md",)
    assert plan.metadata_filters == {"person": "张三"}
    assert plan.semantic_query == "张三实习期间做了什么工作？"
    assert json.loads(json.dumps(plan.to_dict()))["source_ids"] == ["zhang-san"]


def test_conjoined_chinese_entities_are_ambiguous_and_fall_back_to_global():
    catalog = MemoryCatalog(
        [
            source(
                "zhang-san",
                virtual_path="/people/张三.md",
                document_name="张三.md",
                entity={"person": "张三"},
            ),
            source(
                "li-si",
                virtual_path="/people/李四.md",
                document_name="李四.md",
                entity={"person": "李四"},
            ),
        ]
    )

    plan = QueryPlanner().plan("张三和李四", catalog)

    assert plan.source_ids is None
    assert plan.confidence < QueryPlanner.HIGH_CONFIDENCE
    assert "ambiguous" in plan.reason


def test_chinese_context_prefix_of_a_compound_falls_back_to_global():
    catalog = MemoryCatalog(
        [
            source(
                "zhang-san",
                virtual_path="/people/张三.md",
                document_name="张三.md",
                entity={"person": "张三"},
            )
        ]
    )

    plan = QueryPlanner().plan("张三工作室的职责是什么？", catalog)

    assert plan.source_ids is None
    assert plan.confidence < QueryPlanner.HIGH_CONFIDENCE


def test_chinese_entity_match_does_not_accept_a_longer_partial_name():
    catalog = MemoryCatalog(
        [
            source(
                "zhang-san",
                virtual_path="/people/张三.md",
                document_name="张三.md",
                entity={"person": "张三"},
            )
        ]
    )

    plan = QueryPlanner().plan("张三丰实习期间做了什么工作？", catalog)

    assert plan.source_ids is None
    assert plan.confidence < QueryPlanner.HIGH_CONFIDENCE


def test_longer_chinese_entity_wins_over_its_known_short_prefix():
    catalog = MemoryCatalog(
        [
            source(
                "zhang-san",
                virtual_path="/people/张三.md",
                document_name="张三.md",
                entity={"person": "张三"},
            ),
            source(
                "zhang-sanfeng",
                virtual_path="/people/张三丰.md",
                document_name="张三丰.md",
                entity={"person": "张三丰"},
            ),
        ]
    )

    plan = QueryPlanner().plan("张三丰实习期间做了什么工作？", catalog)

    assert plan.source_ids == ("zhang-sanfeng",)
    assert plan.metadata_filters == {"person": "张三丰"}


def test_duplicate_entity_in_different_branches_falls_back_to_global():
    catalog = MemoryCatalog(
        [
            source(
                "team-a",
                virtual_path="/Team-A/张三.md",
                entity={"person": "张三"},
            ),
            source(
                "team-b",
                virtual_path="/Team-B/张三.md",
                entity={"person": "张三"},
            ),
        ]
    )

    plan = QueryPlanner().plan("张三负责什么？", catalog)

    assert plan.source_ids is None
    assert plan.confidence < QueryPlanner.HIGH_CONFIDENCE
    assert "ambiguous" in plan.reason


def test_explicit_path_type_and_caller_allowlist_are_intersected():
    catalog = MemoryCatalog(
        [
            source(
                "alice-md",
                source_type="markdown",
                virtual_path="/team/app/alice.md",
                entity={"person": "Alice"},
            ),
            source(
                "bob-md",
                source_type="markdown",
                virtual_path="/team/app/bob.md",
                entity={"person": "Bob"},
            ),
            source(
                "alice-pdf",
                source_type="pdf",
                virtual_path="/team/app/alice.pdf",
                entity={"person": "Alice"},
            ),
        ]
    )

    plan = QueryPlanner().plan(
        "Alice summary",
        catalog,
        path="/team/app/alice.md",
        source_types=["markdown"],
        allowed_source_ids=["alice-md", "bob-md"],
    )

    assert plan.source_ids == ("alice-md",)
    assert plan.virtual_paths == ("/team/app/alice.md",)
    assert plan.source_types == ("markdown",)


@pytest.mark.parametrize(
    "catalog",
    [
        MemoryCatalog([KnowledgeSource(source_id="legacy", source_name="张三.md")]),
        MemoryCatalog(
            [
                KnowledgeSource(
                    source_id="malformed",
                    virtual_path="/people/person.md",
                    document_name="person.md",
                    entity={"person": ["张三"]},
                )
            ]
        ),
    ],
    ids=["legacy-metadata", "malformed-entity"],
)
def test_absent_or_malformed_metadata_does_not_create_a_high_confidence_scope(
    catalog,
):
    plan = QueryPlanner().plan("张三在做什么？", catalog)

    assert plan.source_ids is None
    assert plan.confidence < QueryPlanner.HIGH_CONFIDENCE


def test_empty_catalog_returns_an_explicit_empty_scope():
    plan = QueryPlanner().plan("unmatched request", MemoryCatalog([]))

    assert plan.source_ids == ()
    assert plan.confidence >= QueryPlanner.HIGH_CONFIDENCE


def test_unknown_source_type_is_rejected_instead_of_weakening_the_filter():
    with pytest.raises(ValueError, match="Unsupported source type"):
        QueryPlanner().plan("Alice", MemoryCatalog([]), source_types=["archive"])


def test_empty_metadata_filters_do_not_create_an_all_sources_scope():
    catalog = MemoryCatalog(
        [source("alice", virtual_path="/team/alice.md", entity={"person": "Alice"})]
    )

    plan = QueryPlanner().plan("unmatched request", catalog, filters={})

    assert plan.source_ids is None


def test_explicit_unmatched_path_is_an_empty_scope_not_a_global_fallback():
    catalog = MemoryCatalog(
        [source("alice", virtual_path="/team/alice.md", entity={"person": "Alice"})]
    )

    plan = QueryPlanner().plan("Alice", catalog, path="/team/missing.md")

    assert plan.source_ids == ()
    assert plan.confidence >= QueryPlanner.HIGH_CONFIDENCE


def test_empty_caller_visibility_is_an_explicit_empty_scope():
    catalog = MemoryCatalog(
        [source("alice", virtual_path="/team/alice.md", entity={"person": "Alice"})]
    )

    plan = QueryPlanner().plan("Alice", catalog, allowed_source_ids=[])

    assert plan.source_ids == ()
    assert plan.confidence >= QueryPlanner.HIGH_CONFIDENCE


def test_repository_path_segment_uses_exact_token_boundaries():
    catalog = MemoryCatalog(
        [
            source("api", virtual_path="/Engineering/API/overview.md"),
            source("apiary", virtual_path="/Engineering/APIary/overview.md"),
        ]
    )

    plan = QueryPlanner().plan("What is in the API repository?", catalog)

    assert plan.source_ids == ("api",)
