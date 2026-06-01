from typing import Any, Optional

from ktem.db.models import IssueReport

from .base import BaseCRUD


class IssueReportCRUD(BaseCRUD):
    """CRUD operations for the IssueReport table."""

    def create(
        self,
        issues: dict[str, Any],
        *,
        chat: Optional[dict[str, Any]] = None,
        settings: Optional[dict[str, Any]] = None,
        user: Optional[str] = None,
    ) -> IssueReport:
        """Persist a new issue report.

        Args:
            issues: structured issue data (correctness, labels, etc.).
            chat: snapshot of the conversation at report time.
            settings: snapshot of user settings at report time.
            user: id of the reporting user.

        Returns:
            The newly created IssueReport row.
        """
        item = IssueReport(
            issues=issues,
            chat=chat,
            settings=settings,
            user=user,
        )
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, id: int) -> IssueReport | None:
        """Return the issue report with the given *id*, or None.

        Args:
            id: primary-key id of the issue report.
        """
        return self.session.get(IssueReport, id)
