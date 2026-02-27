import json
import os
from typing import Any

# Path to locales folder
_LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "locales"
)

# Cache for loaded translations (by language code)
_translations_cache: dict[str, dict] = {}


def _load_locale(lang_code: str) -> dict:
    """Load translations for a specific language from its JSON file.

    Args:
        lang_code: The language code (e.g., 'en', 'ja', 'vi', etc.)

    Returns:
        Dictionary containing translations for the specified language.
    """
    global _translations_cache

    if lang_code in _translations_cache:
        return _translations_cache[lang_code]

    locale_file = os.path.join(_LOCALES_DIR, f"{lang_code}.json")
    try:
        with open(locale_file, "r", encoding="utf-8") as f:
            _translations_cache[lang_code] = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to empty dict if file not found or invalid
        _translations_cache[lang_code] = {}

    return _translations_cache[lang_code]


def _get_nested_value(data: dict, key: str) -> Any:
    """Get a value from nested dict using dot notation.

    Args:
        data: The dictionary to search in
        key: The key in dot notation (e.g., 'chat.conversations')

    Returns:
        The value if found, None otherwise.
    """
    keys = key.split(".")
    value = data
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    return value


def _get_supported_languages() -> dict:
    """Get supported languages from locale files.

    Returns:
        Dictionary mapping language codes to their display names.
    """
    supported = {}

    # Check which locale files exist
    if os.path.exists(_LOCALES_DIR):
        for filename in os.listdir(_LOCALES_DIR):
            if filename.endswith(".json"):
                lang_code = filename[:-5]  # Remove .json extension
                locale_data = _load_locale(lang_code)
                # Get language name from the locale file itself
                lang_name = locale_data.get("language_name", lang_code.capitalize())
                supported[lang_code] = lang_name

    # Ensure at least English is available
    if not supported:
        supported = {"en": "English"}

    return supported


# Load SUPPORTED_LANGUAGE_MAP from locale files
SUPPORTED_LANGUAGE_MAP = _get_supported_languages()


def get_ui_text(key: str, lang_code: str = "en") -> str:
    """Get translated UI text for a given key and language code.

    Args:
        key: The translation key. Can be:
             - Simple key (e.g., 'page', 'preview') for flat structure
             - Dot notation (e.g., 'chat.conversations', 'file_upload.quick_upload')
        lang_code: The language code (e.g., 'en', 'ja', 'vi', etc.)

    Returns:
        The translated string, or the English version if translation is not available,
        or the key itself if no translation is found.
    """
    # Load target language
    lang_translations = _load_locale(lang_code)

    # Try to get value using dot notation
    value = _get_nested_value(lang_translations, key)

    if value is not None and isinstance(value, str):
        return value

    # Fallback to English if available
    if lang_code != "en":
        en_translations = _load_locale("en")
        en_value = _get_nested_value(en_translations, key)
        if en_value is not None and isinstance(en_value, str):
            return en_value

    # Return the key itself as last resort
    return key


def clear_translations_cache() -> None:
    """Clear the translations cache. Useful for reloading translations."""
    global _translations_cache
    _translations_cache = {}
