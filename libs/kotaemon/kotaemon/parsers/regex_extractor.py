from __future__ import annotations

import re
from typing import Callable

from kotaemon.base import Document, ExtractorOutput


class RegexExtractor:
    pattern: list[str]
    output_map: dict[str, str] | Callable[[str], str]

    def __init__(
        self,
        pattern: str | list[str],
        *,
        output_map: dict[str, str] | Callable[[str], str] | None = None,
    ) -> None:
        if isinstance(pattern, str):
            pattern = [pattern]
        self.pattern = pattern
        self.output_map = output_map if output_map is not None else {}

    @staticmethod
    def run_raw_static(pattern: str, text: str) -> list[str]:
        return re.findall(pattern, text)

    @staticmethod
    def map_output(text, output_map) -> str:
        if not output_map:
            return text
        if isinstance(output_map, dict):
            return output_map.get(text, text)
        return output_map(text)

    def run_raw(self, text: str) -> ExtractorOutput:
        output: list[str] = sum(
            [self.run_raw_static(p, text) for p in self.pattern], []
        )
        output = [self.map_output(item, self.output_map) for item in output]
        return ExtractorOutput(
            text=output[0] if output else "",
            matches=output,
            metadata={"origin": "RegexExtractor"},
        )

    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[ExtractorOutput]:
        input_: list[str] = []
        if not isinstance(text, list):
            text = [text]
        for item in text:
            if isinstance(item, str):
                input_.append(item)
            elif isinstance(item, Document):
                input_.append(item.text)
            else:
                raise ValueError(
                    f"Invalid input type {type(item)}, should be str or Document"
                )
        return [self.run_raw(each) for each in input_]

    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)


class FirstMatchRegexExtractor(RegexExtractor):
    def run_raw(self, text: str) -> ExtractorOutput:
        for p in self.pattern:
            output = self.run_raw_static(p, text)
            if output:
                output = [
                    self.map_output(item, self.output_map) for item in output
                ]
                return ExtractorOutput(
                    text=output[0],
                    matches=output,
                    metadata={"origin": "FirstMatchRegexExtractor"},
                )
        return ExtractorOutput(
            text=None, matches=[], metadata={"origin": "FirstMatchRegexExtractor"}
        )
