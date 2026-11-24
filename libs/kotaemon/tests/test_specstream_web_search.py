from unittest.mock import MagicMock, patch

import pytest

from kotaemon.indices.retrievers import specstream_web_search


def test_specstream_web_search_requires_api_key(monkeypatch):
    monkeypatch.setattr(specstream_web_search, "SPECSTREAM_API_KEY", "")
    monkeypatch.setattr(specstream_web_search, "config", lambda key, default="": "")
    retriever = specstream_web_search.WebSearch()
    with pytest.raises(ValueError, match="SPECSTREAM_API_KEY"):
        retriever.run("python release notes")


def test_specstream_web_search_returns_documents(monkeypatch):
    monkeypatch.setattr(specstream_web_search, "SPECSTREAM_API_KEY", "test-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "sources": [
            {
                "url": "https://example.com/a",
                "title": "Example A",
                "snippet": "Short snippet",
                "excerpt": "Detailed excerpt",
            },
            {
                "url": "https://example.com/b",
                "title": "Example B",
                "snippet": "Fallback snippet",
            },
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch.object(specstream_web_search.requests, "post", return_value=mock_resp) as mock_post:
        retriever = specstream_web_search.WebSearch(num=5)
        docs = retriever.run("example query")

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert call_kwargs["json"] == {"q": "example query", "num": 5, "speed": "default"}
    assert len(docs) == 2
    assert "Detailed excerpt" in docs[0].text
    assert "https://example.com/a" in docs[0].text
    assert "Fallback snippet" in docs[1].text
    assert retriever.generate_relevant_scores("q", docs) == docs
