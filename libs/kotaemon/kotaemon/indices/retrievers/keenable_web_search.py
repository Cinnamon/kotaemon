import requests
from decouple import config

from kotaemon.base import BaseComponent, Param, RetrievedDocument

KEENABLE_API_KEY = config("KEENABLE_API_KEY", default="")
KEENABLE_API_BASE = config("KEENABLE_API_BASE", default="https://api.keenable.ai")

# Sent on every request so Keenable can attribute traffic to the app.
# Mandatory on keyless calls.
KEENABLE_APP_TITLE = "kotaemon"


class WebSearch(BaseComponent):
    """WebSearch component for fetching data from the web
    using the Keenable search API (https://keenable.ai)

    Works without an API key through the public endpoint. Setting
    `KEENABLE_API_KEY` switches to the authenticated endpoint, which only
    lifts the rate limits.
    """

    max_results: int = Param(10, help="Number of search results to fetch (1 to 50)")
    snippet_max_length: int = Param(
        2000,
        help=(
            "Approximate maximum length in characters of the page text "
            "returned for each result"
        ),
    )
    timeout: int = Param(30, help="HTTP timeout in seconds")

    def _search(self, query: str) -> list[dict]:
        headers = {
            "Content-Type": "application/json",
            "X-Keenable-Title": KEENABLE_APP_TITLE,
        }
        if KEENABLE_API_KEY:
            api_url = f"{KEENABLE_API_BASE}/v1/search"
            headers["X-API-Key"] = KEENABLE_API_KEY
        else:
            api_url = f"{KEENABLE_API_BASE}/v1/search/public"

        payload = {
            "query": query,
            "max_results": self.max_results,
            "snippet_max_length": self.snippet_max_length,
        }

        response = requests.post(
            api_url, json=payload, headers=headers, timeout=self.timeout
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            try:
                retry_after = response.json().get("retryAfter", retry_after)
            except ValueError:
                pass
            hint = (
                "set KEENABLE_API_KEY to lift the limit"
                if not KEENABLE_API_KEY
                else "try again later"
            )
            raise RuntimeError(
                "Keenable web search rate limit exceeded "
                f"(retry after {retry_after} seconds); {hint}"
            )
        response.raise_for_status()

        return response.json().get("results", [])

    def run(
        self,
        text: str,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        results = self._search(text)

        context = "\n\n".join(
            "###URL: [{url}]({url})\n\n####{title}\n\n{content}".format(
                url=result.get("url", ""),
                title=result.get("title", ""),
                # `snippet` carries the page text; `description` is usually empty
                content=result.get("snippet") or result.get("description") or "",
            )
            for result in results
        )

        return [
            RetrievedDocument(
                text=context,
                metadata={
                    "file_name": "Web search",
                    "type": "table",
                    "llm_trulens_score": 1.0,
                },
            )
        ]

    def generate_relevant_scores(self, text, documents: list[RetrievedDocument]):
        return documents
