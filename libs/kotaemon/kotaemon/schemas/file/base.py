from typing import Any

from sqlalchemy.orm import DeclarativeBase


class BaseSchema(DeclarativeBase):
    __abstract__ = True

    @classmethod
    def from_dict(cls, cls_name: str, params: dict[str, Any]) -> Any:
        params["__abstract__"] = False
        return type(cls_name, (BaseSchema,), params)
