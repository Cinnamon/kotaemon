from kotaemon.base import HumanMessage, SystemMessage
from kotaemon.evaluate.utils import re_0_10_rating
from kotaemon.llms import BaseLLM, PromptTemplate

from .base import GroundednessEvaluator

SYSTEM_PROMPT_TEMPLATE: PromptTemplate = PromptTemplate(
    """You are a INFORMATION OVERLAP classifier; providing the overlap of information between the source and statement.
    Respond only as a number from 0 to 10 where 0 is no information overlap and 10 is all information is overlapping.
    Never elaborate."""
)
USER_PROMPT_TEMPLATE: PromptTemplate = PromptTemplate(
    """SOURCE: {premise}

    Hypothesis: {hypothesis}

    Please answer with the template below for all statement sentences:

    Criteria: <Statement Sentence>,
    Supporting Evidence: <Identify and describe the location in the source where the information matches the statement. Provide a detailed, human-readable summary indicating the path or key details. if nothing matches, say NOTHING FOUND>
    Score: <Output a number between 0-10 where 0 is no information overlap and 10 is all information is overlapping>
    """
)


class LLMGroundednessEvaluator(GroundednessEvaluator):
    """
    Class representing an evaluator for groundedness using the LLM model.

    Attributes:
        llm (BaseLLM): The LLM model used for evaluation.
        system_prompt_template (PromptTemplate): The template for system prompts.
        user_prompt_template (PromptTemplate): The template for user prompts.
        normalize (float): The normalization factor for the evaluation result.

    Methods:
        run: Runs the evaluation using the LLM model.

    """

    llm: BaseLLM
    system_prompt_template: PromptTemplate = SYSTEM_PROMPT_TEMPLATE
    user_prompt_template: PromptTemplate = USER_PROMPT_TEMPLATE
    normalize: float = 10

    def run(self, evidence: str, answer: str) -> float:
        """
        Runs the evaluation using the LLM model.

        Args:
            evidence (str): The evidence text.
            answer (str): The answer text.

        Returns:
            float: The evaluation result.

        """
        messages = []
        messages.append(SystemMessage(self.system_prompt_template.populate()))
        messages.append(
            HumanMessage(
                self.user_prompt_template.populate(premise=evidence, hypothesis=answer)
            )
        )
        response = self.llm(messages).text
        result = float(re_0_10_rating(response)) / self.normalize

        return result
