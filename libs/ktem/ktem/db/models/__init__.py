from ktem.db.engine import engine

from .base import Base
from .conversation import BaseConversation
from .embedding import BaseEmbedding
from .issue_report import BaseIssueReport
from .llm import BaseLLM
from .settings import BaseSettings
from .tables import (
    Conversation,
    EmbeddingTable,
    Index,
    IssueReport,
    LLMTable,
    Settings,
    User,
)
from .user import BaseUser

__all__ = [
    # engine — re-exported so callers can do:
    #   from ktem.db.models import Conversation, engine
    "engine",
    # declarative base
    "Base",
    # abstract base models
    "BaseConversation",
    "BaseEmbedding",
    "BaseIssueReport",
    "BaseLLM",
    "BaseSettings",
    "BaseUser",
    # concrete table models
    "Conversation",
    "EmbeddingTable",
    "Index",
    "IssueReport",
    "LLMTable",
    "Settings",
    "User",
]
