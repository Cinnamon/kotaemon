import email
from pathlib import Path
from typing import Optional

from llama_index.core.readers.base import BaseReader
from theflow.settings import settings as flowsettings

from kotaemon.base import Document


class HtmlReader(BaseReader):
    """Reader HTML usimg html2text

    Reader behavior:
        - HTML is read with html2text.
        - All of the texts will be split by `page_break_pattern`
        - Each page is extracted as a Document
        - The output is a list of Documents

    Args:
        page_break_pattern (str): Pattern to split the HTML into pages
    """

    def __init__(self, page_break_pattern: Optional[str] = None, *args, **kwargs):
        try:
            import html2text  # noqa
        except ImportError:
            raise ImportError(
                "html2text is not installed. "
                "Please install it using `pip install html2text`"
            )

        self._page_break_pattern: Optional[str] = page_break_pattern
        super().__init__()

    def load_data(
        self, file_path: Path | str, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        """Load data using Html reader

        Args:
            file_path: path to HTML file
            extra_info: extra information passed to this reader during extracting data

        Returns:
            list[Document]: list of documents extracted from the HTML file
        """
        import html2text

        file_path = Path(file_path).resolve()

        with file_path.open("r") as f:
            html_text = "".join([line[:-1] for line in f.readlines()])

        # read HTML
        all_text = html2text.html2text(html_text)
        pages = (
            all_text.split(self._page_break_pattern)
            if self._page_break_pattern
            else [all_text]
        )

        extra_info = extra_info or {}

        # create Document from non-table text
        documents = [
            Document(
                text=page.strip(),
                metadata={"page_label": page_id + 1, **extra_info},
            )
            for page_id, page in enumerate(pages)
        ]

        return documents


class MhtmlReader(BaseReader):
    """Parse `MHTML` files with `BeautifulSoup`."""

    def __init__(
        self,
        cache_dir: Optional[str] = getattr(
            flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None
        ),
        open_encoding: Optional[str] = None,
        bs_kwargs: Optional[dict] = None,
        get_text_separator: str = "",
    ) -> None:
        """initialize with path, and optionally, file encoding to use, and any kwargs
        to pass to the BeautifulSoup object.

        Args:
            cache_dir: Path for markdwon format.
            file_path: Path to file to load.
            open_encoding: The encoding to use when opening the file.
            bs_kwargs: Any kwargs to pass to the BeautifulSoup object.
            get_text_separator: The separator to use when getting the text
                from the soup.
        """
        try:
            import bs4  # noqa:F401
        except ImportError:
            raise ImportError(
                "beautifulsoup4 package not found, please install it with "
                "`pip install beautifulsoup4`"
            )

        self.cache_dir = cache_dir
        self.open_encoding = open_encoding
        if bs_kwargs is None:
            bs_kwargs = {"features": "lxml"}
        self.bs_kwargs = bs_kwargs
        self.get_text_separator = get_text_separator

    def load_data(
        self, file_path: Path | str, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        """Load MHTML document into document objects."""

        from bs4 import BeautifulSoup

        extra_info = extra_info or {}
        metadata: dict = extra_info
        page = []
        file_name = Path(file_path)
        with open(file_path, "r", encoding=self.open_encoding) as f:
            message = email.message_from_string(f.read())
            parts = message.get_payload()

            if not isinstance(parts, list):
                parts = [message]

            for part in parts:
                if part.get_content_type() == "text/html":
                    html = part.get_payload(decode=True).decode()

                    soup = BeautifulSoup(html, **self.bs_kwargs)
                    text = soup.get_text(self.get_text_separator)

                    if soup.title:
                        title = str(soup.title.string)
                    else:
                        title = ""

                    metadata = {
                        "source": str(file_path),
                        "title": title,
                        **extra_info,
                    }
                    lines = [line for line in text.split("\n") if line.strip()]
                    text = "\n\n".join(lines)
                    if text:
                        page.append(text)
        # save the page into markdown format
        print(self.cache_dir)
        if self.cache_dir is not None:
            print(Path(self.cache_dir) / f"{file_name.stem}.md")
            with open(Path(self.cache_dir) / f"{file_name.stem}.md", "w") as f:
                f.write(page[0])

        return [Document(text="\n\n".join(page), metadata=metadata)]
