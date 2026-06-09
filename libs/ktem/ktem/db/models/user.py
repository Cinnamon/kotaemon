import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BaseUser(Base):
    """Store the user information.

    Attributes:
        id: canonical id to identify the user
        username: the username of the user
        username_lower: lowercased username for case-insensitive
            lookup
        password: the hashed password of the user
        admin: whether the user has admin privileges
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        index=True,
        default=lambda: uuid.uuid4().hex,
    )
    username: Mapped[str] = mapped_column(String, unique=True)
    username_lower: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(String)
    admin: Mapped[bool] = mapped_column(Boolean, default=False)
