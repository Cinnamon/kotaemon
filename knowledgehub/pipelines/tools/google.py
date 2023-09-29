from typing import AnyStr, Optional, Type

from pydantic import BaseModel, Field

from .base import BaseTool


class GoogleSearchArgs(BaseModel):
    query: str = Field(..., description="a search query")


class GoogleSearchTool(BaseTool):
    name = "google_search"
    description = (
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
        output = ""
        search_results = search(query, advanced=True)
        if search_results:
            output = "\n".join(
                "{} {}".format(item.title, item.description) for item in search_results
            )

        return output
