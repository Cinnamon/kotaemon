from pathlib import Path
from typing import Optional

from kotaemon.base import Document

from .base import BaseReader


class TxtReader(BaseReader):
    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        return self.load_data(Path(file_path), extra_info=extra_info, **kwargs)

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        with open(file_path, "r") as f:
            text = f.read()

        metadata = extra_info or {}
        return [Document(text=text, metadata=metadata)]
