"""Construct file-index knowledge services for UI and Agent callers."""

from kotaemon.indices.knowledge.planning.query_planner import QueryPlanner
from kotaemon.indices.knowledge.retrieval import KnowledgeService

from .knowledge_catalog import KnowledgeCatalog


def create_file_knowledge_service(
    *,
    Source,
    Index,
    vector_retrieval,
    docstore,
    private: bool = False,
    user_id: str | None = None,
    session_factory=None,
) -> KnowledgeService:
    """Build the selected-file UI service from the current file index."""
    catalog = KnowledgeCatalog(
        Source,
        Index,
        private=private,
        user_id=None if user_id is None else str(user_id),
        session_factory=session_factory,
    )
    return KnowledgeService(
        planner=QueryPlanner(),
        catalog=catalog,
        retriever=vector_retrieval,
        docstore=docstore,
    )


def create_agent_knowledge_service(
    *,
    Source,
    Index,
    vector_retrieval,
    docstore,
    private: bool = False,
    user_id: str | None = None,
    session_factory=None,
) -> KnowledgeService:
    """Build the explicitly global Agent service over SQL-visible sources.

    Callers may pass ``allowed_source_ids`` on each operation to narrow access.
    Omitting it uses the Source rows visible under this index's private/user
    policy; it never skips the SQL catalog.
    """
    return create_file_knowledge_service(
        Source=Source,
        Index=Index,
        vector_retrieval=vector_retrieval,
        docstore=docstore,
        private=private,
        user_id=user_id,
        session_factory=session_factory,
    )
