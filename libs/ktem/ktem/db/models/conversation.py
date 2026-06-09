import datetime
import uuid
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from tzlocal import get_localzone

from .base import Base


class BaseConversation(Base):
    """Store the chat conversation between the user and the bot.

    Attributes:
        id: canonical id to identify the conversation
        name: human-friendly name of the conversation
        user: the user id
        is_public: whether the conversation is public
        data_source: messages, selected files, chat_suggestions
        date_created: creation timestamp
        date_updated: last-updated timestamp
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
        default=lambda: uuid.uuid4().hex,
    )
    name: Mapped[str] = mapped_column(
        String,
        default=lambda: "Untitled - {}".format(
            datetime.datetime.now(get_localzone()).strftime("%Y-%m-%d %H:%M:%S")
        ),
    )
    user: Mapped[str] = mapped_column(String, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    date_created: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    date_updated: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
