"""Use reader-reported section, slide and row boundaries conservatively."""

from kotaemon.base import Document
from kotaemon.indices.splitters import BaseSplitter

from .base import semantic_unit
from .token import TokenChunkStrategy


class StructuredChunkStrategy:
    def __init__(self, token_splitter: BaseSplitter):
        self.fallback = TokenChunkStrategy(token_splitter)

    def split(self, document: Document) -> list[Document]:
        metadata = document.metadata
        path = metadata.get("section_path")
        if isinstance(path, str):
            path = [path]
        elif isinstance(path, (list, tuple)):
            path = [str(part) for part in path]
        else:
            path = []
        if metadata.get("source_type") == "ppt":
            slide = metadata.get("slide_number") or metadata.get("page_number")
            if slide is None:
                return self.fallback.split(document)
            title = metadata.get("slide_title") or f"Slide {slide}"
            unit = semantic_unit(document, document.text, path or [str(title)])
            unit.metadata.update(
                slide_number=slide,
                slide_title=str(title),
                presentation=metadata.get("presentation")
                or unit.metadata["document_name"],
            )
        elif metadata.get("source_type") == "excel":
            row = metadata.get("row_number")
            if row is None:
                return self.fallback.split(document)
            path = path or [str(metadata.get("sheet_name", "Sheet")), f"Row {row}"]
            unit = semantic_unit(document, document.text, path)
        else:
            heading = metadata.get("heading")
            if not path and isinstance(heading, str) and heading.strip():
                path = [heading.strip()]
            if not path:
                return self.fallback.split(document)
            unit = semantic_unit(document, document.text, path)
        return self.fallback.split(unit)
