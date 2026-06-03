import html
import re

from ktem.utils.commands import WEB_SEARCH_COMMAND


def _normalize_mention(raw_mention: str) -> str:
    mention = raw_mention.strip()
    if mention.startswith('"') and mention.endswith('"'):
        mention = mention[1:-1].strip()
    return mention


# Quoted names, @WebSearch, or unquoted tokens (e.g. @pic**1.jpeg).
_MENTION_PATTERN = rf"(?:(?<=\s)|^)@(?:\"[^\"]+\"|{WEB_SEARCH_COMMAND}|[^\s@]+)"

_DISPLAY_MENTION_HTML_PATTERN = r"<strong>@([\s\S]*?)</strong>"


def strip_display_mentions(input_str: str) -> str:
    """Remove @ mentions produced by format_mentions_for_display."""
    return re.sub(_DISPLAY_MENTION_HTML_PATTERN, "", input_str).strip()


def prepare_llm_query(
    display_text: str,
    *,
    has_selected_files: bool,
    default_question: str,
) -> str:
    """Derive the LLM question from a chat bubble display string."""
    text = strip_display_mentions(display_text)
    _, text = get_mentions_regex(text)
    _, text = get_urls(text)
    if not text and has_selected_files:
        return default_question
    return text


def format_mentions_for_display(input_str: str) -> str:
    """Normalize and highlight @ mentions for chat display."""

    def _replace(match: re.Match[str]) -> str:
        raw_match = match.group(0)
        raw_mention = raw_match[1:]
        mention = _normalize_mention(raw_mention)
        if not mention:
            return raw_match
        return f"<strong>@{html.escape(mention)}</strong>"

    return re.sub(_MENTION_PATTERN, _replace, input_str)


def sync_retrieval_n_message(
    messages: list[list[str]],
    retrievals: list[str],
) -> list[str]:
    """Ensure len of  messages history and retrieval history are equal
    Empty string/Truncate will be used in case any difference exist
    """
    n_message = len(messages)  # include previous history
    n_retrieval = min(n_message, len(retrievals))

    diff = n_message - n_retrieval
    retrievals = retrievals[:n_retrieval] + ["" for _ in range(diff)]

    assert len(retrievals) == n_message

    return retrievals


def get_mentions_regex(input_str: str) -> tuple[list[str], str]:
    # get mentions with pattern @"filename", @WebSearch, or @filename
    # also remove these file names from input_str
    matches_raw = re.findall(_MENTION_PATTERN, input_str)
    matches = []
    for raw_match in matches_raw:
        mention = _normalize_mention(raw_match[1:])
        if mention:
            matches.append(mention)

    input_str = re.sub(_MENTION_PATTERN, "", input_str).strip()

    return matches, input_str


def get_urls(input_str: str) -> tuple[list[str], str]:
    # get all urls in input_str
    # also remove these urls from input_str
    pattern = r"https?://[^\s]+"
    matches = re.findall(pattern, input_str)
    input_str = re.sub(pattern, "", input_str).strip()

    return matches, input_str


if __name__ == "__main__":
    print(sync_retrieval_n_message([[""], [""], [""]], []))
