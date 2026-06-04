from dataclasses import dataclass, field

from decouple import config

from kotaemon.base import RetrievedDocument

from .base import BaseWebSearch


@dataclass(kw_only=True)
class TavilyWebSearch(BaseWebSearch):
    """Web search via the Tavily API."""

    api_key: str = field(
        default_factory=lambda: config("TAVILY_API_KEY", default=""),
        metadata={"description": "Tavily API key (https://app.tavily.com/)."},
    )

    def run(self, text: str, *args, **kwargs) -> list[RetrievedDocument]:
        if not self.api_key:
            raise ValueError(
                "This feature requires TAVILY_API_KEY "
                "(get a free key from https://app.tavily.com/)"
            )
        try:
            from tavily import TavilyClient
        except ImportError as e:
            raise ImportError(
                "Please install tavily-python: pip install tavily-python"
            ) from e

        client = TavilyClient(api_key=self.api_key)
        results = client.search(query=text, search_depth="advanced")["results"]
        context = "\n\n".join(
            "###URL: [{url}]({url})\n\n{content}".format(
                url=result["url"], content=result["content"]
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
