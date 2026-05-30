"""Tests for chat mention and LLM query helpers."""

from __future__ import annotations

import pytest
from ktem.utils.conversation import format_mentions_for_display, prepare_llm_query

DEFAULT_QUESTION = "What is the summary of this document?"


@pytest.mark.parametrize(
    ("raw", "display", "has_files", "expected"),
    (
        (
            'Summarize @"report.pdf"',
            format_mentions_for_display('Summarize @"report.pdf"'),
            False,
            "Summarize",
        ),
        (
            '@"report.pdf"',
            format_mentions_for_display('@"report.pdf"'),
            True,
            DEFAULT_QUESTION,
        ),
        (
            "plain question",
            "plain question",
            False,
            "plain question",
        ),
        (
            "see https://example.com/doc",
            format_mentions_for_display("see https://example.com/doc"),
            False,
            "see",
        ),
        (
            '@"a.pdf" and @"b.pdf"',
            format_mentions_for_display('@"a.pdf" and @"b.pdf"'),
            True,
            "and",
        ),
    ),
)
def test_prepare_llm_query(
    raw: str,
    display: str,
    has_files: bool,
    expected: str,
) -> None:
    """prepare_llm_query strips display mentions and applies defaults."""
    del raw
    assert (
        prepare_llm_query(
            display,
            has_selected_files=has_files,
            default_question=DEFAULT_QUESTION,
        )
        == expected
    )
