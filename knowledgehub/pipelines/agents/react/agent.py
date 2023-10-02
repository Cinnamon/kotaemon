import logging
import re
from typing import Dict, List, Optional, Tuple, Type, Union

from pydantic import BaseModel, create_model

from kotaemon.prompt.template import PromptTemplate

from ..base import AgentOutput, AgentType, BaseAgent, BaseLLM, BaseTool
from ..output.base import AgentAction, AgentFinish

FINAL_ANSWER_ACTION = "Final Answer:"


class ReactAgent(BaseAgent):
    """
    Sequential ReactAgent class inherited from BaseAgent.
    Implementing ReAct agent paradigm https://arxiv.org/pdf/2210.03629.pdf
    """

    name: str = "ReactAgent"
    agent_type: AgentType = AgentType.react
    description: str = "ReactAgent for answering multi-step reasoning questions"
    llm: Union[BaseLLM, Dict[str, BaseLLM]]
    prompt_template: Optional[PromptTemplate] = None
    plugins: List[BaseTool] = list()
    examples: Dict[str, Union[str, List[str]]] = dict()
    args_schema: Optional[Type[BaseModel]] = create_model(
        "ReactArgsSchema", instruction=(str, ...)
    )
    intermediate_steps: List[Tuple[Union[AgentAction, AgentFinish], str]] = []
    """List of AgentAction and observation (tool) output"""
    max_iterations = 10
    strict_decode: bool = False

    def _compose_plugin_description(self) -> str:
        """
        Compose the worker prompt from the workers.

        Example:
        toolname1[input]: tool1 description
        toolname2[input]: tool2 description
        """
        prompt = ""
        try:
            for plugin in self.plugins:
                prompt += f"{plugin.name}[input]: {plugin.description}\n"
        except Exception:
            raise ValueError("Worker must have a name and description.")
        return prompt

    def _construct_scratchpad(
        self, intermediate_steps: List[Tuple[Union[AgentAction, AgentFinish], str]] = []
    ) -> str:
        """Construct the scratchpad that lets the agent continue its thought process."""
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += action.log
            thoughts += f"\nObservation: {observation}\nThought:"
        return thoughts

    def _parse_output(self, text: str) -> Optional[Union[AgentAction, AgentFinish]]:
        """
        Parse text output from LLM for the next Action or Final Answer
        Using Regex to parse "Action:\n Action Input:\n" for the next Action
        Using FINAL_ANSWER_ACTION to parse Final Answer

        Args:
            text[str]: input text to parse
        """
        includes_answer = FINAL_ANSWER_ACTION in text
        regex = (
            r"Action\s*\d*\s*:[\s]*(.*?)[\s]*Action\s*\d*\s*Input\s*\d*\s*:[\s]*(.*)"
        )
        action_match = re.search(regex, text, re.DOTALL)
        action_output: Optional[Union[AgentAction, AgentFinish]] = None
        if action_match:
            if includes_answer:
                raise Exception(
                    "Parsing LLM output produced both a final answer "
                    f"and a parse-able action: {text}"
                )
            action = action_match.group(1).strip()
            action_input = action_match.group(2)
            tool_input = action_input.strip(" ")
            # ensure if its a well formed SQL query we don't remove any trailing " chars
            if tool_input.startswith("SELECT ") is False:
                tool_input = tool_input.strip('"')

            action_output = AgentAction(action, tool_input, text)

        elif includes_answer:
            action_output = AgentFinish(
                {"output": text.split(FINAL_ANSWER_ACTION)[-1].strip()}, text
            )
        else:
            if self.strict_decode:
                raise Exception(f"Could not parse LLM output: `{text}`")
            else:
                action_output = AgentFinish({"output": text}, text)

        return action_output

    def _compose_prompt(self, instruction) -> str:
        """
        Compose the prompt from template, worker description, examples and instruction.
        """
        agent_scratchpad = self._construct_scratchpad(self.intermediate_steps)
        tool_description = self._compose_plugin_description()
        tool_names = ", ".join([plugin.name for plugin in self.plugins])
        if self.prompt_template is None:
            from .prompt import zero_shot_react_prompt

            self.prompt_template = zero_shot_react_prompt
        return self.prompt_template.populate(
            instruction=instruction,
            agent_scratchpad=agent_scratchpad,
            tool_description=tool_description,
            tool_names=tool_names,
        )

    def _format_function_map(self) -> Dict[str, BaseTool]:
        """Format the function map for the open AI function API.

        Return:
            Dict[str, Callable]: The function map.
        """
        # Map the function name to the real function object.
        function_map = {}
        for plugin in self.plugins:
            function_map[plugin.name] = plugin
        return function_map

    def clear(self):
        """
        Clear and reset the agent.
        """
        self.intermediate_steps = []

    def run(self, instruction, max_iterations=None):
        """
        Run the agent with the given instruction.

        Args:
            instruction: Instruction to run the agent with.
            max_iterations: Maximum number of iterations
                of reasoning steps, defaults to 10.

        Return:
            AgentOutput object.
        """
        if not max_iterations:
            max_iterations = self.max_iterations
        assert max_iterations > 0

        self.clear()
        logging.info(f"Running {self.name} with instruction: {instruction}")
        total_cost = 0.0
        total_token = 0

        for _ in range(max_iterations):
            prompt = self._compose_prompt(instruction)
            logging.info(f"Prompt: {prompt}")
            response = self.llm(prompt, stop=["Observation:"])  # type: ignore
            response_text = response.text[0]
            logging.info(f"Response: {response_text}")
            action_step = self._parse_output(response_text)
            if action_step is None:
                raise ValueError("Invalid action")
            is_finished_chain = isinstance(action_step, AgentFinish)
            if is_finished_chain:
                result = ""
            else:
                assert isinstance(action_step, AgentAction)
                action_name = action_step.tool
                tool_input = action_step.tool_input
                logging.info(f"Action: {action_name}")
                logging.info(f"Tool Input: {tool_input}")
                result = self._format_function_map()[action_name](tool_input)
                logging.info(f"Result: {result}")

            self.intermediate_steps.append((action_step, result))
            if is_finished_chain:
                break

        return AgentOutput(
            output=response_text, cost=total_cost, token_usage=total_token
        )
