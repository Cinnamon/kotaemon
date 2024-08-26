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


if __name__ == "__main__":
    print(sync_retrieval_n_message([[""], [""], [""]], []))
