from unittest.mock import MagicMock, patch

import pytest
import requests

from kotaemon.base import RetrievedDocument
from kotaemon.indices.retrievers import keenable_web_search
from kotaemon.indices.retrievers.keenable_web_search import WebSearch

KEENABLE_RESPONSE = {
    "query": "Cinnamon AI",
    "results": [
        {
            "title": "Cinnamon AI",
            "url": "https://www.cinnamon.is/en/",
            "description": "",
            "snippet": "Cinnamon AI is an enterprise AI company.",
            "acquired_at": "2026-09-01T00:00:00Z",
        },
        {
            "title": "kotaemon",
            "url": "https://github.com/Cinnamon/kotaemon",
            "description": "An open-source RAG UI.",
            "snippet": "",
            "acquired_at": "2026-09-01T00:00:00Z",
        },
    ],
}


def _mock_response(status_code=200, json_data=None, headers=None):
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.headers = headers or {}
    response.json.return_value = json_data if json_data is not None else {}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} error"
        )
    return response


@patch("kotaemon.indices.retrievers.keenable_web_search.requests.post")
def test_keenable_web_search_keyless(mock_post, monkeypatch):
    monkeypatch.setattr(keenable_web_search, "KEENABLE_API_KEY", "")
    mock_post.return_value = _mock_response(json_data=KEENABLE_RESPONSE)

    documents = WebSearch(max_results=5)("Cinnamon AI")

    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert mock_post.call_args[0][0].endswith("/v1/search/public")
    assert kwargs["headers"]["X-Keenable-Title"] == "kotaemon"
    assert "X-API-Key" not in kwargs["headers"]
    assert kwargs["json"] == {
        "query": "Cinnamon AI",
        "max_results": 5,
        "snippet_max_length": 2000,
    }

    assert len(documents) == 1
    assert isinstance(documents[0], RetrievedDocument)
    assert documents[0].metadata["file_name"] == "Web search"
    # page text comes from `snippet`, falling back to `description`
    assert "https://www.cinnamon.is/en/" in documents[0].text
    assert "Cinnamon AI is an enterprise AI company." in documents[0].text
    assert "An open-source RAG UI." in documents[0].text


@patch("kotaemon.indices.retrievers.keenable_web_search.requests.post")
def test_keenable_web_search_with_api_key(mock_post, monkeypatch):
    monkeypatch.setattr(keenable_web_search, "KEENABLE_API_KEY", "test-key")
    mock_post.return_value = _mock_response(json_data=KEENABLE_RESPONSE)

    WebSearch()("Cinnamon AI")

    _, kwargs = mock_post.call_args
    assert mock_post.call_args[0][0].endswith("/v1/search")
    assert kwargs["headers"]["X-API-Key"] == "test-key"
    assert kwargs["headers"]["X-Keenable-Title"] == "kotaemon"


@patch("kotaemon.indices.retrievers.keenable_web_search.requests.post")
def test_keenable_web_search_rate_limited(mock_post, monkeypatch):
    monkeypatch.setattr(keenable_web_search, "KEENABLE_API_KEY", "")
    mock_post.return_value = _mock_response(
        status_code=429,
        json_data={
            "error": "Rate limit exceeded",
            "message": "Too many requests",
            "retryAfter": 7,
        },
    )

    with pytest.raises(RuntimeError, match="rate limit exceeded.*7"):
        WebSearch()("Cinnamon AI")
