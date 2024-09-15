import pytest


@pytest.fixture(scope="function")
def mock_google_search(monkeypatch):
    import googlesearch

    def result(*args, **kwargs):
        yield googlesearch.SearchResult(
            url="https://www.cinnamon.is/en/",
            title="Cinnamon AI",
            description="Cinnamon AI is an enterprise AI company.",
        )

    monkeypatch.setattr(googlesearch, "search", result)


def if_haystack_not_installed():
    try:
        import haystack  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_sentence_bert_not_installed():
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_sentence_fastembed_not_installed():
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_unstructured_not_installed():
    try:
        import unstructured  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_cohere_not_installed():
    try:
        import cohere  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_llama_cpp_not_installed():
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return True
    else:
        return False


skip_when_haystack_not_installed = pytest.mark.skipif(
    if_haystack_not_installed(), reason="Haystack is not installed"
)

skip_when_sentence_bert_not_installed = pytest.mark.skipif(
    if_sentence_bert_not_installed(), reason="SBert is not installed"
)

skip_when_fastembed_not_installed = pytest.mark.skipif(
    if_sentence_fastembed_not_installed(), reason="fastembed is not installed"
)

skip_when_unstructured_not_installed = pytest.mark.skipif(
    if_unstructured_not_installed(), reason="unstructured is not installed"
)

skip_when_cohere_not_installed = pytest.mark.skipif(
    if_cohere_not_installed(), reason="cohere is not installed"
)

skip_openai_lc_wrapper_test = pytest.mark.skipif(
    True, reason="OpenAI LC wrapper test is skipped"
)

skip_llama_cpp_not_installed = pytest.mark.skipif(
    if_llama_cpp_not_installed(), reason="llama_cpp is not installed"
)
