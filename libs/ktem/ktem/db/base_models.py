import datetime
import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class BaseSource(SQLModel):
    """The source of the document

    Attributes:
        id: id of the source
        name: name of the source
        path: path to the source
    """

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
    name: str
    path: str


class SourceTargetRelation(str, Enum):
    DOCUMENT = "document"
    VECTOR = "vector"


class BaseIndex(SQLModel):
    """The index pointing from the original id to the target id"""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    source_id: str
    target_id: str
    relation_type: Optional[SourceTargetRelation] = Field(default=None)


class BaseConversation(SQLModel):
    """Conversation record"""

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
    name: str = Field(
        default_factory=lambda: datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    )
    user: int = Field(default=0)  # For now we only have one user

    # contains messages + current files
    data_source: dict = Field(default={}, sa_column=Column(JSON))

    date_created: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    date_updated: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class BaseUser(SQLModel):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password: str


class BaseSettings(SQLModel):
    """Record of settings"""

    __table_args__ = {"extend_existing": True}

    id: str = Field(
        default_factory=lambda: uuid.uuid4().hex, primary_key=True, index=True
    )
    user: int = Field(default=0)
    setting: dict = Field(default={}, sa_column=Column(JSON))


class BaseIssueReport(SQLModel):
    """Record of issues"""

    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    issues: dict = Field(default={}, sa_column=Column(JSON))
    chat: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    settings: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    user: Optional[int] = Field(default=None)
