from typing import Any, Optional

from ktem.db.models import Base
from ktem.db.engine import engine
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Index(Base):
    __tablename__ = "ktem__index"

    id: Mapped[Optional[int]] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    index_type: Mapped[str] = mapped_column(String)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


Index.metadata.create_all(engine)
