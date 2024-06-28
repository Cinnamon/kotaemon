from kotaemon.base import HumanMessage, SystemMessage
from kotaemon.evaluate.utils import re_0_10_rating
from kotaemon.llms import BaseLLM, PromptTemplate

from .base import AnswerRelevanceEvaluator

SYSTEM_PROMPT_TEMPLATE: PromptTemplate = PromptTemplate(
    """You are a RELEVANCE grader; providing the relevance of the given RESPONSE to the given PROMPT.
    Respond only as a number from 0 to 10 where 0 is the least relevant and 10 is the most relevant.

    A few additional scoring guidelines:

    - Long RESPONSES should score equally well as short RESPONSES.

    - Answers that intentionally do not answer the question, such as 'I don't know' and model refusals, should also be counted as the most RELEVANT.

    - RESPONSE must be relevant to the entire PROMPT to get a score of 10.

    - RELEVANCE score should increase as the RESPONSE provides RELEVANT context to more parts of the PROMPT.

    - RESPONSE that is RELEVANT to none of the PROMPT should get a score of 0.

    - RESPONSE that is RELEVANT to some of the PROMPT should get as score of 2, 3, or 4. Higher score indicates more RELEVANCE.

    - RESPONSE that is RELEVANT to most of the PROMPT should get a score between a 5, 6, 7 or 8. Higher score indicates more RELEVANCE.

    - RESPONSE that is RELEVANT to the entire PROMPT should get a score of 9 or 10.

    - RESPONSE that is RELEVANT and answers the entire PROMPT completely should get a score of 10.

    - RESPONSE that confidently FALSE should get a score of 0.

    - RESPONSE that is only seemingly RELEVANT should get a score of 0.

    - Never elaborate.
    """
)
USER_PROMPT_TEMPLATE: PromptTemplate = PromptTemplate(
    """PROMPT: {prompt}

    RESPONSE: {response}

    RELEVANCE: """
)


class LLMAnswerRelevanceEvaluator(AnswerRelevanceEvaluator):
    """
    Evaluates the relevance of an answer using a Language Model.

    Attributes:
        llm (BaseLLM): The Language Model used for evaluation.
        system_prompt_template (PromptTemplate): The template for the system prompt.
        user_prompt_template (PromptTemplate): The template for the user prompt.
        normalize (float): The normalization factor for the evaluation result.
    """

    llm: BaseLLM
    system_prompt_template: PromptTemplate = SYSTEM_PROMPT_TEMPLATE
    user_prompt_template: PromptTemplate = USER_PROMPT_TEMPLATE
    normalize: float = 10

    def run(self, query: str, answer: str) -> float:
        """
        Runs the evaluation process for the given query and answer.

        Args:
            query (str): The query string.
            answer (str): The answer string.

        Returns:
            float: The relevance score of the answer.
        """
        messages = []
        messages.append(SystemMessage(self.system_prompt_template.populate()))
        messages.append(
            HumanMessage(
                self.user_prompt_template.populate(prompt=query, response=answer)
            )
        )
        response = self.llm(messages).text
        result = float(re_0_10_rating(response)) / self.normalize

        return result
