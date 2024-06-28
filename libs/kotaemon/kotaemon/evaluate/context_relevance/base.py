from __future__ import annotations

from abc import abstractmethod

from kotaemon.base import BaseComponent, Document


class ContextRelevanceEvaluator(BaseComponent):
    """
    Base class for context relevance evaluators.

    This class defines the interface for context relevance evaluators.
    Subclasses should implement the `run` method to calculate the relevance
    score of a document given a query.
    """

    @abstractmethod
    def run(self, document: Document, query: str) -> float:
        """
        Calculate the relevance score of a document given a query.

        Args:
            document (Document): The document to evaluate.
            query (str): The query to evaluate against.

        Returns:
            float: The relevance score of the document.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.

        """
        raise NotImplementedError
