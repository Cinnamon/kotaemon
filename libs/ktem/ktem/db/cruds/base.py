from types import TracebackType
from typing_extensions import Self

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class BaseCRUD:
    """Context manager that provides a SQLAlchemy Session.

    Usage::

        with SomeCRUD(engine) as crud:
            item = crud.get("id")
            crud.delete("id")
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._session: Session | None = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError(
                "Session not initialised. "
                "Use this CRUD as a context manager."
            )
        return self._session

    def commit(self) -> None:
        """Commit, rolling back automatically on failure."""
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def __enter__(self) -> Self:
        self._session = Session(self.engine)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session:
            self._session.close()
            self._session = None
