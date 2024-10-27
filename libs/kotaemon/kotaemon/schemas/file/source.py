import uuid
from typing import cast

from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.ext.mutable import MutableDict

from .base import BaseSchema


class Source(BaseSchema):
    __abstract__ = True

    id = Column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), unique=True
    )
    name = Column(String)
    path = Column(String)
    size = Column(Integer, default=0)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    user = Column(Integer, default=1)
    note = Column(MutableDict.as_mutable(JSON), default={})  # type: ignore

    @classmethod
    def from_index(cls, idx: int, private: bool = False) -> type["Source"]:
        cls.__tablename__ = f"index__{idx}__source"
        if private:
            cls.__table_args__ = (
                UniqueConstraint("name", "user", name="_name_user_uc"),
            )
            cls.name = Column(String)
        else:
            cls.name = Column(String, unique=True)

        return cast(type["Source"], cls.from_dict("Source", dict(vars(cls))))
