import logging
import ast
import json
import re
from typing import Optional

from kotaemon.agents.base import BaseAgent, BaseLLM
from kotaemon.agents.codeact.prompt import (
    DEFAULT_AUTHORIZED_IMPORTS,
    default_codeact_planning_prompt,
    zero_shot_codeact_prompt,
)
from kotaemon.agents.sandbox.repl import LocalPythonInterpreter
from kotaemon.agents.tools import BaseTool
from kotaemon.agents.typedefs import (
    AgentOutput,
    AgentStatus,
    AgentType,
    EventActionEnd,
    EventActionStart,
    EventAnswer,
    EventFinalResponse,
)
from kotaemon.base import Param
from kotaemon.llms import PromptTemplate

logger = logging.getLogger(__name__)
_TOOL_CALL_MARKER = "__KOTAEMON_TOOL_CALL__"

class CodeActAgent(BaseAgent):
    """
    CodeActAgent uses a continuous stateful Python REPL to interactively
    explore, execute tools, and answer a user prompt.
    """

    name: str = "CodeActAgent"
    agent_type: AgentType = AgentType.CODEACT
    description: str = "CodeActAgent that runs Python via a stateful REPL to solve tasks."
    llm: BaseLLM
    max_iterations: int = Param(default=10, help="Max iterations before giving up.")
    timeout: int = Param(default=60, help="Max wait for interpreter completion per step.")
    prompt_template: Optional[PromptTemplate] = None
    output_lang: str = Param(default="English", help="Language for final answer.")
    authorized_imports: list[str] = Param(
        default_callback=lambda _: list(DEFAULT_AUTHORIZED_IMPORTS),
        help="Whitelisted Python modules available to the agent.",
    )
    planning: bool = Param(default=False, help="Whether to include an initial planning step")
    planning_prompt_template: Optional[PromptTemplate] = None
    intermediate_steps: list[tuple[str, str]] = Param(
        default_callback=lambda _: [],
        help="List of Action Log and observation string",
    )

    def _construct_scratchpad(self, intermediate_steps: list[tuple[str, str]]) -> str:
        thoughts = ""
        for action_log, observation in intermediate_steps:
            thoughts += action_log
            thoughts += f"\nObservation:\n```text\n{observation}\n```\n"
        return thoughts

    def _extract_code_block(self, text: str) -> Optional[str]:
        pattern = r"```python\s*(.*?)\s*```"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _populate_prompt(prompt_template: PromptTemplate, **kwargs) -> str:
        """Populate only keys used by a prompt template to avoid redundant-key warnings."""
        selected_kwargs = {
            key: value for key, value in kwargs.items() if key in prompt_template.placeholders
        }
        return prompt_template.populate(**selected_kwargs)

    def _tool_description(self) -> str:
        if not self.plugins:
            return (
                "1) Python REPL: execute code in a persistent interpreter.\n"
                "2) print(...): emit observation text for the next step.\n"
                "3) final_answer(result): end the loop and return the final answer.\n"
                "No external tools are enabled in this run."
            )

        lines = [
            "1) Python REPL: execute code in a persistent interpreter.",
            "2) print(...): emit observation text for the next step.",
            "3) final_answer(result): end the loop and return the final answer.",
            "4) Enabled external tools (call as Python functions):",
        ]
        for alias, tool in self._resolve_tool_alias_map().items():
            lines.append(f"   - {alias}(...) -> {tool.description}")
        if any(tool.name == "docsearch" for tool in self.plugins):
            lines.append(
                "Important: use docsearch only for internal/uploaded documents; "
                "for public topics like stocks/news, prefer web-capable tools."
            )
        return "\n".join(lines)

    @staticmethod
    def _sanitize_alias(raw_name: str) -> str:
        alias = re.sub(r"\W+", "_", raw_name).strip("_")
        if not alias:
            alias = "tool"
        if alias[0].isdigit():
            alias = f"tool_{alias}"
        return alias

    def _resolve_tool_alias_map(self) -> dict[str, BaseTool]:
        alias_map: dict[str, BaseTool] = {}
        used_aliases: set[str] = set()
        for tool in self.plugins:
            alias = self._sanitize_alias(tool.name)
            base_alias = alias
            idx = 2
            while alias in used_aliases:
                alias = f"{base_alias}_{idx}"
                idx += 1
            used_aliases.add(alias)
            alias_map[alias] = tool
        return alias_map

    @staticmethod
    def _tool_bridge_macro(tool_aliases: list[str]) -> str:
        bridge = [
            "import json as __kota_json",
            "def __emit_tool_call(name, *args, **kwargs):",
            f"    print('{_TOOL_CALL_MARKER}' + __kota_json.dumps({{'name': name, 'args': list(args), 'kwargs': kwargs}}, ensure_ascii=False))",
            "    return None",
        ]
        for alias in tool_aliases:
            bridge.append(f"def {alias}(*args, **kwargs):")
            bridge.append(f"    return __emit_tool_call('{alias}', *args, **kwargs)")
        return "\n".join(bridge)

    @staticmethod
    def _format_tool_observation(value: object, max_chars: int = 4000) -> str:
        if value is None:
            text = "[Tool returned no output]"
        elif hasattr(value, "content"):
            text = str(getattr(value, "content"))
        elif hasattr(value, "text"):
            text = str(getattr(value, "text"))
        else:
            text = str(value)
        if len(text) > max_chars:
            return text[:max_chars] + f"\n... [truncated at {max_chars} chars]"
        return text

    def _invoke_tool(self, tool: BaseTool, args: list, kwargs: dict) -> str:
        try:
            if kwargs:
                tool_input = kwargs
            elif args:
                tool_input = args[0] if len(args) == 1 else " ".join(str(x) for x in args)
            else:
                tool_input = ""
            result = tool.run(tool_input)
            return self._format_tool_observation(result)
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "pip install" in msg or "install " in msg.lower():
                return (
                    "Tool unavailable in current environment. "
                    "Do not install packages from code; choose another enabled tool or reason without it."
                )
            return f"Tool execution failed: {msg}"

    def _extract_and_run_tool_calls(
        self, output: str, tool_alias_map: dict[str, BaseTool]
    ) -> tuple[str, list[str]]:
        cleaned_lines: list[str] = []
        observations: list[str] = []
        for line in output.splitlines():
            if _TOOL_CALL_MARKER not in line:
                cleaned_lines.append(line)
                continue

            payload_str = line.split(_TOOL_CALL_MARKER, 1)[1]
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                observations.append("Tool call parse error: invalid payload")
                continue

            alias = str(payload.get("name", ""))
            args = payload.get("args", [])
            kwargs = payload.get("kwargs", {})
            tool = tool_alias_map.get(alias)
            if tool is None:
                observations.append(
                    f"Tool '{alias}' is not enabled. Use one of: {', '.join(tool_alias_map.keys()) or '[none]'}"
                )
                continue

            obs = self._invoke_tool(tool, args if isinstance(args, list) else [], kwargs if isinstance(kwargs, dict) else {})
            observations.append(f"Tool[{alias}] output:\n{obs}")

        return "\n".join(cleaned_lines), observations

    @staticmethod
    def _normalize_final_answer(raw_answer: str) -> str:
        text = raw_answer.strip()
        if not text:
            return text

        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:  # noqa: BLE001
            try:
                parsed = ast.literal_eval(text)
            except Exception:  # noqa: BLE001
                return text

        if isinstance(parsed, dict):
            for key in ("final_answer", "answer", "result", "output", "response", "text"):
                if key in parsed:
                    return str(parsed[key])
            if len(parsed) == 1:
                return str(next(iter(parsed.values())))
            return text
        if isinstance(parsed, (list, tuple)) and len(parsed) == 1:
            return str(parsed[0])
        return str(parsed)

    def clear(self):
        """
        Clear and reset the agent's memory.
        """
        self.intermediate_steps = []

    def run(self, instruction: str, max_iterations: int | None = None) -> AgentOutput:
        """
        Run the agent to completion.
        """
        last_text = ""
        for event in self.stream(instruction, max_iterations):
            if isinstance(event, EventFinalResponse):
                return AgentOutput(
                    text=event.text,
                    agent_type=self.agent_type,
                    status=event.status,
                    intermediate_steps=event.intermediate_steps or self.intermediate_steps,
                )
            if isinstance(event, EventAnswer):
                last_text = event.text
                
        return AgentOutput(
            text=last_text or "Exceeded max iterations or failed.",
            agent_type=self.agent_type,
            status=AgentStatus.FAILED,
            intermediate_steps=self.intermediate_steps,
        )

    def stream(self, instruction: str, max_iterations: int | None = None):
        """
        Stream agent events token by token or step by step.
        """
        if not max_iterations:
            max_iterations = self.max_iterations

        self.clear()
        prompt_tpl = self.prompt_template or zero_shot_codeact_prompt
        plan_prompt_tpl = self.planning_prompt_template or default_codeact_planning_prompt
        tool_description = self._tool_description()
        authorized_imports = ", ".join(self.authorized_imports)
        tool_alias_map = self._resolve_tool_alias_map()

        if self.planning:
            plan_prompt = self._populate_prompt(
                plan_prompt_tpl,
                instruction=instruction,
                tool_description=tool_description,
                authorized_imports=authorized_imports,
            )
            logger.info("Executing initial planning step.")
            yield EventActionStart(action_name="planning", action_input="", log="Starting initial planning phase...")
            plan_response = self.llm(plan_prompt).text
            # Use formatting similar to smolagents
            plan_record = (
                f"Here are the facts I know and the plan of action that I will follow to solve the task:\\n"
                f"```\\n{plan_response}\\n```"
            )
            self.intermediate_steps.append(("Initial Plan Formulation", plan_record))
            yield EventActionEnd(action_name="planning", action_input="", action_output=plan_record, log=plan_response)


        with LocalPythonInterpreter(timeout=self.timeout) as interp:
            # Inject final_answer macro globally
            macro = (
                "def final_answer(res):\n"
                "    print(f'__FINAL_ANSWER_START__\\n{res}\\n__FINAL_ANSWER_END__')"
            )
            interp(macro)
            if tool_alias_map:
                interp(self._tool_bridge_macro(list(tool_alias_map.keys())))

            for step in range(1, max_iterations + 1):
                scratchpad = self._construct_scratchpad(self.intermediate_steps)
                prompt = self._populate_prompt(
                    prompt_tpl,
                    instruction=instruction,
                    agent_scratchpad=scratchpad,
                    lang=self.output_lang,
                    tool_description=tool_description,
                    authorized_imports=authorized_imports,
                )

                logger.info(f"CodeAct Step {step} Prompt:\n{prompt[-100:]}")
                response = self.llm(prompt)
                response_text = response.text or "[Empty response from LLM]"

                # Parse the generated code block
                code = self._extract_code_block(response_text)

                if code is None:
                    # In case LLM didn't format properly, inform it via observation
                    yield EventActionStart(
                        action_name="thought", 
                        action_input="", 
                        log=response_text
                    )
                    error_msg = "Error: No ```python``` code block found. You MUST write python code to proceed or call final_answer(result)."
                    self.intermediate_steps.append((response_text, error_msg))
                    yield EventActionEnd(
                        action_name="thought", 
                        action_input="", 
                        action_output=error_msg, 
                        log=response_text
                    )
                    continue

                yield EventActionStart(action_name="python", action_input=code, log=response_text)

                # Execute
                result = interp(code)
                output_str = result.stdout
                if result.error:
                    output_str += f"\\nError: {result.error}"
                if result.timed_out:
                    output_str += "\\nExecution timed out."

                cleaned_output, tool_observations = self._extract_and_run_tool_calls(
                    output_str, tool_alias_map
                )
                output_parts = [cleaned_output.strip()] if cleaned_output.strip() else []
                output_parts.extend(tool_observations)
                output_str = "\n\n".join(part for part in output_parts if part).strip()
                
                output_str = output_str.strip()

                # Parse for final_answer match
                final_answer_match = re.search(
                    r"__FINAL_ANSWER_START__\n(.*?)\n__FINAL_ANSWER_END__",
                    output_str,
                    re.DOTALL,
                )
                if final_answer_match:
                    ans = self._normalize_final_answer(final_answer_match.group(1))
                    self.intermediate_steps.append((response_text, output_str))
                    yield EventActionEnd(
                        action_name="python", 
                        action_input=code, 
                        action_output=output_str, 
                        log=response_text
                    )
                    yield EventAnswer(text=ans)
                    yield EventFinalResponse(
                        text=ans,
                        status=AgentStatus.FINISHED,
                        intermediate_steps=self.intermediate_steps,
                        agent_type=self.agent_type,
                        max_iterations=max_iterations,
                    )
                    return
                
                # Else record the observation and move to next step
                if not output_str:
                    output_str = "[No printed output]"

                self.intermediate_steps.append((response_text, output_str))
                yield EventActionEnd(
                    action_name="python", 
                    action_input=code, 
                    action_output=output_str, 
                    log=response_text
                )

        yield EventFinalResponse(
            text="Max iterations reached without a final answer.",
            status=AgentStatus.STOPPED,
            intermediate_steps=self.intermediate_steps,
            agent_type=self.agent_type,
            max_iterations=max_iterations,
        )
