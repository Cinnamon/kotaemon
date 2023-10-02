import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, create_model

from kotaemon.llms.chats.base import ChatLLM
from kotaemon.llms.completions.base import LLM
from kotaemon.prompt.template import PromptTemplate

from ..base import AgentOutput, AgentType, BaseAgent, BaseLLM, BaseTool
from ..output.base import BaseScratchPad
from ..utils import get_plugin_response_content
from .planner import Planner
from .solver import Solver


class RewooAgent(BaseAgent):
    """Distributive RewooAgent class inherited from BaseAgent.
    Implementing ReWOO paradigm https://arxiv.org/pdf/2305.18323.pdf"""

    name: str = "RewooAgent"
    agent_type: AgentType = AgentType.rewoo
    description: str = "RewooAgent for answering multi-step reasoning questions"
    llm: Union[BaseLLM, Dict[str, BaseLLM]]  # {"Planner": xxx, "Solver": xxx}
    prompt_template: Dict[
        str, PromptTemplate
    ] = dict()  # {"Planner": xxx, "Solver": xxx}
    plugins: List[BaseTool] = list()
    examples: Dict[str, Union[str, List[str]]] = dict()
    args_schema: Optional[Type[BaseModel]] = create_model(
        "ReactArgsSchema", instruction=(str, ...)
    )

    def _get_llms(self):
        if isinstance(self.llm, ChatLLM) or isinstance(self.llm, LLM):
            return {"Planner": self.llm, "Solver": self.llm}
        elif (
            isinstance(self.llm, dict)
            and "Planner" in self.llm
            and "Solver" in self.llm
        ):
            return {"Planner": self.llm["Planner"], "Solver": self.llm["Solver"]}
        else:
            raise ValueError("llm must be a BaseLLM or a dict with Planner and Solver.")

    def _parse_plan_map(
        self, planner_response: str
    ) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
        """
        Parse planner output. It should be an n-to-n mapping from Plans to #Es.
        This is because sometimes LLM cannot follow the strict output format.
        Example:
            #Plan1
            #E1
            #E2
        should result in: {"#Plan1": ["#E1", "#E2"]}
        Or:
            #Plan1
            #Plan2
            #E1
        should result in: {"#Plan1": [], "#Plan2": ["#E1"]}
        This function should also return a plan map.

        Returns:
            Tuple[Dict[str, List[str]], Dict[str, str]]: A list of plan map
        """
        valid_chunk = [
            line
            for line in planner_response.splitlines()
            if line.startswith("#Plan") or line.startswith("#E")
        ]

        plan_to_es: Dict[str, List[str]] = dict()
        plans: Dict[str, str] = dict()
        for line in valid_chunk:
            if line.startswith("#Plan"):
                plan = line.split(":", 1)[0].strip()
                plans[plan] = line.split(":", 1)[1].strip()
                plan_to_es[plan] = []
            elif line.startswith("#E"):
                plan_to_es[plan].append(line.split(":", 1)[0].strip())

        return plan_to_es, plans

    def _parse_planner_evidences(
        self, planner_response: str
    ) -> Tuple[Dict[str, str], List[List[str]]]:
        """
        Parse planner output. This should return a mapping from #E to tool call.
        It should also identify the level of each #E in dependency map.
        Example:
            {
            "#E1": "Tool1", "#E2": "Tool2",
            "#E3": "Tool3", "#E4": "Tool4"
            }, [[#E1, #E2], [#E3, #E4]]

        Returns:
            Tuple[dict[str, str], List[List[str]]]:
            A mapping from #E to tool call and a list of levels.
        """
        evidences: Dict[str, str] = dict()
        dependence: Dict[str, List[str]] = dict()
        for line in planner_response.splitlines():
            if line.startswith("#E") and line[2].isdigit():
                e, tool_call = line.split(":", 1)
                e, tool_call = e.strip(), tool_call.strip()
                if len(e) == 3:
                    dependence[e] = []
                    evidences[e] = tool_call
                    for var in re.findall(r"#E\d+", tool_call):
                        if var in evidences:
                            dependence[e].append(var)
                else:
                    evidences[e] = "No evidence found"
        level = []
        while dependence:
            select = [i for i in dependence if not dependence[i]]
            if len(select) == 0:
                raise ValueError("Circular dependency detected.")
            level.append(select)
            for item in select:
                dependence.pop(item)
            for item in dependence:
                for i in select:
                    if i in dependence[item]:
                        dependence[item].remove(i)

        return evidences, level

    def _run_plugin(
        self,
        e: str,
        planner_evidences: Dict[str, str],
        worker_evidences: Dict[str, str],
        output=BaseScratchPad(),
    ):
        """
        Run a plugin for a given evidence.
        This function should also cumulate the cost and tokens.
        """
        result = dict(e=e, plugin_cost=0, plugin_token=0, evidence="")
        tool_call = planner_evidences[e]
        if "[" not in tool_call:
            result["evidence"] = tool_call
        else:
            tool, tool_input = tool_call.split("[", 1)
            tool_input = tool_input[:-1]
            # find variables in input and replace with previous evidences
            for var in re.findall(r"#E\d+", tool_input):
                if var in worker_evidences:
                    tool_input = tool_input.replace(var, worker_evidences.get(var, ""))
            try:
                selected_plugin = self._find_plugin(tool)
                if selected_plugin is None:
                    raise ValueError("Invalid plugin detected")
                tool_response = selected_plugin(tool_input)
                # cumulate agent-as-plugin costs and tokens.
                if isinstance(tool_response, AgentOutput):
                    result["plugin_cost"] = tool_response.cost
                    result["plugin_token"] = tool_response.token_usage
                result["evidence"] = get_plugin_response_content(tool_response)
            except ValueError:
                result["evidence"] = "No evidence found."
            finally:
                output.panel_print(
                    result["evidence"], f"[green] Function Response of [blue]{tool}: "
                )
        return result

    def _get_worker_evidence(
        self,
        planner_evidences: Dict[str, str],
        evidences_level: List[List[str]],
        output=BaseScratchPad(),
    ) -> Any:
        """
        Parallel execution of plugins in DAG for speedup.
        This is one of core benefits of ReWOO agents.

        Args:
            planner_evidences: A mapping from #E to tool call.
            evidences_level: A list of levels of evidences.
                Calculated from DAG of plugin calls.
            output: Output object, defaults to BaseOutput().
        Returns:
            A mapping from #E to tool call.
        """
        worker_evidences: Dict[str, str] = dict()
        plugin_cost, plugin_token = 0.0, 0.0
        with ThreadPoolExecutor() as pool:
            for level in evidences_level:
                results = []
                for e in level:
                    results.append(
                        pool.submit(
                            self._run_plugin,
                            e,
                            planner_evidences,
                            worker_evidences,
                            output,
                        )
                    )
                if len(results) > 1:
                    output.update_status(f"Running tasks {level} in parallel.")
                else:
                    output.update_status(f"Running task {level[0]}.")
                for r in results:
                    resp = r.result()
                    plugin_cost += resp["plugin_cost"]
                    plugin_token += resp["plugin_token"]
                    worker_evidences[resp["e"]] = resp["evidence"]
                output.done()

        return worker_evidences, plugin_cost, plugin_token

    def _find_plugin(self, name: str):
        for p in self.plugins:
            if p.name == name:
                return p

    def _run_tool(self, instruction: str) -> AgentOutput:
        """
        Run the agent with a given instruction.
        """
        logging.info(f"Running {self.name} with instruction: {instruction}")
        total_cost = 0.0
        total_token = 0

        planner_llm = self._get_llms()["Planner"]
        solver_llm = self._get_llms()["Solver"]

        planner = Planner(
            model=planner_llm,
            plugins=self.plugins,
            prompt_template=self.prompt_template.get("Planner", None),
            examples=self.examples.get("Planner", None),
        )
        solver = Solver(
            model=solver_llm,
            prompt_template=self.prompt_template.get("Solver", None),
            examples=self.examples.get("Solver", None),
        )

        # Plan
        planner_output = planner(instruction)
        plannner_text_output = planner_output.text
        plan_to_es, plans = self._parse_plan_map(plannner_text_output)
        planner_evidences, evidence_level = self._parse_planner_evidences(
            plannner_text_output
        )

        # Work
        worker_evidences, plugin_cost, plugin_token = self._get_worker_evidence(
            planner_evidences, evidence_level
        )
        worker_log = ""
        for plan in plan_to_es:
            worker_log += f"{plan}: {plans[plan]}\n"
            for e in plan_to_es[plan]:
                worker_log += f"{e}: {worker_evidences[e]}\n"

        # Solve
        solver_output = solver(instruction, worker_log)
        solver_output_text = solver_output.text

        return AgentOutput(
            output=solver_output_text, cost=total_cost, token_usage=total_token
        )
