"""Markdown/Wiki heading sections without a mandatory parser dependency."""

import re

from kotaemon.base import Document
from kotaemon.indices.splitters import BaseSplitter

from .base import semantic_unit
from .token import TokenChunkStrategy

_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


class MarkdownChunkStrategy:
    def __init__(self, token_splitter: BaseSplitter):
        self.fallback = TokenChunkStrategy(token_splitter)

    def split(self, document: Document) -> list[Document]:
        sections = []
        lines = []
        stack = []
        path = list(document.metadata.get("section_path") or [])
        fence = None
        found_heading = False
        for line in document.text.splitlines(keepends=True):
            fence_match = _FENCE.match(line.rstrip("\r\n"))
            if fence_match:
                marker, rest = fence_match.groups()
                if fence is None:
                    fence = marker
                elif (
                    marker[0] == fence[0]
                    and len(marker) >= len(fence)
                    and not rest.strip()
                ):
                    fence = None
                lines.append(line)
                continue
            heading = _HEADING.match(line.rstrip("\r\n")) if fence is None else None
            if heading:
                if lines and "".join(lines).strip():
                    sections.append(("".join(lines).strip(), path))
                level = len(heading[1])
                title = re.sub(r"[ \t]+#+[ \t]*$", "", heading[2]).strip()
                if not title:
                    return self.fallback.split(document)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                path = [title for _, title in stack]
                lines = [line]
                found_heading = True
            else:
                lines.append(line)
        if fence is not None or not found_heading:
            return self.fallback.split(document)
        if lines and "".join(lines).strip():
            sections.append(("".join(lines).strip(), path))
        return [
            chunk
            for text, section_path in sections
            for chunk in self.fallback.split(
                semantic_unit(document, text, section_path)
            )
        ]
