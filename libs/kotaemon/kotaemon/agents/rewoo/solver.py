from dataclasses import dataclass
from typing import Any, List, Optional, Union

from kotaemon.agents.io import BaseScratchPad
from kotaemon.llms import BaseLLM, PromptTemplate

from .prompt import few_shot_solver_prompt, zero_shot_solver_prompt


@dataclass(kw_only=True)
class Solver:
    model: BaseLLM
    prompt_template: Optional[PromptTemplate] = None
    examples: Optional[Union[str, List[str]]] = None
    output_lang: str = "English"

    def _compose_fewshot_prompt(self) -> str:
        if self.examples is None:
            return ""
        if isinstance(self.examples, str):
            return self.examples
        return "\n\n".join(e.strip("\n") for e in self.examples)

    def _compose_prompt(self, instruction, plan_evidence, output_lang) -> str:
        fewshot = self._compose_fewshot_prompt()
        if self.prompt_template is not None:
            if "fewshot" in self.prompt_template.placeholders:
                return self.prompt_template.populate(
                    plan_evidence=plan_evidence,
                    fewshot=fewshot,
                    task=instruction,
                    lang=output_lang,
                )
            return self.prompt_template.populate(
                plan_evidence=plan_evidence, task=instruction, lang=output_lang
            )
        if self.examples is not None:
            return few_shot_solver_prompt.populate(
                plan_evidence=plan_evidence,
                fewshot=fewshot,
                task=instruction,
                lang=output_lang,
            )
        return zero_shot_solver_prompt.populate(
            plan_evidence=plan_evidence, task=instruction, lang=output_lang
        )

    def run(
        self,
        instruction: str,
        plan_evidence: str,
        output: BaseScratchPad = BaseScratchPad(),
    ) -> Any:
        prompt = self._compose_prompt(instruction, plan_evidence, self.output_lang)
        return self.model(prompt)

    def stream(
        self,
        instruction: str,
        plan_evidence: str,
        output: BaseScratchPad = BaseScratchPad(),
    ) -> Any:
        prompt = self._compose_prompt(instruction, plan_evidence, self.output_lang)
        try:
            for text in self.model.stream(prompt):
                yield text
        except NotImplementedError:
            yield self.model(prompt)
