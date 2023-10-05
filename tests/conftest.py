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
