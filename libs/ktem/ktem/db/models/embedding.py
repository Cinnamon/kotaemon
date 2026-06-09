from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from kotaemon.embeddings.factory import EmbeddingVendor

from .base import Base


class BaseEmbedding(Base):
    """Store embedding model pool entries.

    Attributes:
        name: unique name of the embedding model
        vendor: vendor class identifier used for factory lookup
        spec: constructor parameters for the vendor class
        default: whether this model is the default in the pool
    """

    __abstract__ = True

    name: Mapped[str] = mapped_column(String, primary_key=True)
    vendor: Mapped[EmbeddingVendor] = mapped_column(String)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    default: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def ui(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "default": self.default,
        }
