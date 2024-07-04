from __future__ import annotations

from abc import abstractmethod

from kotaemon.base import BaseComponent


class GroundednessEvaluator(BaseComponent):
    """
    Abstract base class for groundedness evaluators.

    Subclasses of GroundnessEvaluator should implement the `run` method,
    which takes an evidence string and an answer string as input and returns
    a float value representing the groundedness score.
    """

    @abstractmethod
    def run(self, evidence: str, query: str, answer: str) -> float:
        """
        Calculate the groundedness score for the given evidence and answer.

        Parameters:
            evidence (str): The evidence string.
            query (str): The query string
            answer (str): The answer string.

        Returns:
            float: The groundedness score. Value range is [0, 1]

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError
