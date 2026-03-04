from ktem.db.engine import engine
from sqlalchemy import JSON, Column, String
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseMCPTable(Base):
    """Base table to store MCP server configurations"""

    __abstract__ = True

    name = Column(String, primary_key=True, unique=True)
    config = Column(JSON, default={})  # Full JSON config for the MCP server


class MCPTable(BaseMCPTable):
    __tablename__ = "mcp_table"


# Drop and recreate to handle schema changes from old multi-column layout.
_inspector = sa_inspect(engine)
if _inspector.has_table("mcp_table"):
    _columns = {col["name"] for col in _inspector.get_columns("mcp_table")}
    if "config" not in _columns:
        MCPTable.__table__.drop(engine)  # type: ignore[attr-defined]

MCPTable.metadata.create_all(engine)
