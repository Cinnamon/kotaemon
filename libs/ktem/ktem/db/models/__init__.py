from ktem.db.engine import engine

from .base import Base
from .conversation import BaseConversation
from .embedding import BaseEmbedding
from .file_index import (
    BaseFileChunkRelation,
    BaseFileGroup,
    BaseFileSource,
    get_file_chunk_relation_model,
    get_file_group_model,
    get_file_source_model,
)
from .issue_report import BaseIssueReport
from .llm import BaseLLM
from .reranking import BaseReranking
from .settings import BaseSettings
from .tables import (
    Conversation,
    EmbeddingTable,
    Index,
    IssueReport,
    LLMTable,
    RerankingTable,
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
    "BaseFileChunkRelation",
    "BaseFileGroup",
    "BaseFileSource",
    "get_file_chunk_relation_model",
    "get_file_group_model",
    "get_file_source_model",
    "BaseEmbedding",
    "BaseIssueReport",
    "BaseLLM",
    "BaseReranking",
    "BaseSettings",
    "BaseUser",
    # concrete table models
    "Conversation",
    "EmbeddingTable",
    "Index",
    "IssueReport",
    "LLMTable",
    "RerankingTable",
    "Settings",
    "User",
]
