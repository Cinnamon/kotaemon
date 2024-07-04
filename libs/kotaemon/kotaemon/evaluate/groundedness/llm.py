import re

from kotaemon.base import HumanMessage, SystemMessage
from kotaemon.evaluate.utils import re_0_10_rating
from kotaemon.llms import BaseLLM, PromptTemplate

from .base import GroundednessEvaluator

SYSTEM_PROMPT_TEMPLATE: PromptTemplate = PromptTemplate("You are a helpful assistant.")

CRITERIA = {
    "faithfulness": """
Score 1: The answer directly contradicts the information provided in the reference docs.
Score 3: The answer contains a mix of correct information from the reference docs and incorrect or unverifiable information not found in the docs.
Score 5: The answer is mostly aligned with the reference docs but includes extra information that, while not contradictory, is not verified by the docs.
Score 7: The answer aligns well with the reference docs but includes minor, commonly accepted facts not found in the docs.
Score 10: The answer perfectly aligns with and is fully entailed by the reference docs, with no extra information."""
}

SCORING_TEMPLATE_WITH_REFERENCE: PromptTemplate = PromptTemplate(
    "[Instruction]\nPlease act as an impartial judge \
and evaluate the quality of the response provided by an AI \
assistant to the user question displayed below. {criteria}"
    '[Ground truth]\n{reference}\nBegin your evaluation \
by providing a short explanation. Be as objective as possible. \
After providing your explanation, you must rate the response on a scale of 1 to 10 \
by strictly following this format: "[[rating]]", for example: "Rating: [[5]]".\n\n\
[Question]\n{input}\n\n[The Start of Assistant\'s Answer]\n{prediction}\n\
[The End of Assistant\'s Answer]',
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
    user_prompt_template: PromptTemplate = SCORING_TEMPLATE_WITH_REFERENCE
    normalize: float = 10
    result_format: str = r"Rating: \[\[(\d+)\]\]"

    def run(self, evidence: str, query: str, answer: str) -> float:
        """
        Runs the evaluation using the LLM model.

        Args:
            evidence (str): The evidence text.
            query (str): The query string
            answer (str): The answer text.

        Returns:
            float: The evaluation result.

        """
        messages = []
        messages.append(SystemMessage(self.system_prompt_template.populate()))
        criteria_str = "\n".join(f"{k}: {v}" for k, v in CRITERIA.items()).strip()
        docs_string = f"Reference docs:\n<DOCS>\n{evidence}\n</DOCS>\n\n"
        messages.append(
            HumanMessage(
                self.user_prompt_template.populate(
                    input=query,
                    prediction=answer,
                    reference=docs_string,
                    criteria=criteria_str,
                )
            )
        )
        response = self.llm(messages).text
        if self.result_format:
            match = re.search(self.result_format, response)
            if match is not None:
                response = match.group(1)

        result = float(re_0_10_rating(response)) / self.normalize

        return result
