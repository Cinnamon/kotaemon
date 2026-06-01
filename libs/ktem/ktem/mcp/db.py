from typing import Any

from ktem.db.models import Base
from ktem.db.engine import engine
from sqlalchemy import JSON, String
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapped, mapped_column


class BaseMCPTable(Base):
    """Base table to store MCP server configurations."""

    __abstract__ = True

    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    config: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )


class MCPTable(BaseMCPTable):
    __tablename__ = "mcp_table"


# Drop and recreate to handle schema changes from old multi-column layout.
_inspector = sa_inspect(engine)
if _inspector.has_table("mcp_table"):
    _columns = {col["name"] for col in _inspector.get_columns("mcp_table")}
    if "config" not in _columns:
        MCPTable.__table__.drop(engine)  # type: ignore[attr-defined]

MCPTable.metadata.create_all(engine)
