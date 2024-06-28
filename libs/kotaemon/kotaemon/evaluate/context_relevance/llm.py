from kotaemon.base import Document, HumanMessage, SystemMessage
from kotaemon.evaluate.utils import re_0_10_rating
from kotaemon.llms import BaseLLM, PromptTemplate

from .base import ContextRelevanceEvaluator

SYSTEM_PROMPT_TEMPLATE = PromptTemplate(
    """You are a RELEVANCE grader; providing the relevance of the given CONTEXT to the given QUESTION.
        Respond only as a number from 0 to 10 where 0 is the least relevant and 10 is the most relevant.

        A few additional scoring guidelines:

        - Long CONTEXTS should score equally well as short CONTEXTS.

        - RELEVANCE score should increase as the CONTEXTS provides more RELEVANT context to the QUESTION.

        - RELEVANCE score should increase as the CONTEXTS provides RELEVANT context to more parts of the QUESTION.

        - CONTEXT that is RELEVANT to some of the QUESTION should score of 2, 3 or 4. Higher score indicates more RELEVANCE.

        - CONTEXT that is RELEVANT to most of the QUESTION should get a score of 5, 6, 7 or 8. Higher score indicates more RELEVANCE.

        - CONTEXT that is RELEVANT to the entire QUESTION should get a score of 9 or 10. Higher score indicates more RELEVANCE.

        - CONTEXT must be relevant and helpful for answering the entire QUESTION to get a score of 10.

        - Never elaborate."""
)

USER_PROMPT_TEMPLATE = PromptTemplate(
    """QUESTION: {question}

        CONTEXT: {context}

        RELEVANCE: """
)


class LLMContextRelevanceEvaluator(ContextRelevanceEvaluator):
    """
    Evaluates the context relevance using a Language Model (LLM).

    Attributes:
        llm (BaseLLM): The Language Model used for evaluation.
        system_prompt_template (PromptTemplate): The template for system prompts.
        user_prompt_template (PromptTemplate): The template for user prompts.
        normalize (float): The normalization factor for the evaluation result.
    """

    llm: BaseLLM
    system_prompt_template: PromptTemplate = SYSTEM_PROMPT_TEMPLATE
    user_prompt_template: PromptTemplate = USER_PROMPT_TEMPLATE
    normalize: float = 10

    def run(self, document: Document, query: str) -> float:
        """
        Runs the context relevance evaluation.

        Args:
            document (Document): The document to evaluate.
            query (str): The query to evaluate against.

        Returns:
            float: The context relevance score.
        """
        messages = []
        messages.append(SystemMessage(self.system_prompt_template.populate()))
        messages.append(
            HumanMessage(
                self.user_prompt_template.populate(
                    question=query, context=document.get_content()
                )
            )
        )
        response = self.llm(messages).text
        result = float(re_0_10_rating(response)) / self.normalize

        return result
