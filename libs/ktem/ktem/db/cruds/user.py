from typing import Optional

from sqlalchemy import select

from ktem.db.models import User

from .base import BaseCRUD


class UserCRUD(BaseCRUD):
    """CRUD operations for the User table."""

    def create(
        self,
        username: str,
        password: str,
        *,
        admin: bool = False,
        user_id: Optional[str] = None,
    ) -> User:
        """Create a new user.

        Args:
            username: the display username.
            password: the already-hashed password.
            admin: whether the user has admin privileges.
            user_id: explicit id; auto-generated when omitted.

        Returns:
            The newly created User row.

        Raises:
            ValueError: if the username already exists.
        """
        if self.get_by_username(username) is not None:
            raise ValueError(
                f"Username '{username}' already exists"
            )
        kwargs: dict = dict(
            username=username,
            username_lower=username.lower(),
            password=password,
            admin=admin,
        )
        if user_id is not None:
            kwargs["id"] = user_id
        item = User(**kwargs)
        self.session.add(item)
        self.commit()
        self.session.refresh(item)
        return item

    def get(self, id: str) -> User | None:
        """Return the user with the given *id*, or None.

        Args:
            id: primary-key id of the user.
        """
        return self.session.get(User, id)

    def get_by_username(self, username: str) -> User | None:
        """Return the user whose username (case-insensitive) matches, or None.

        Args:
            username: the username to look up.
        """
        stmt = select(User).where(
            User.username_lower == username.lower()
        )
        return self.session.scalars(stmt).first()

    def list_all(self) -> list[User]:
        """Return all users."""
        return list(self.session.scalars(select(User)).all())

    def username_taken(
        self, username: str, exclude_id: Optional[str] = None
    ) -> bool:
        """Check whether *username* is already in use.

        Args:
            username: username to check.
            exclude_id: user id to exclude from the check (used
                when renaming an existing user).

        Returns:
            True if the username is taken by another user.
        """
        stmt = select(User).where(
            User.username_lower == username.lower()
        )
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return self.session.scalars(stmt).first() is not None

    def update(
        self,
        id: str,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        admin: Optional[bool] = None,
    ) -> User:
        """Partially update a user record.

        Args:
            id: primary-key id of the user.
            username: new username; unchanged when None.
            password: new hashed password; unchanged when None.
            admin: new admin flag; unchanged when None.

        Returns:
            The updated User row.

        Raises:
            ValueError: if the user is not found.
        """
        item = self.session.get(User, id)
        if item is None:
            raise ValueError(f"User '{id}' not found")
        if username is not None:
            item.username = username
            item.username_lower = username.lower()
        if password is not None:
            item.password = password
        if admin is not None:
            item.admin = admin
        self.commit()
        self.session.refresh(item)
        return item

    def delete(self, id: str) -> None:
        """Delete the user with the given *id*.

        Args:
            id: primary-key id of the user.

        Raises:
            ValueError: if the user is not found.
        """
        item = self.session.get(User, id)
        if item is None:
            raise ValueError(f"User '{id}' not found")
        self.session.delete(item)
        self.commit()
