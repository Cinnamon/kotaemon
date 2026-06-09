from dataclasses import dataclass
from typing import Any, List, Optional, Union

from kotaemon.agents.base import BaseLLM, BaseTool
from kotaemon.agents.io import BaseScratchPad
from kotaemon.llms import PromptTemplate

from .prompt import few_shot_planner_prompt, zero_shot_planner_prompt


@dataclass(kw_only=True)
class Planner:
    model: BaseLLM
    plugins: List[BaseTool]
    prompt_template: Optional[PromptTemplate] = None
    examples: Optional[Union[str, List[str]]] = None

    def _compose_worker_description(self) -> str:
        return "".join(
            f"{worker.name}[input]: {worker.description}\n" for worker in self.plugins
        )

    def _compose_fewshot_prompt(self) -> str:
        if self.examples is None:
            return ""
        if isinstance(self.examples, str):
            return self.examples
        return "\n\n".join(e.strip("\n") for e in self.examples)

    def _compose_prompt(self, instruction) -> str:
        worker_desctription = self._compose_worker_description()
        fewshot = self._compose_fewshot_prompt()
        if self.prompt_template is not None:
            if "fewshot" in self.prompt_template.placeholders:
                return self.prompt_template.populate(
                    tool_description=worker_desctription,
                    fewshot=fewshot,
                    task=instruction,
                )
            return self.prompt_template.populate(
                tool_description=worker_desctription, task=instruction
            )
        if self.examples is not None:
            return few_shot_planner_prompt.populate(
                tool_description=worker_desctription,
                fewshot=fewshot,
                task=instruction,
            )
        return zero_shot_planner_prompt.populate(
            tool_description=worker_desctription, task=instruction
        )

    def run(self, instruction: str, output: BaseScratchPad = BaseScratchPad()) -> Any:
        output.info("Running Planner")
        prompt = self._compose_prompt(instruction)
        return self.model(prompt)

    def stream(self, instruction: str, output: BaseScratchPad = BaseScratchPad()):
        prompt = self._compose_prompt(instruction)
        try:
            for text in self.model.stream(prompt):
                yield text
        except NotImplementedError:
            yield self.model(prompt)
