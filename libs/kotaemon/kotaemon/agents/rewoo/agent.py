import logging
import re
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

import tiktoken

from kotaemon.agents.base import BaseAgent
from kotaemon.agents.io import AgentOutput, AgentType, BaseScratchPad
from kotaemon.agents.tools import BaseTool
from kotaemon.agents.utils import get_plugin_response_content
from kotaemon.base import Document, Node, Param
from kotaemon.indices.qa.citation import CitationPipeline
from kotaemon.indices.splitters import TokenSplitter
from kotaemon.llms import BaseLLM, PromptTemplate

from .planner import Planner
from .solver import Solver


class RewooAgent(BaseAgent):
    """Distributive RewooAgent class inherited from BaseAgent.
    Implementing ReWOO paradigm https://arxiv.org/pdf/2305.18323.pdf"""

    name: str = "RewooAgent"
    agent_type: AgentType = AgentType.rewoo
    description: str = "RewooAgent for answering multi-step reasoning questions"
    output_lang: str = "English"
    planner_llm: BaseLLM
    solver_llm: BaseLLM
    prompt_template: dict[str, PromptTemplate] = Param(
        default_callback=lambda _: {},
        help="A dict to supply different prompt to the agent.",
    )
    plugins: list[BaseTool] = Param(
        default_callback=lambda _: [], help="A list of plugins to be used in the model."
    )
    examples: dict[str, str | list[str]] = Param(
        default_callback=lambda _: {}, help="Examples to be used in the agent."
    )
    max_context_length: int = Param(
        default=3000,
        help="Max context length for each tool output.",
    )
    trim_func: TokenSplitter | None = None

    @Node.auto(depends_on=["planner_llm", "plugins", "prompt_template", "examples"])
    def planner(self):
        return Planner(
            model=self.planner_llm,
            plugins=self.plugins,
            prompt_template=self.prompt_template.get("Planner", None),
            examples=self.examples.get("Planner", None),
        )

    @Node.auto(depends_on=["solver_llm", "prompt_template", "examples"])
    def solver(self):
        return Solver(
            model=self.solver_llm,
            prompt_template=self.prompt_template.get("Solver", None),
            examples=self.examples.get("Solver", None),
            output_lang=self.output_lang,
        )

    def _parse_plan_map(
        self, planner_response: str
    ) -> tuple[dict[str, list[str]], dict[str, str]]:
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
            tuple[Dict[str, List[str]], Dict[str, str]]: A list of plan map
        """
        valid_chunk = [
            line
            for line in planner_response.splitlines()
            if line.startswith("#Plan") or line.startswith("#E")
        ]

        plan_to_es: dict[str, list[str]] = dict()
        plans: dict[str, str] = dict()
        prev_key = ""
        for line in valid_chunk:
            key, description = line.split(":", 1)
            key = key.strip()
            if key.startswith("#Plan"):
                plans[key] = description.strip()
                plan_to_es[key] = []
                prev_key = key
            elif key.startswith("#E"):
                plan_to_es[prev_key].append(key)

        return plan_to_es, plans

    def _parse_planner_evidences(
        self, planner_response: str
    ) -> tuple[dict[str, str], list[list[str]]]:
        """
        Parse planner output. This should return a mapping from #E to tool call.
        It should also identify the level of each #E in dependency map.
        Example:
            {
            "#E1": "Tool1", "#E2": "Tool2",
            "#E3": "Tool3", "#E4": "Tool4"
            }, [[#E1, #E2], [#E3, #E4]]

        Returns:
            tuple[dict[str, str], List[List[str]]]:
            A mapping from #E to tool call and a list of levels.
        """
        evidences: dict[str, str] = dict()
        dependence: dict[str, list[str]] = dict()
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
        planner_evidences: dict[str, str],
        worker_evidences: dict[str, str],
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
                print("Tool input: ", tool_input)
                print("Var: ", var)
                print("Worker evidences: ", worker_evidences)
                if var in worker_evidences:
                    tool_input = tool_input.replace(
                        var, worker_evidences.get(var, "") or ""
                    )
            try:
                selected_plugin = self._find_plugin(tool)
                if selected_plugin is None:
                    raise ValueError("Invalid plugin detected")
                tool_response = selected_plugin(tool_input)
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
        planner_evidences: dict[str, str],
        evidences_level: list[list[str]],
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
        worker_evidences: dict[str, str] = dict()
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
                    worker_evidences[resp["e"]] = self._trim_evidence(resp["evidence"])
                output.done()

        return worker_evidences, plugin_cost, plugin_token

    def _find_plugin(self, name: str):
        for p in self.plugins:
            if p.name == name:
                return p

    def _trim_evidence(self, evidence: str):
        evidence_trim_func = (
            self.trim_func
            if self.trim_func
            else TokenSplitter(
                chunk_size=self.max_context_length,
                chunk_overlap=0,
                separator=" ",
                tokenizer=partial(
                    tiktoken.encoding_for_model("gpt-3.5-turbo").encode,
                    allowed_special=set(),
                    disallowed_special="all",
                ),
            )
        )
        if evidence:
            texts = evidence_trim_func([Document(text=evidence)])
            evidence = texts[0].text
            logging.info(f"len (trimmed): {len(evidence)}")
            return evidence

    @BaseAgent.safeguard_run
    def run(self, instruction: str, use_citation: bool = False) -> AgentOutput:
        """
        Run the agent with a given instruction.
        """
        logging.info(f"Running {self.name} with instruction: {instruction}")
        total_cost = 0.0
        total_token = 0

        # Plan
        planner_output = self.planner(instruction)
        planner_text_output = planner_output.text
        plan_to_es, plans = self._parse_plan_map(planner_text_output)
        planner_evidences, evidence_level = self._parse_planner_evidences(
            planner_text_output
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
        solver_output = self.solver(instruction, worker_log)
        solver_output_text = solver_output.text
        if use_citation:
            citation_pipeline = CitationPipeline(llm=self.solver_llm)
            citation = citation_pipeline(context=worker_log, question=instruction)
        else:
            citation = None

        return AgentOutput(
            text=solver_output_text,
            agent_type=self.agent_type,
            status="finished",
            total_tokens=total_token,
            total_cost=total_cost,
            citation=citation,
            metadata={"citation": citation, "worker_log": worker_log},
        )

    def stream(self, instruction: str, use_citation: bool = False):
        """
        Stream the agent with a given instruction.
        """
        logging.info(f"Streaming {self.name} with instruction: {instruction}")
        total_cost = 0.0
        total_token = 0

        # Plan
        planner_output = self.planner(instruction)
        planner_text_output = planner_output.text
        plan_to_es, plans = self._parse_plan_map(planner_text_output)
        planner_evidences, evidence_level = self._parse_planner_evidences(
            planner_text_output
        )

        print("Planner output:", planner_text_output)
        # output planner to info panel
        yield AgentOutput(
            text="",
            agent_type=self.agent_type,
            status="thinking",
            intermediate_steps=[{"planner_log": planner_text_output}],
        )

        # Work
        worker_evidences, plugin_cost, plugin_token = self._get_worker_evidence(
            planner_evidences, evidence_level
        )
        worker_log = ""
        for plan in plan_to_es:
            worker_log += f"{plan}: {plans[plan]}\n"
            current_progress = f"{plan}: {plans[plan]}\n"
            for e in plan_to_es[plan]:
                worker_log += f"#Action: {planner_evidences.get(e, None)}\n"
                worker_log += f"{e}: {worker_evidences[e]}\n"
                current_progress += f"#Action: {planner_evidences.get(e, None)}\n"
                current_progress += f"{e}: {worker_evidences[e]}\n"

            yield AgentOutput(
                text="",
                agent_type=self.agent_type,
                status="thinking",
                intermediate_steps=[{"worker_log": current_progress}],
            )

        # Solve
        solver_response = ""
        for solver_output in self.solver.stream(instruction, worker_log):
            solver_output_text = solver_output.text
            solver_response += solver_output_text
            yield AgentOutput(
                text=solver_output_text,
                agent_type=self.agent_type,
                status="thinking",
            )
        if use_citation:
            citation_pipeline = CitationPipeline(llm=self.solver_llm)
            citation = citation_pipeline.invoke(
                context=worker_log, question=instruction
            )
        else:
            citation = None

        return AgentOutput(
            text="",
            agent_type=self.agent_type,
            status="finished",
            total_tokens=total_token,
            total_cost=total_cost,
            citation=citation,
            metadata={"citation": citation, "worker_log": worker_log},
        )
