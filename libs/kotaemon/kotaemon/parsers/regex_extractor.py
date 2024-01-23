from __future__ import annotations

import re
from typing import Callable

from kotaemon.base import BaseComponent, Document, ExtractorOutput, Param


class RegexExtractor(BaseComponent):
    """
    Simple class for extracting text from a document using a regex pattern.

    Args:
        pattern (List[str]): The regex pattern(s) to use.
        output_map (dict, optional): A mapping from extracted text to the
            desired output. Defaults to None.
    """

    class Config:
        middleware_switches = {"theflow.middleware.CachingMiddleware": False}

    pattern: list[str]
    output_map: dict[str, str] | Callable[[str], str] = Param(
        default_callback=lambda *_: {}
    )

    def __init__(self, pattern: str | list[str], **kwargs):
        if isinstance(pattern, str):
            pattern = [pattern]
        super().__init__(pattern=pattern, **kwargs)

    @staticmethod
    def run_raw_static(pattern: str, text: str) -> list[str]:
        """
        Finds all non-overlapping occurrences of a pattern in a string.

        Parameters:
            pattern (str): The regular expression pattern to search for.
            text (str): The input string to search in.

        Returns:
            List[str]: A list of all non-overlapping occurrences of the pattern in the
                string.
        """
        return re.findall(pattern, text)

    @staticmethod
    def map_output(text, output_map) -> str:
        """
        Maps the given `text` to its corresponding value in the `output_map` dictionary.

        Parameters:
            text (str): The input text to be mapped.
            output_map (dict): A dictionary containing mapping of input text to output
                values.

        Returns:
            str: The corresponding value from the `output_map` if `text` is found in the
                dictionary, otherwise returns the original `text`.
        """
        if not output_map:
            return text

        if isinstance(output_map, dict):
            return output_map.get(text, text)

        return output_map(text)

    def run_raw(self, text: str) -> ExtractorOutput:
        """
        Matches the raw text against the pattern and rans the output mapping, returning
            an instance of ExtractorOutput.

        Args:
            text (str): The raw text to be processed.

        Returns:
            ExtractorOutput: The processed output as a list of ExtractorOutput.
        """
        output: list[str] = sum(
            [self.run_raw_static(p, text) for p in self.pattern], []
        )
        output = [self.map_output(text, self.output_map) for text in output]

        return ExtractorOutput(
            text=output[0] if output else "",
            matches=output,
            metadata={"origin": "RegexExtractor"},
        )

    def run(
        self, text: str | list[str] | Document | list[Document]
    ) -> list[ExtractorOutput]:
        """Match the input against a pattern and return the output for each input

        Parameters:
            text: contains the input string to be processed

        Returns:
            A list contains the output ExtractorOutput for each input

        Example:
            ```pycon
            >>> document1 = Document(...)
            >>> document2 = Document(...)
            >>> document_batch = [document1, document2]
            >>> batch_output = self(document_batch)
            >>> print(batch_output)
            [output1_document1, output1_document2]
            ```
        """
        # TODO: this conversion seems common
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

        output = []
        for each_input in input_:
            output.append(self.run_raw(each_input))

        return output


class FirstMatchRegexExtractor(RegexExtractor):
    pattern: list[str]

    def run_raw(self, text: str) -> ExtractorOutput:
        for p in self.pattern:
            output = self.run_raw_static(p, text)
            if output:
                output = [self.map_output(text, self.output_map) for text in output]
                return ExtractorOutput(
                    text=output[0],
                    matches=output,
                    metadata={"origin": "FirstMatchRegexExtractor"},
                )

        return ExtractorOutput(
            text=None, matches=[], metadata={"origin": "FirstMatchRegexExtractor"}
        )
