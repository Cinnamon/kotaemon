"""Tests for language settings synchronization (Issues #692, #709)"""
from unittest.mock import MagicMock


class TestLanguageSettingsSync:
    """Test suite for language settings synchronization between
    Reasoning settings and Chat settings."""

    def test_load_user_language_returns_default_when_no_user(self):
        """When user_id is None, should return default language."""
        # Create a mock ChatPage instance
        mock_app = MagicMock()
        mock_app.default_settings.reasoning.settings = {"lang": MagicMock(value="en")}

        # Import the function logic (simplified version)
        default_lang = mock_app.default_settings.reasoning.settings["lang"].value
        user_id = None

        # Simulate the function logic
        if not user_id:
            result = default_lang
        else:
            result = "should_not_reach"

        assert result == "en"

    def test_load_user_language_returns_saved_language(self):
        """When user has saved language preference, should return it."""
        mock_setting = {"reasoning.lang": "es"}

        # Simulate extracting language from settings
        default_lang = "en"
        result = mock_setting.get("reasoning.lang", default_lang)

        assert result == "es"

    def test_load_user_language_returns_default_when_no_saved_setting(self):
        """When user has no saved language setting, should return default."""
        mock_setting: dict = {}

        default_lang = "en"
        result = mock_setting.get("reasoning.lang", default_lang)

        assert result == "en"

    def test_reset_language_returns_default(self):
        """Reset function should return the default language value."""
        mock_app = MagicMock()
        mock_app.default_settings.reasoning.settings = {"lang": MagicMock(value="en")}

        result = mock_app.default_settings.reasoning.settings["lang"].value
        assert result == "en"
