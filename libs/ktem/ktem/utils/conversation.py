import re


def _normalize_mention(raw_mention: str) -> str:
    mention = raw_mention.strip()
    if mention.startswith('"') and mention.endswith('"'):
        mention = mention[1:-1].strip()
    return mention


def format_mentions_for_display(input_str: str) -> str:
    """Normalize and bold @ mentions for chat display."""
    mention_pattern = r'(?:(?<=\s)|^)@(?:"[^"]+"|WebSearch)'

    def _replace(match: re.Match[str]) -> str:
        raw_match = match.group(0)
        raw_mention = raw_match[1:]
        mention = _normalize_mention(raw_mention)
        if not mention:
            return raw_match
        return f"**@{mention}**"

    return re.sub(mention_pattern, _replace, input_str)


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
    # get mentions with pattern @"filename" or @WebSearch in input_str
    # also remove these file names from input_str
    pattern = r"(?:(?<=\s)|^)@(?:(\"[^\"]+\")|(WebSearch))"
    matches_raw = re.findall(pattern, input_str)
    matches = []
    for quoted, web in matches_raw:
        raw_mention = quoted if quoted else web
        mention = _normalize_mention(raw_mention)
        if mention:
            matches.append(mention)

    input_str = re.sub(pattern, "", input_str).strip()

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
