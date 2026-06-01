from typing import Any, Type

from ktem.db.models import Base
from ktem.db.engine import engine
from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from theflow.settings import settings as flowsettings
from theflow.utils.modules import import_dotted_string


class BaseRerankingTable(Base):
    """Base table to store rerankings model."""

    __abstract__ = True

    name: Mapped[str] = mapped_column(String, primary_key=True, unique=True)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    default: Mapped[bool] = mapped_column(Boolean, default=False)


__base_reranking: Type[BaseRerankingTable] = (
    import_dotted_string(flowsettings.KH_TABLE_RERANKING, safe=False)
    if hasattr(flowsettings, "KH_TABLE_RERANKING")
    else BaseRerankingTable
)


class RerankingTable(__base_reranking):  # type: ignore
    __tablename__ = "reranking"


if not getattr(flowsettings, "KH_ENABLE_ALEMBIC", False):
    RerankingTable.metadata.create_all(engine)
