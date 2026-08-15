"""Tests for chat mention and LLM query helpers."""

from __future__ import annotations

import pytest
from ktem.utils.conversation import (
    format_mentions_for_display,
    get_mentions_regex,
    prepare_llm_query,
    strip_display_mentions,
)

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


@pytest.mark.parametrize(
    ("raw", "expected_display"),
    (
        ('@"report.pdf"', "<strong>@report.pdf</strong>"),
        ('@"star*file.pdf"', "<strong>@star*file.pdf</strong>"),
        ('@"under_score.pdf"', "<strong>@under_score.pdf</strong>"),
        ('@"tick`name.pdf"', "<strong>@tick`name.pdf</strong>"),
        ('@"bracket[1].pdf"', "<strong>@bracket[1].pdf</strong>"),
        ("@pic**1.jpeg", "<strong>@pic**1.jpeg</strong>"),
        ('@"pic**1.jpeg"', "<strong>@pic**1.jpeg</strong>"),
    ),
)
def test_format_mentions_use_html_strong(
    raw: str,
    expected_display: str,
) -> None:
    """File names with markdown metacharacters are safe inside HTML mentions."""
    assert format_mentions_for_display(raw) == expected_display


def test_strip_display_mentions_with_special_characters() -> None:
    """Stripping removes HTML mentions that contain metacharacters."""
    display = format_mentions_for_display('Summarize @"pic**1.jpeg"')
    assert strip_display_mentions(display) == "Summarize"
    assert (
        prepare_llm_query(
            display,
            has_selected_files=False,
            default_question=DEFAULT_QUESTION,
        )
        == "Summarize"
    )


def test_get_mentions_regex_unquoted_filename_with_asterisks() -> None:
    """Unquoted @pic**1.jpeg is parsed as a file mention."""
    mentions, text = get_mentions_regex("Summarize @pic**1.jpeg")
    assert mentions == ["pic**1.jpeg"]
    assert text == "Summarize"
