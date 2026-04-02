import logging
from copy import deepcopy
import html
import re

from ktem.llms.manager import llms
from ktem.mcp.manager import mcp_manager
from ktem.reasoning.react import TOOL_REGISTRY
from ktem.reasoning.base import BaseReasoning
from ktem.utils.generator import Generator
from ktem.utils.render import Render
from kotaemon.agents.codeact import CodeActAgent
from kotaemon.agents.codeact.prompt import zero_shot_codeact_prompt
from kotaemon.agents.tools.mcp import create_tools_from_config
from kotaemon.agents.typedefs import (
    EventActionEnd,
    EventActionStart,
    EventAnswer,
    EventFinalResponse,
)
from kotaemon.base import BaseComponent, Document
from kotaemon.llms import PromptTemplate

from ..utils import SUPPORTED_LANGUAGE_MAP

logger = logging.getLogger(__name__)

class CodeActAgentPipeline(BaseReasoning):
    """Question answering pipeline using CodeAct agent."""

    class Config:
        allow_extra = True

    retrievers: list[BaseComponent]
    agent: CodeActAgent = CodeActAgent.withx()
    _step_counter: int = 0

    @staticmethod
    def _extract_thought(log: str) -> str:
        if not log:
            return ""
        return re.sub(r"```python\s*.*?\s*```", "", log, flags=re.DOTALL).strip()

    @staticmethod
    def _extract_thought_from_code(code: str) -> str:
        lines = code.splitlines()
        thought_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not stripped.startswith("#"):
                break
            thought_lines.append(stripped.lstrip("#").strip())
        return "\n".join(thought_lines).strip()

    @staticmethod
    def _to_pre_block(text: str, language: str = "") -> str:
        lang_class = f" class='language-{language}'" if language else ""
        return f"<pre><code{lang_class}>{html.escape(text)}</code></pre>"

    @staticmethod
    def _header_text(thought: str, fallback: str) -> str:
        text = thought.strip() if thought else fallback
        if not text:
            return fallback
        one_line = " ".join(text.split())
        if len(one_line) > 180:
            return one_line[:177] + "..."
        return one_line

    @staticmethod
    def _python_block(code: str) -> str:
        return (
            "<div class='codeact-python-block' "
            "style='border:1px solid #d0d7de;border-radius:8px;background:#f6f8fa;"
            "padding:10px;margin:6px 0 10px 0;'>"
            f"{CodeActAgentPipeline._to_pre_block(code, language='python')}"
            "</div>"
        )

    def _render_codeact_step(self, event: EventActionEnd) -> str:
        thought = self._extract_thought(event.log)
        if not thought and event.action_name == "python":
            thought = self._extract_thought_from_code(event.action_input)

        self._step_counter += 1
        fallback_header = f"CodeAct Step {self._step_counter}"
        header = self._header_text(thought, fallback=fallback_header)
        if event.action_name == "python":
            code_html = self._python_block(event.action_input)
            observation_html = self._to_pre_block(event.action_output, language="text")
            body = (
                "<div class='codeact-panel'>"
                "<p><strong>Code</strong></p>"
                f"{code_html}"
                "<p><strong>Observation</strong></p>"
                f"{observation_html}"
                "</div>"
            )
            return Render.collapsible(
                header=header,
                content=body,
                open=True,
            )

        body = (
            "<div class='codeact-panel'>"
            "<p><strong>Observation</strong></p>"
            f"{self._to_pre_block(event.action_output, language='text')}"
            "</div>"
        )
        return Render.collapsible(
            header=header,
            content=body,
            open=True,
        )

    async def ainvoke(  # type: ignore
        self, message, conv_id: str, history: list, **kwargs  # type: ignore
    ) -> Document:
        
        answer = self.agent(message)
        self.report_output(Document(content=answer.text, channel="chat"))

        intermediate_steps = getattr(answer, "intermediate_steps", [])
        for _, step_output in intermediate_steps:
            self.report_output(Document(content=step_output, channel="info"))

        self.report_output(None)
        return answer

    def stream(self, message, conv_id: str, history: list, **kwargs):
        output_stream = Generator(self.agent.stream(message))
        has_answer = False
        self._step_counter = 0
        for event in output_stream:
            if isinstance(event, EventAnswer):
                has_answer = True
                yield Document(channel="chat", content=event.text)
            elif isinstance(event, EventActionEnd):
                yield Document(
                    channel="info",
                    content=self._render_codeact_step(event),
                )
            elif isinstance(event, EventActionStart):
                if event.action_name == "planning":
                    yield Document(
                        channel="info",
                        content=Render.collapsible(
                            header="CodeAct Planning",
                            content=f"<p>{html.escape(event.log or 'Starting initial planning phase...')}</p>",
                            open=True,
                        ),
                    )
            elif isinstance(event, EventFinalResponse):
                if event.error:
                    yield Document(channel="chat", content=f"Error: {event.error}")
                elif not has_answer:
                    # Fallback: if no answer was streamed but we have a final response, show it.
                    yield Document(channel="chat", content=event.text)

    @classmethod
    def get_pipeline(
        cls, settings: dict, states: dict, retrievers: list | None = None
    ) -> BaseReasoning:
        _id = cls.get_info()["id"]
        prefix = f"reasoning.options.{_id}"

        llm_name = settings[f"{prefix}.llm"]
        llm = llms.get(llm_name, llms.get_default())

        pipeline = CodeActAgentPipeline(retrievers=retrievers or [])
        pipeline.agent.llm = llm
        pipeline.agent.max_iterations = settings[f"{prefix}.max_iterations"]
        pipeline.agent.planning = settings.get(f"{prefix}.planning", False)
        pipeline.agent.output_lang = SUPPORTED_LANGUAGE_MAP.get(
            settings["reasoning.lang"], "English"
        )
        tools = []
        mcp_manager.load()
        for tool_name in settings.get(f"{prefix}.tools", []):
            if tool_name.startswith("[MCP] "):
                server_name = tool_name[len("[MCP] ") :]
                entry = mcp_manager.get(server_name)
                if entry:
                    config = dict(entry["config"])
                    enabled_tools = config.pop("enabled_tools", None)
                    mcp_tools = create_tools_from_config(config, enabled_tools)
                    tools.extend(mcp_tools)
            else:
                tool = deepcopy(TOOL_REGISTRY[tool_name])
                if tool_name == "SearchDoc":
                    tool.retrievers = retrievers
                elif tool_name == "LLM":
                    tool.llm = llm
                tools.append(tool)
        pipeline.agent.plugins = tools

        pipeline.agent.prompt_template = PromptTemplate(settings[f"{prefix}.qa_prompt"])

        return pipeline

    @classmethod
    def get_user_settings(cls) -> dict:
        llm = ""
        llm_choices = [("(default)", "")]
        try:
            llm_choices += [(_, _) for _ in llms.options().keys()]
        except Exception as e:
            logger.exception(f"Failed to get LLM options: {e}")

        tool_choices = ["Wikipedia", "Google", "LLM", "SearchDoc"]
        try:
            mcp_manager.load()
            tool_choices += mcp_manager.get_enabled_tools()
        except Exception as e:
            logger.exception(f"Failed to get MCP tool options: {e}")

        return {
            "llm": {
                "name": "Language model",
                "value": llm,
                "component": "dropdown",
                "choices": llm_choices,
                "special_type": "llm",
                "info": (
                    "The language model to use for generating the answer. If None, "
                    "the application default language model will be used."
                ),
            },
            "tools": {
                "name": "Tools for knowledge retrieval",
                "value": ["Google", "LLM"],
                "component": "checkboxgroup",
                "choices": tool_choices,
            },
            "max_iterations": {
                "name": "Maximum number of iterations the CodeAct loop can go through",
                "value": 10,
                "component": "number",
            },
            "planning": {
                "name": "Enable initial planning step",
                "value": False,
                "component": "checkbox",
                "info": "If enabled, the agent will analyze the request and create a step-by-step plan before writing code.",
            },
            "qa_prompt": {
                "name": "QA Prompt",
                "value": zero_shot_codeact_prompt.template,
            },
        }

    @classmethod
    def get_info(cls) -> dict:
        return {
            "id": "CodeAct",
            "name": "CodeAct Agent",
            "description": (
                "Implementing CodeAct paradigm. "
                "Answers the user's request by iteratively formulating python scripts and executing them in a stateful REPL."
            ),
        }
