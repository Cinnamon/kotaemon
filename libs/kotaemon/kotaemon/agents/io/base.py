import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Literal, NamedTuple, Optional, Union

from pydantic import ConfigDict

from kotaemon.base import LLMInterface


def check_log():
    """
    Checks if logging has been enabled.
    :return: True if logging has been enabled, False otherwise.
    :rtype: bool
    """
    return os.environ.get("LOG_PATH", None) is not None


class AgentType(Enum):
    """
    Enumerated type for agent types.
    """

    openai = "openai"
    openai_multi = "openai_multi"
    openai_tool = "openai_tool"
    self_ask = "self_ask"
    react = "react"
    rewoo = "rewoo"
    vanilla = "vanilla"


class BaseScratchPad:
    """
    Base class for output handlers.

    Attributes:
    -----------
    logger : logging.Logger
        The logger object to log messages.

    Methods:
    --------
    stop():
        Stop the output.

    update_status(output: str, **kwargs):
        Update the status of the output.

    thinking(name: str):
        Log that a process is thinking.

    done(_all=False):
        Log that the process is done.

    stream_print(item: str):
        Not implemented.

    json_print(item: Dict[str, Any]):
        Log a JSON object.

    panel_print(item: Any, title: str = "Output", stream: bool = False):
        Log a panel output.

    clear():
        Not implemented.

    print(content: str, **kwargs):
        Log arbitrary content.

    format_json(json_obj: str):
        Format a JSON object.

    debug(content: str, **kwargs):
        Log a debug message.

    info(content: str, **kwargs):
        Log an informational message.

    warning(content: str, **kwargs):
        Log a warning message.

    error(content: str, **kwargs):
        Log an error message.

    critical(content: str, **kwargs):
        Log a critical message.
    """

    def __init__(self):
        """
        Initialize the BaseOutput object.

        """
        self.logger = logging
        self.log = []

    def stop(self):
        """
        Stop the output.
        """

    def update_status(self, output: str, **kwargs):
        """
        Update the status of the output.
        """
        if check_log():
            self.logger.info(output)

    def thinking(self, name: str):
        """
        Log that a process is thinking.
        """
        if check_log():
            self.logger.info(f"{name} is thinking...")

    def done(self, _all=False):
        """
        Log that the process is done.
        """

        if check_log():
            self.logger.info("Done")

    def stream_print(self, item: str):
        """
        Stream print.
        """

    def json_print(self, item: Dict[str, Any]):
        """
        Log a JSON object.
        """
        if check_log():
            self.logger.info(json.dumps(item, indent=2))

    def panel_print(self, item: Any, title: str = "Output", stream: bool = False):
        """
        Log a panel output.

        Args:
            item : Any
                The item to log.
            title : str, optional
                The title of the panel, defaults to "Output".
            stream : bool, optional
        """
        if not stream:
            self.log.append(item)
        if check_log():
            self.logger.info("-" * 20)
            self.logger.info(item)
            self.logger.info("-" * 20)

    def clear(self):
        """
        Not implemented.
        """

    def print(self, content: str, **kwargs):
        """
        Log arbitrary content.
        """
        self.log.append(content)
        if check_log():
            self.logger.info(content)

    def format_json(self, json_obj: str):
        """
        Format a JSON object.
        """
        formatted_json = json.dumps(json_obj, indent=2)
        return formatted_json

    def debug(self, content: str, **kwargs):
        """
        Log a debug message.
        """
        if check_log():
            self.logger.debug(content, **kwargs)

    def info(self, content: str, **kwargs):
        """
        Log an informational message.
        """
        if check_log():
            self.logger.info(content, **kwargs)

    def warning(self, content: str, **kwargs):
        """
        Log a warning message.
        """
        if check_log():
            self.logger.warning(content, **kwargs)

    def error(self, content: str, **kwargs):
        """
        Log an error message.
        """
        if check_log():
            self.logger.error(content, **kwargs)

    def critical(self, content: str, **kwargs):
        """
        Log a critical message.
        """
        if check_log():
            self.logger.critical(content, **kwargs)


@dataclass
class AgentAction:
    """Agent's action to take.

    Args:
        tool: The tool to invoke.
        tool_input: The input to the tool.
        log: The log message.
    """

    tool: str
    tool_input: Union[str, dict]
    log: str


class AgentFinish(NamedTuple):
    """Agent's return value when finishing execution.

    Args:
        return_values: The return values of the agent.
        log: The log message.
    """

    return_values: dict
    log: str


class AgentOutput(LLMInterface):
    """Output from an agent.

    Args:
        text: The text output from the agent.
        agent_type: The type of agent.
        status: The status after executing the agent.
        error: The error message if any.
    """

    model_config = ConfigDict(extra="allow")

    text: str
    type: str = "agent"
    agent_type: AgentType
    status: Literal["thinking", "finished", "stopped", "failed"]
    error: Optional[str] = None
    intermediate_steps: Optional[list] = None
