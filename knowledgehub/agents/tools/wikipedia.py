from typing import Any, AnyStr, Optional, Type, Union

from pydantic import BaseModel, Field

from kotaemon.base import Document

from .base import BaseTool


class Wiki:
    """Wrapper around wikipedia API."""

    def __init__(self) -> None:
        """Check that wikipedia package is installed."""
        try:
            import wikipedia  # noqa: F401
        except ImportError:
            raise ValueError(
                "Could not import wikipedia python package. "
                "Please install it with `pip install wikipedia`."
            )

    def search(self, search: str) -> Union[str, Document]:
        """Try to search for wiki page.

        If page exists, return the page summary, and a PageWithLookups object.
        If page does not exist, return similar entries.
        """
        import wikipedia

        try:
            page_content = wikipedia.page(search).content
            url = wikipedia.page(search).url
            result: Union[str, Document] = Document(
                text=page_content, metadata={"page": url}
            )
        except wikipedia.PageError:
            result = f"Could not find [{search}]. Similar: {wikipedia.search(search)}"
        except wikipedia.DisambiguationError:
            result = f"Could not find [{search}]. Similar: {wikipedia.search(search)}"
        return result


class WikipediaArgs(BaseModel):
    query: str = Field(..., description="a search query as input to wkipedia")


class WikipediaTool(BaseTool):
    """Tool that adds the capability to query the Wikipedia API."""

    name: str = "wikipedia"
    description: str = (
        "Search engine from Wikipedia, retrieving relevant wiki page. "
        "Useful when you need to get holistic knowledge about people, "
        "places, companies, historical events, or other subjects. "
        "Input should be a search query."
    )
    args_schema: Optional[Type[BaseModel]] = WikipediaArgs
    doc_store: Any = None

    def _run_tool(self, query: AnyStr) -> AnyStr:
        if not self.doc_store:
            self.doc_store = Wiki()
        tool = self.doc_store
        evidence = tool.search(query)
        return evidence
