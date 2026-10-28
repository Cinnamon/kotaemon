"""Tests for the supported output language map."""

from ktem.utils.lang import SUPPORTED_LANGUAGE_MAP


def test_traditional_chinese_is_supported():
    assert SUPPORTED_LANGUAGE_MAP["zh-TW"] == "Traditional Chinese (Taiwan)"


def test_legacy_zh_code_is_kept_as_simplified_chinese():
    # "zh" may already be stored in user settings, so the code must stay valid
    assert SUPPORTED_LANGUAGE_MAP["zh"] == "Simplified Chinese"


def test_language_names_are_unique():
    names = list(SUPPORTED_LANGUAGE_MAP.values())
    assert len(names) == len(set(names))
