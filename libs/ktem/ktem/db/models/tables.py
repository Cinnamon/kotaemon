from typing import Any, Optional

from ktem.db.engine import engine
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from ktem.settings_config import app_settings as settings

from .base import Base
from .conversation import BaseConversation
from .embedding import BaseEmbedding
from .issue_report import BaseIssueReport
from .llm import BaseLLM
from .reranking import BaseReranking
from .settings import BaseSettings
from .user import BaseUser


class Conversation(BaseConversation):
    __tablename__ = "conversation"


class User(BaseUser):
    __tablename__ = "user"


class Settings(BaseSettings):
    __tablename__ = "settings"


class IssueReport(BaseIssueReport):
    __tablename__ = "issuereport"


class EmbeddingTable(BaseEmbedding):
    __tablename__ = "embedding"


class LLMTable(BaseLLM):
    __tablename__ = "llm_table"


class RerankingTable(BaseReranking):
    __tablename__ = "reranking"


class Index(Base):
    __tablename__ = "ktem__index"

    id: Mapped[Optional[int]] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, unique=True)
    index_type: Mapped[str] = mapped_column(String)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


if not settings.KH_ENABLE_ALEMBIC:
    Base.metadata.create_all(engine)
