import re
from typing import Dict, List

from kotaemon.base import BaseComponent
from kotaemon.documents.base import Document


class RegexExtractor(BaseComponent):
    """
    Simple class for extracting text from a document using a regex pattern.

    Args:
        pattern (str): The regex pattern to use.
        output_map (dict, optional): A mapping from extracted text to the
            desired output. Defaults to None.
    """

    pattern: str
    output_map: Dict[str, str] = {}

    @staticmethod
    def run_raw_static(pattern: str, text: str) -> List[str]:
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

        return output_map.get(text, text)

    def run_raw(self, text: str) -> List[str]:
        """
        Runs the raw text through the static pattern and output mapping, returning a
            list of strings.

        Args:
            text (str): The raw text to be processed.

        Returns:
            List[str]: The processed output as a list of strings.
        """
        output = self.run_raw_static(self.pattern, text)
        output = [self.map_output(text, self.output_map) for text in output]

        return output

    def run_batch_raw(self, text_batch: List[str]) -> List[List[str]]:
        """
        Runs a batch of raw text inputs through the `run_raw()` method and returns the
            output for each input.

        Parameters:
            text_batch (List[str]): A list of raw text inputs to process.

        Returns:
            List[List[str]]: A list of lists containing the output for each input in the
                batch.
        """
        batch_output = [self.run_raw(each_text) for each_text in text_batch]

        return batch_output

    def run_document(self, document: Document) -> List[Document]:
        """
        Run the document through the regex extractor and return a list of extracted
            documents.

        Args:
            document (Document): The input document.

        Returns:
            List[Document]: A list of extracted documents.
        """
        texts = self.run_raw(document.text)
        output = [
            Document(text=text, metadata={**document.metadata, "RegexExtractor": True})
            for text in texts
        ]

        return output

    def run_batch_document(
        self, document_batch: List[Document]
    ) -> List[List[Document]]:
        """
        Runs a batch of documents through the `run_document` function and returns the
            output for each document.


        Parameters:
            document_batch (List[Document]): A list of Document objects representing the
                batch of documents to process.

        Returns:
            List[List[Document]]: A list of lists where each inner list contains the
                output Document for each input Document in the batch.

        Example:
            document1 = Document(...)
            document2 = Document(...)
            document_batch = [document1, document2]
            batch_output = self.run_batch_document(document_batch)
            # batch_output will be [[output1_document1, ...], [output1_document2, ...]]
        """

        batch_output = [
            self.run_document(each_document) for each_document in document_batch
        ]

        return batch_output

    def is_document(self, text) -> bool:
        """
        Check if the given text is an instance of the Document class.

        Args:
            text: The text to check.

        Returns:
            bool: True if the text is an instance of Document, False otherwise.
        """
        if isinstance(text, Document):
            return True

        return False

    def is_batch(self, text) -> bool:
        """
        Check if the given text is a batch of documents.

        Parameters:
            text (List): The text to be checked.

        Returns:
            bool: True if the text is a batch of documents, False otherwise.
        """
        if not isinstance(text, List):
            return False

        if len(set(self.is_document(each_text) for each_text in text)) <= 1:
            return True

        return False
