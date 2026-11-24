import requests
from decouple import config

from kotaemon.base import BaseComponent, RetrievedDocument

SPECSTREAM_API_KEY = config("SPECSTREAM_API_KEY", default="")
SPECSTREAM_URL = config(
    "SPECSTREAM_URL", default="https://api.specstream.ai/v1/web-search"
)


class WebSearch(BaseComponent):
    """WebSearch component for fetching live web results using the SpecStream API."""

    num: int = 10
    speed: str = "default"
    timeout: int = 30

    def run(
        self,
        text: str,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        api_key = SPECSTREAM_API_KEY or config("SPECSTREAM_API_KEY", default="")
        if not api_key:
            raise ValueError(
                "This feature requires SPECSTREAM_API_KEY "
                "(get an API key from https://specstream.ai)"
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "q": text,
            "num": kwargs.get("num", self.num),
            "speed": kwargs.get("speed", self.speed),
        }
        response = requests.post(
            SPECSTREAM_URL,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        response_dict = response.json()

        documents = []
        for item in response_dict.get("sources") or []:
            url = item.get("url", "")
            title = item.get("title", "")
            content = item.get("excerpt") or item.get("snippet") or ""
            documents.append(
                RetrievedDocument(
                    text=(
                        "###URL: [{url}]({url})\n\n"
                        "####{title}\n\n"
                        "{content}"
                    ).format(
                        url=url,
                        title=title,
                        content=content,
                    ),
                    metadata={
                        "file_name": "Web search",
                        "type": "table",
                        "llm_trulens_score": 1.0,
                        "url": url,
                        "title": title,
                    },
                )
            )
        return documents

    def generate_relevant_scores(self, text, documents: list[RetrievedDocument]):
        return documents
