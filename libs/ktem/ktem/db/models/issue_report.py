from typing import Any, Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BaseIssueReport(Base):
    """Store user-reported issues.

    Attributes:
        id: auto-increment integer primary key
        issues: the issues reported, formatted as a dict
        chat: the conversation at the time of the report
        settings: the user settings at the time of the report
        user: the user id
    """

    __abstract__ = True

    id: Mapped[Optional[int]] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    issues: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    chat: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    user: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
