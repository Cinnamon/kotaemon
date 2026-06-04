import uuid
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BaseSettings(Base):
    """Record of user settings.

    Attributes:
        id: canonical id to identify the settings record
        user: the user id
        setting: the user settings serialised as JSON
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
        default=lambda: uuid.uuid4().hex,
    )
    user: Mapped[str] = mapped_column(String, default="")
    setting: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
