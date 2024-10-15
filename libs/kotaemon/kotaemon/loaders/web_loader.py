from pathlib import Path
from typing import Optional

import requests
from decouple import config

from kotaemon.base import Document

from .base import BaseReader

JINA_API_KEY = config("JINA_API_KEY", default="")
JINA_URL = config("JINA_URL", default="https://r.jina.ai/")


class WebReader(BaseReader):
    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        return self.load_data(Path(file_path), extra_info=extra_info, **kwargs)

    def fetch_url(self, url: str):
        # setup the request
        api_url = f"https://r.jina.ai/{url}"
        headers = {
            "X-With-Links-Summary": "true",
        }
        if JINA_API_KEY:
            headers["Authorization"] = f"Bearer {JINA_API_KEY}"

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        data = response.text
        return data

    def load_data(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        file_path = str(file_path)
        output = self.fetch_url(file_path)
        metadata = extra_info or {}

        return [Document(text=output, metadata=metadata)]
