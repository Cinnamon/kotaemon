from __future__ import annotations

from abc import abstractmethod

from kotaemon.base import BaseComponent


class AnswerRelevanceEvaluator(BaseComponent):
    """
    Base class for answer relevance evaluation.

    This class provides a blueprint for implementing answer relevance evaluators.
    Subclasses should override the `run` method to define the specific evaluation logic.

    Attributes:
        None

    Methods:
        run(query: str, answer: str) -> float:
            Abstract method that evaluates the relevance of an answer to a query.

    """

    @abstractmethod
    def run(self, query: str, answer: str) -> float:
        """
        Abstract method that evaluates the relevance of an answer to a query.

        Args:
            query (str): The query string.
            answer (str): The answer string.

        Returns:
            float: A relevance score indicating the degree of relevance between the query and answer.

        Raises:
            NotImplementedError: This method must be implemented in subclasses.

        """
        raise NotImplementedError
