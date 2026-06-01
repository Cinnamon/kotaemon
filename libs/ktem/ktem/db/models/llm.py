from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class BaseLLM(Base):
    """Store LLM model pool entries.

    Attributes:
        name: unique name of the LLM
        spec: serialized LLM specification
        default: whether this model is the default in the pool
    """

    __abstract__ = True

    name: Mapped[str] = mapped_column(String, primary_key=True)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    default: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def vendor(self) -> str:
        return self.spec.get("__type__", "-").split(".")[-1]

    @property
    def ui(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "default": self.default,
        }
