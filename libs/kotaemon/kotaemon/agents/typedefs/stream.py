from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .io import AgentStatus, AgentType


class EventLabel(StrEnum):
    ACTION_START = auto()
    ANSWER = auto()
    ACTION_END = auto()
    FINAL_RESPONSE = auto()


class EventBase(BaseModel):
    label: EventLabel


class EventAnswer(EventBase):
    """Token-by-token chunk yielded while the agent is generating the final answer."""

    label: Literal[EventLabel.ANSWER] = EventLabel.ANSWER

    text: str


class EventActionStart(EventBase):
    """Emitted when the agent begins executing a tool."""

    label: Literal[EventLabel.ACTION_START] = EventLabel.ACTION_START

    action_name: str
    action_input: str
    log: str = ""


class EventActionEnd(EventBase):
    """Emitted when a tool finishes executing."""

    label: Literal[EventLabel.ACTION_END] = EventLabel.ACTION_END

    action_name: str
    action_input: str
    action_output: str
    log: str = ""


class EventFinalResponse(EventBase):
    label: Literal[EventLabel.FINAL_RESPONSE] = EventLabel.FINAL_RESPONSE

    text: str
    agent_type: AgentType
    status: AgentStatus
    error: str | None = None
    total_tokens: int = 0
    total_cost: float = 0.0
    intermediate_steps: list[tuple] | None = None
    metadata: dict | None = None
    max_iterations: int | None = None


AgentEvent = Annotated[
    EventActionStart | EventActionEnd | EventAnswer | EventFinalResponse,
    Field(discriminator="label"),
]
