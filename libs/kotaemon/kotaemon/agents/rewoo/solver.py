from typing import Any, List, Optional, Union

from kotaemon.agents.io import BaseScratchPad
from kotaemon.base import BaseComponent
from kotaemon.llms import BaseLLM, PromptTemplate

from .prompt import few_shot_solver_prompt, zero_shot_solver_prompt


class Solver(BaseComponent):
    model: BaseLLM
    prompt_template: Optional[PromptTemplate] = None
    examples: Optional[Union[str, List[str]]] = None
    output_lang: str = "English"

    def _compose_fewshot_prompt(self) -> str:
        if self.examples is None:
            return ""
        if isinstance(self.examples, str):
            return self.examples
        else:
            return "\n\n".join([e.strip("\n") for e in self.examples])

    def _compose_prompt(self, instruction, plan_evidence, output_lang) -> str:
        """
        Compose the prompt from template, plan&evidence, examples and instruction.
        """
        fewshot = self._compose_fewshot_prompt()
        if self.prompt_template is not None:
            if "fewshot" in self.prompt_template.placeholders:
                return self.prompt_template.populate(
                    plan_evidence=plan_evidence,
                    fewshot=fewshot,
                    task=instruction,
                    lang=output_lang,
                )
            else:
                return self.prompt_template.populate(
                    plan_evidence=plan_evidence, task=instruction, lang=output_lang
                )
        else:
            if self.examples is not None:
                return few_shot_solver_prompt.populate(
                    plan_evidence=plan_evidence,
                    fewshot=fewshot,
                    task=instruction,
                    lang=output_lang,
                )
            else:
                return zero_shot_solver_prompt.populate(
                    plan_evidence=plan_evidence,
                    task=instruction,
                    lang=output_lang,
                )

    def run(
        self,
        instruction: str,
        plan_evidence: str,
        output: BaseScratchPad = BaseScratchPad(),
    ) -> Any:
        response = None
        output.info("Running Solver")
        output.debug(f"Instruction: {instruction}")
        output.debug(f"Plan Evidence: {plan_evidence}")
        prompt = self._compose_prompt(instruction, plan_evidence, self.output_lang)
        output.debug(f"Prompt: {prompt}")
        try:
            response = self.model(prompt)
            output.info("Solver run successful.")
        except ValueError:
            output.error("Solver failed to retrieve response from LLM")

        return response

    def stream(
        self,
        instruction: str,
        plan_evidence: str,
        output: BaseScratchPad = BaseScratchPad(),
    ) -> Any:
        response = ""
        output.info("Running Solver")
        output.debug(f"Instruction: {instruction}")
        output.debug(f"Plan Evidence: {plan_evidence}")
        prompt = self._compose_prompt(instruction, plan_evidence, self.output_lang)
        output.debug(f"Prompt: {prompt}")
        try:
            for text in self.model.stream(prompt):
                response += text.text
                yield text
            output.info("Planner run successful.")
        except NotImplementedError:
            response = self.model(prompt).text
            output.info("Solver run successful.")
        except ValueError:
            output.error("Solver failed to retrieve response from LLM")

        return response
