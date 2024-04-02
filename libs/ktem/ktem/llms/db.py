from typing import Type

from ktem.db.engine import engine
from sqlalchemy import JSON, Boolean, Column, String
from sqlalchemy.orm import DeclarativeBase
from theflow.settings import settings as flowsettings
from theflow.utils.modules import import_dotted_string


class Base(DeclarativeBase):
    pass


class BaseLLMTable(Base):
    """Base table to store language model"""

    __abstract__ = True

    name = Column(String, primary_key=True, unique=True)
    spec = Column(JSON, default={})
    default = Column(Boolean, default=False)


_base_llm: Type[BaseLLMTable] = (
    import_dotted_string(flowsettings.KH_TABLE_LLM, safe=False)
    if hasattr(flowsettings, "KH_TABLE_LLM")
    else BaseLLMTable
)


class LLMTable(_base_llm):  # type: ignore
    __tablename__ = "llm_table"


if not getattr(flowsettings, "KH_ENABLE_ALEMBIC", False):
    LLMTable.metadata.create_all(engine)
