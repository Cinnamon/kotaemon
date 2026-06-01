from ktem.db.engine import engine
from theflow.settings import settings
from theflow.utils.modules import import_dotted_string

from .base import Base
from .conversation import BaseConversation
from .embedding import BaseEmbedding
from .issue_report import BaseIssueReport
from .llm import BaseLLM
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


if not getattr(settings, "KH_ENABLE_ALEMBIC", False):
    Base.metadata.create_all(engine)
