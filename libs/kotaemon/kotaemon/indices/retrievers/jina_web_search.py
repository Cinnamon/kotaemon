import requests
from decouple import config
from typing import Any

from kotaemon.base import BaseComponent, RetrievedDocument

JINA_API_KEY = config("JINA_API_KEY", default="")
JINA_URL = config("JINA_URL", default="https://r.jina.ai/")


class WebSearch(BaseComponent):
    """WebSearch component for fetching data from the web
    using Jina API
    """

    def __init__(
        self, web_search_url: str = "https://s.jina.ai/", **kwargs: Any
    ) -> None:
        self.web_search_url = web_search_url
        super().__init__(**kwargs)

    def run(
        self,
        text: str,
        *args: Any,
        **kwargs: Any,
    ) -> list[RetrievedDocument]:
        if JINA_API_KEY == "":
            raise ValueError(
                "This feature requires JINA_API_KEY "
                "(get free one from https://jina.ai/reader)"
            )

        # setup the request
        api_url = f"https://s.jina.ai/{text}"
        headers = {"X-With-Generated-Alt": "true", "Accept": "application/json"}
        if JINA_API_KEY:
            headers["Authorization"] = f"Bearer {JINA_API_KEY}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        response_dict = response.json()

        return [
            RetrievedDocument(
                text=(
                    "###URL: [{url}]({url})\n\n####{title}\n\n{description}\n{content}"
                ).format(
                    url=item["url"],
                    title=item["title"],
                    description=item["description"],
                    content=item["content"],
                ),
                metadata={
                    "file_name": "Web search",
                    "type": "table",
                    "llm_trulens_score": 1.0,
                },
            )
            for item in response_dict["data"]
        ]

    def retrieve(
        self, query: str, top_k: int = 5, **kwargs: Any
    ) -> list[RetrievedDocument]:
        return self.run(query, **kwargs)[:top_k]

    def generate_relevant_scores(
        self, text: str, documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        return documents
