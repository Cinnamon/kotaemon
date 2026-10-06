"""Question/answer units with conservative whole-input fallback."""

import re

from kotaemon.base import Document
from kotaemon.indices.splitters import BaseSplitter

from .base import semantic_unit
from .token import TokenChunkStrategy

_MARKER = re.compile(r"^\s*(Q|Question|A|Answer)\s*:\s*(.*)$", re.IGNORECASE)


class FAQChunkStrategy:
    def __init__(self, token_splitter: BaseSplitter):
        self.fallback = TokenChunkStrategy(token_splitter)

    def split(self, document: Document) -> list[Document]:
        metadata = document.metadata
        if "question" in metadata or "answer" in metadata:
            question, answer = metadata.get("question"), metadata.get("answer")
            if not all(
                isinstance(value, str) and value.strip() for value in (question, answer)
            ):
                return self.fallback.split(document)
            pairs = [(f"Q: {question}\nA: {answer}", question.strip())]
        else:
            pairs = self._parse_pairs(document.text)
            if not pairs:
                return self.fallback.split(document)
        return [
            chunk
            for text, question in pairs
            for chunk in self.fallback.split(semantic_unit(document, text, [question]))
        ]

    @staticmethod
    def _parse_pairs(text: str) -> list[tuple[str, str]]:
        pairs = []
        lines = []
        question = []
        answer = []
        state = None
        for line in text.splitlines():
            match = _MARKER.match(line)
            if match:
                marker, value = match.groups()
                if marker.lower() in {"q", "question"}:
                    if state is not None:
                        if (
                            not "\n".join(question).strip()
                            or not "\n".join(answer).strip()
                        ):
                            return []
                        pairs.append(
                            ("\n".join(lines).strip(), "\n".join(question).strip())
                        )
                    lines, question, answer = [line], [value], []
                    state = "question"
                else:
                    if state != "question":
                        return []
                    lines.append(line)
                    answer = [value]
                    state = "answer"
            elif state is None:
                if line.strip():
                    return []
            else:
                lines.append(line)
                (question if state == "question" else answer).append(line)
        if (
            state != "answer"
            or not "\n".join(question).strip()
            or not "\n".join(answer).strip()
        ):
            return []
        pairs.append(("\n".join(lines).strip(), "\n".join(question).strip()))
        return pairs
