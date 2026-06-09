from dataclasses import dataclass, field

import requests
from decouple import config

from kotaemon.base import RetrievedDocument

from .base import BaseWebSearch


@dataclass(kw_only=True)
class JinaWebSearch(BaseWebSearch):
    """Web search via the Jina Search API."""

    api_key: str = field(
        default_factory=lambda: config("JINA_API_KEY", default=""),
        metadata={"description": "Jina API key (https://jina.ai/reader)."},
    )

    def run(self, text: str, *args, **kwargs) -> list[RetrievedDocument]:
        if not self.api_key:
            raise ValueError(
                "This feature requires JINA_API_KEY "
                "(get a free key from https://jina.ai/reader)"
            )

        api_url = f"https://s.jina.ai/{text}"
        headers = {"X-With-Generated-Alt": "true", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        response_dict = response.json()

        return [
            RetrievedDocument(
                text=(
                    "###URL: [{url}]({url})\n\n"
                    "####{title}\n\n{description}\n{content}"
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
