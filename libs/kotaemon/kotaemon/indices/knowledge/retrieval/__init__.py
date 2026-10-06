"""Agent-facing knowledge retrieval interfaces."""

from .knowledge_service import KnowledgeService
from .trace import RetrievalTrace

__all__ = ["KnowledgeService", "RetrievalTrace"]
