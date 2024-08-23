import datetime
import uuid
from enum import Enum
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel
from theflow.settings import settings as flowsettings


class BaseConversation(SQLModel):
    """Store the chat conversation between the user and the bot

    Attributes:
        id: canonical id to identify the conversation
        name: human-friendly name of the conversation
        user: the user id
        data_source: the data source of the conversation
        date_created: the date the conversation was created
        date_updated: the date the conversation was updated
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
    name: str = Field(
        default_factory=lambda: datetime.datetime.now(
            ZoneInfo(getattr(flowsettings, "TIME_ZONE", "UTC"))
        ).strftime("%Y-%m-%d %H:%M:%S")
    )
    user: int = Field(default=0)  # For now we only have one user

    is_public: bool = Field(default=False)

    # contains messages + current files
    data_source: dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    date_created: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    date_updated: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class BaseUser(SQLModel):
    """Store the user information

    Attributes:
        id: canonical id to identify the user
        username: the username of the user
        password: the hashed password of the user
    """

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    username_lower: str = Field(unique=True)
    password: str
    admin: bool = Field(default=False)


class BaseSettings(SQLModel):
    """Record of user settings

    Attributes:
        id: canonical id to identify the settings
        user: the user id
        setting: the user settings (in dict/json format)
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
    user: int = Field(default=0)
    setting: dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class BaseIssueReport(SQLModel):
    """Store user-reported issues

    Attributes:
        id: canonical id to identify the issue report
        issues: the issues reported by the user, formatted as a dict
        chat: the conversation id when the user reported the issue
        settings: the user settings at the time of the issue report
        user: the user id
    """

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    issues: dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    chat: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    settings: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    user: Optional[int] = Field(default=None)


class TagType(str, Enum):
    text = "Text"
    classification = "Classification"
    boolean = "True/False"

    @classmethod
    def list_all(cls) -> list[str]:
        return [en.value for en in cls]


class TagScope(str, Enum):
    chunk = "Chunk"
    file = "File"

    @classmethod
    def list_all(cls) -> list[str]:
        return [en.value for en in cls]


class TagProcessStatus(str, Enum):
    pending = "Pending"
    in_progress = "In Progress"
    done = "Done"
    failed = "Failed"


class ScenarioType(str, Enum):
    incident_search = "Incident Search"

    @classmethod
    def get_types(cls) -> list[str]:
        return [en.value for en in cls]


class PromptVariableType(str, Enum):
    input = "INPUT"
    file_name = "FILE_NAME"
    index_name = "INDEX_NAME"

    @classmethod
    def get_types(cls) -> list[str]:
        return [en.value for en in cls]


class BaseTag(SQLModel):
    """
    Store records of tag

    Attributes:
        id: canonical id to identify the tag
        name: human-friendly name of the tag
        prompt: tag prompt to feed to LLM
        type: tag type, should be text, classification or boolean.
              In case meta['classes'] is the acceptable classes.
        meta: store additional information about the tag
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )

    prompt: str
    config: str = Field(default="")
    name: str = Field(unique=True)
    type: str
    scope: str = Field(default=TagScope.chunk.value)
    meta: dict[str, Any] = Field(default={}, sa_column=Column(JSON))


class BaseChunkTagIndex(SQLModel):
    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )

    tag_id: str
    chunk_id: str
    content: str

    date_updated: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    status: str


class BaseScenario(SQLModel):
    """
    Store records of scenarios

    Attributes:
        id: canonical id to identify the scenario
        name: human-friendly name of the scenario
        scenario_type: type of the scenario, using an enum for specific classes
        specification: detailed specification of the scenario
        base_prompt: base prompt to be used in the scenario
        retrieval_validator: string representing the retrieval validator logic
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )

    name: str = Field(unique=True)
    scenario_type: str
    specification: str
    base_prompt: str
    retrieval_validator: str
