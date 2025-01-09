from decouple import config

from kotaemon.base import BaseComponent, RetrievedDocument

TAVILY_API_KEY = config("TAVILY_API_KEY", default="")


class WebSearch(BaseComponent):
    """WebSearch component for fetching data from the web
    using Jina API
    """

    def run(
        self,
        text: str,
        *args,
        **kwargs,
    ) -> list[RetrievedDocument]:
        if TAVILY_API_KEY == "":
            raise ValueError(
                "This feature requires TAVILY_API_KEY "
                "(get free one from https://app.tavily.com/)"
            )

        try:
            from tavily import TavilyClient
        except ImportError:
            raise ImportError(
                "Please install `pip install tavily-python` to use this feature"
            )

        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        results = tavily_client.search(
            query=text,
            search_depth="advanced",
        )["results"]
        context = "\n\n".join(
            "###URL: [{url}]({url})\n\n{content}".format(
                url=result["url"],
                content=result["content"],
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
