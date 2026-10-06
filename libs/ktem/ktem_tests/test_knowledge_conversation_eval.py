"""Synthetic reviewed-fixture checks for multi-turn retrieval evaluation."""

from __future__ import annotations

import json

import pytest


def _conversation_eval():
    from kotaemon.indices.knowledge.evaluation import combination_eval

    return combination_eval


def test_conversation_fixture_is_separate_and_reviewed(tmp_path):
    fixture_path = tmp_path / "conversation.json"
    fixture = {
        "schema_version": 1,
        "reviewed": True,
        "cases": [
            {
                "case_id": "synthetic-conversation-a",
                "turns": [
                    {
                        "turn_id": "turn-a-1",
                        "question": "Which synthetic service owns VPN reset?",
                        "allowed_source_ids": ["source-a"],
                        "expected_relevant_source_ids": ["source-a"],
                        "expected_anchors": [],
                        "topic_switch": False,
                        "no_answer": False,
                        "path": None,
                        "source_types": ["markdown"],
                        "filters": None,
                    }
                ],
            }
        ],
    }
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    parsed = _conversation_eval().load_conversation_fixture(fixture_path)

    assert parsed.reviewed is True
    assert parsed.cases[0].case_id == "synthetic-conversation-a"
    assert parsed.digest
    assert fixture_path.read_text(encoding="utf-8") == json.dumps(fixture)


def test_conversation_fixture_rejects_unreviewed_and_label_leaking_fields(
    tmp_path,
):
    load = _conversation_eval().load_conversation_fixture
    base_case = {
        "case_id": "synthetic-conversation-a",
        "turns": [
            {
                "turn_id": "turn-a-1",
                "question": "synthetic question",
                "allowed_source_ids": [],
                "expected_relevant_source_ids": [],
                "expected_anchors": [],
                "topic_switch": False,
                "no_answer": True,
                "path": None,
                "source_types": None,
                "filters": None,
            }
        ],
    }
    for reviewed, extra in ((False, {}), (True, {"label": "synthetic-gold"})):
        fixture_path = tmp_path / f"fixture-{reviewed}-{bool(extra)}.json"
        fixture_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "reviewed": reviewed,
                    "cases": [{**base_case, **extra}],
                }
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            load(fixture_path)


def test_conversation_fixture_rejects_unknown_source_ids(tmp_path):
    fixture_path = tmp_path / "conversation.json"
    fixture_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "reviewed": True,
                "cases": [
                    {
                        "case_id": "synthetic-conversation-a",
                        "turns": [
                            {
                                "turn_id": "turn-a-1",
                                "question": "synthetic question",
                                "allowed_source_ids": ["unknown-source"],
                                "expected_relevant_source_ids": [],
                                "expected_anchors": [],
                                "topic_switch": False,
                                "no_answer": True,
                                "path": None,
                                "source_types": None,
                                "filters": None,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    fixture = _conversation_eval().load_conversation_fixture(fixture_path)
    with pytest.raises(ValueError, match="unknown source"):
        _conversation_eval().validate_conversation_fixture_sources(
            fixture, known_source_ids={"source-a"}
        )
