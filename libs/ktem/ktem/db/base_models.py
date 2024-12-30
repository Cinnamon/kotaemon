import datetime
import uuid
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel
from tzlocal import get_localzone


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
        default_factory=lambda: "Untitled - {}".format(
            datetime.datetime.now(get_localzone()).strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    user: str = Field(default="")  # For now we only have one user

    is_public: bool = Field(default=False)

    # contains messages + current files + chat_suggestions
    data_source: dict = Field(default={}, sa_column=Column(JSON))

    date_created: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(get_localzone())
    )
    date_updated: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(get_localzone())
    )


class BaseUser(SQLModel):
    """Store the user information

    Attributes:
        id: canonical id to identify the user
        username: the username of the user
        password: the hashed password of the user
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
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
    user: str = Field(default="")
    setting: dict = Field(default={}, sa_column=Column(JSON))


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
    issues: dict = Field(default={}, sa_column=Column(JSON))
    chat: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    settings: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    user: Optional[str] = Field(default=None)
