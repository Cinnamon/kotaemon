from typing import Any

from ktem.db.models import Conversation
from sqlalchemy import or_, select

from .base import BaseCRUD


class ConversationCRUD(BaseCRUD):
    """CRUD operations for the Conversation table."""

    def create(self, user: str) -> Conversation:
        """Create a new conversation owned by *user*.

        Args:
            user: the user id that owns the conversation.

        Returns:
            The newly created Conversation row.
        """
        item = Conversation(user=user)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, id: str) -> Conversation | None:
        """Return the conversation with the given *id*, or None.

        Args:
            id: primary-key id of the conversation.
        """
        return self.session.get(Conversation, id)

    def list_by_user(self, user_id: str) -> list[Conversation]:
        """Return all conversations owned by *user_id*, newest first.

        Args:
            user_id: the user id to filter by.
        """
        stmt = (
            select(Conversation)
            .where(Conversation.user == user_id)
            .order_by(Conversation.date_created.desc())  # type: ignore[attr-defined]
        )
        return list(self.session.scalars(stmt).all())

    def list_by_user_or_public(self, user_id: str) -> list[Conversation]:
        """Return conversations owned by *user_id* plus all public ones.

        Public conversations appear first, then sorted by creation date.

        Args:
            user_id: the user id to filter by.
        """
        stmt = (
            select(Conversation)
            .where(
                or_(
                    Conversation.user == user_id,
                    Conversation.is_public,
                )
            )
            .order_by(
                Conversation.is_public.desc(),  # type: ignore[attr-defined]
                Conversation.date_created.desc(),  # type: ignore[attr-defined]
            )
        )
        return list(self.session.scalars(stmt).all())

    def update_name(self, id: str, name: str) -> Conversation:
        """Rename a conversation.

        Args:
            id: primary-key id of the conversation.
            name: the new name.

        Returns:
            The updated Conversation row.

        Raises:
            ValueError: if no conversation with *id* exists.
        """
        item = self.session.get(Conversation, id)
        if item is None:
            raise ValueError(f"Conversation '{id}' not found")
        item.name = name
        self.commit()
        self.session.refresh(item)
        return item

    def update_data_source(self, id: str, data_source: dict[str, Any]) -> Conversation:
        """Replace the data_source payload of a conversation.

        Args:
            id: primary-key id of the conversation.
            data_source: the new data_source dict.

        Returns:
            The updated Conversation row.

        Raises:
            ValueError: if no conversation with *id* exists.
        """
        item = self.session.get(Conversation, id)
        if item is None:
            raise ValueError(f"Conversation '{id}' not found")
        item.data_source = data_source
        self.commit()
        self.session.refresh(item)
        return item

    def update_public(self, id: str, *, is_public: bool) -> Conversation:
        """Toggle the public flag of a conversation.

        Args:
            id: primary-key id of the conversation.
            is_public: new value for the public flag.

        Returns:
            The updated Conversation row.

        Raises:
            ValueError: if no conversation with *id* exists.
        """
        item = self.session.get(Conversation, id)
        if item is None:
            raise ValueError(f"Conversation '{id}' not found")
        item.is_public = is_public
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, id: str) -> None:
        """Delete the conversation with the given *id*.

        Args:
            id: primary-key id of the conversation.

        Raises:
            ValueError: if no conversation with *id* exists.
        """
        item = self.session.get(Conversation, id)
        if item is None:
            raise ValueError(f"Conversation '{id}' not found")
        self.session.delete(item)
        self.commit()
