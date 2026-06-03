from typing import Any, Optional

from ktem.db.engine import engine
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from theflow.settings import settings
from theflow.utils.modules import import_dotted_string

from .base import Base
from .conversation import BaseConversation
from .embedding import BaseEmbedding
from .issue_report import BaseIssueReport
from .llm import BaseLLM
from .reranking import BaseReranking
from .settings import BaseSettings
from .user import BaseUser

_base_conv = (
    import_dotted_string(settings.KH_TABLE_CONV, safe=False)
    if hasattr(settings, "KH_TABLE_CONV")
    else BaseConversation
)

_base_user = (
    import_dotted_string(settings.KH_TABLE_USER, safe=False)
    if hasattr(settings, "KH_TABLE_USER")
    else BaseUser
)

_base_settings = (
    import_dotted_string(settings.KH_TABLE_SETTINGS, safe=False)
    if hasattr(settings, "KH_TABLE_SETTINGS")
    else BaseSettings
)

_base_issue_report = (
    import_dotted_string(settings.KH_TABLE_ISSUE_REPORT, safe=False)
    if hasattr(settings, "KH_TABLE_ISSUE_REPORT")
    else BaseIssueReport
)

_base_embedding = (
    import_dotted_string(settings.KH_TABLE_EMBEDDING, safe=False)
    if hasattr(settings, "KH_TABLE_EMBEDDING")
    else BaseEmbedding
)

_base_llm = (
    import_dotted_string(settings.KH_TABLE_LLM, safe=False)
    if hasattr(settings, "KH_TABLE_LLM")
    else BaseLLM
)

_base_reranking = (
    import_dotted_string(settings.KH_TABLE_RERANKING, safe=False)
    if hasattr(settings, "KH_TABLE_RERANKING")
    else BaseReranking
)


class Conversation(_base_conv):  # type: ignore
    """Conversation record"""

    __tablename__ = "conversation"  # type: ignore


class User(_base_user):  # type: ignore
    """User table"""

    __tablename__ = "user"  # type: ignore


class Settings(_base_settings):  # type: ignore
    """Record of settings"""

    __tablename__ = "settings"  # type: ignore


class IssueReport(_base_issue_report):  # type: ignore
    """Record of issues"""

    __tablename__ = "issuereport"  # type: ignore


class EmbeddingTable(_base_embedding):  # type: ignore
    """Embedding model pool record"""

    __tablename__ = "embedding"  # type: ignore


class LLMTable(_base_llm):  # type: ignore
    """LLM model pool record"""

    __tablename__ = "llm_table"  # type: ignore


class RerankingTable(_base_reranking):  # type: ignore
    """Reranking model pool record"""

    __tablename__ = "reranking"  # type: ignore


class Index(Base):
    """Collection (index) record"""

    __tablename__ = "ktem__index"

    id: Mapped[Optional[int]] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    index_type: Mapped[str] = mapped_column(String)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


if not getattr(settings, "KH_ENABLE_ALEMBIC", False):
    Base.metadata.create_all(engine)
