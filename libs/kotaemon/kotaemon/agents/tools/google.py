from typing import AnyStr, Optional, Type
from urllib.error import HTTPError

from langchain_community.utilities import SerpAPIWrapper
from pydantic import BaseModel, Field

from .base import BaseTool


class GoogleSearchArgs(BaseModel):
    query: str = Field(..., description="a search query")


class GoogleSearchTool(BaseTool):
    name: str = "google_search"
    description: str = (
        "A search engine retrieving top search results as snippets from Google. "
        "Input should be a search query."
    )
    args_schema: Optional[Type[BaseModel]] = GoogleSearchArgs

    def _run_tool(self, query: AnyStr) -> str:
        try:
            from googlesearch import search
        except ImportError:
            raise ImportError(
                "install googlesearch using `pip3 install googlesearch-python` to "
                "use this tool"
            )

        try:
            output = ""
            search_results = search(query, advanced=True)
            if search_results:
                output = "\n".join(
                    "{} {}".format(item.title, item.description)
                    for item in search_results
                )
        except HTTPError:
            output = "No evidence found."

        return output


class SerpTool(BaseTool):
    name = "google_search"
    description = (
        "Worker that searches results from Google. Useful when you need to find short "
        "and succinct answers about a specific topic. Input should be a search query."
    )
    args_schema: Optional[Type[BaseModel]] = GoogleSearchArgs

    def _run_tool(self, query: AnyStr) -> str:
        tool = SerpAPIWrapper()
        evidence = tool.run(query)

        return evidence
