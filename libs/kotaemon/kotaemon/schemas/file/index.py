from typing import cast

from sqlalchemy import Column, Integer, String

from .base import BaseSchema


class Index(BaseSchema):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(String)
    target_id = Column(String)
    relation_type = Column(String)
    user = Column(Integer, default=1)

    @classmethod
    def from_index(cls, idx: int) -> type["Index"]:
        cls.__tablename__ = f"index__{idx}__index"
        return cast(type["Index"], cls.from_dict("Index", dict(vars(cls))))
