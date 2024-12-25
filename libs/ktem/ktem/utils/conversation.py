import re


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


def get_file_names_regex(input_str: str) -> tuple[list[str], str]:
    # get all file names with pattern @"filename" in input_str
    # also remove these file names from input_str
    pattern = r'@"([^"]*)"'
    matches = re.findall(pattern, input_str)
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
