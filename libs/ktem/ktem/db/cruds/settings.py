from typing import Any

from ktem.db.models import Settings
from sqlalchemy import select

from .base import BaseCRUD


class SettingsCRUD(BaseCRUD):
    """CRUD operations for the Settings table."""

    def get_by_user(self, user_id: str) -> Settings | None:
        """Return the settings record for *user_id*, or None.

        Args:
            user_id: the user id to look up.
        """
        stmt = select(Settings).where(Settings.user == user_id)
        return self.session.scalars(stmt).first()

    def upsert(self, user_id: str, setting: dict[str, Any]) -> Settings:
        """Create or replace the settings record for *user_id*.

        Args:
            user_id: the user id that owns the settings.
            setting: the settings payload to store.

        Returns:
            The created or updated Settings row.
        """
        item = self.get_by_user(user_id)
        if item is None:
            item = Settings(user=user_id, setting=setting)
            self.session.add(item)
        else:
            item.setting = setting
        self.commit()
        self.session.refresh(item)
        return item

    def delete_by_user(self, user_id: str) -> None:
        """Delete the settings record for *user_id* if one exists.

        Args:
            user_id: the user id whose settings should be removed.
        """
        item = self.get_by_user(user_id)
        if item is not None:
            self.session.delete(item)
            self.commit()
