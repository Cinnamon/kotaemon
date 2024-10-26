from typing import cast

from sqlalchemy import JSON, Column, DateTime, Integer, String, func
from sqlalchemy.ext.mutable import MutableDict
from typing_extensions import Self

from .base import BaseSchema


class FileGroup(BaseSchema):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_created = Column(DateTime(timezone=True), server_default=func.now())
    name = Column(String, unique=True)
    user = Column(Integer, default=1)
    data = Column(MutableDict.as_mutable(JSON), default={"files": []})  # type: ignore

    @classmethod
    def from_index(cls, idx: int) -> Self:
        cls.__tablename__ = f"index__{idx}__group"
        return cast(Self, cls.from_dict("FileGroup", dict(vars(cls))))
