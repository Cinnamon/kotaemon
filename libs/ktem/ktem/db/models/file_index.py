from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column
from tzlocal import get_localzone

from .base import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _now_local() -> datetime:
    return datetime.now(get_localzone())


class BaseFileSource(Base):
    """Indexed file or URL in a file collection (per-index table)."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer, default=0)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_local
    )
    user: Mapped[str] = mapped_column(String, default="")
    note: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),  # type: ignore[arg-type]
        default=lambda: {},
    )


class BaseFileChunkRelation(Base):
    """Link from a source file to a doc-store or vector-store chunk id."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String)
    relation_type: Mapped[str] = mapped_column(String)
    user: Mapped[str] = mapped_column(String, default="")


class BaseFileGroup(Base):
    """Named group of source file ids within a file collection."""

    __abstract__ = True

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_new_uuid)
    date_created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_local
    )
    name: Mapped[str] = mapped_column(String)
    user: Mapped[str] = mapped_column(String, default="")
    data: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSON),  # type: ignore[arg-type]
        default=lambda: {"files": []},
    )


_mp_file_source_models: dict[tuple[int, bool], type[BaseFileSource]] = {}
_mp_file_chunk_relation_models: dict[int, type[BaseFileChunkRelation]] = {}
_mp_file_group_models: dict[int, type[BaseFileGroup]] = {}


def get_file_source_model(index_id: int, *, private: bool) -> type[BaseFileSource]:
    """Return the mapped Source class for a file collection."""
    key = (index_id, private)
    if key in _mp_file_source_models:
        return _mp_file_source_models[key]

    table_args = (
        (UniqueConstraint("name", "user", name="_name_user_uc"),)
        if private
        else (UniqueConstraint("name", name="_name_uc"),)
    )
    model = type(
        f"FileSource_{index_id}",
        (BaseFileSource,),
        {
            "__tablename__": f"index__{index_id}__source",
            "__table_args__": table_args,
        },
    )
    _mp_file_source_models[key] = model
    return model


def get_file_chunk_relation_model(index_id: int) -> type[BaseFileChunkRelation]:
    """Return the mapped chunk-relation class for a file collection."""
    if index_id in _mp_file_chunk_relation_models:
        return _mp_file_chunk_relation_models[index_id]

    model = type(
        f"FileChunkRelation_{index_id}",
        (BaseFileChunkRelation,),
        {"__tablename__": f"index__{index_id}__index"},
    )
    _mp_file_chunk_relation_models[index_id] = model
    return model


def get_file_group_model(index_id: int) -> type[BaseFileGroup]:
    """Return the mapped FileGroup class for a file collection."""
    if index_id in _mp_file_group_models:
        return _mp_file_group_models[index_id]

    model = type(
        f"FileGroup_{index_id}",
        (BaseFileGroup,),
        {
            "__tablename__": f"index__{index_id}__group",
            "__table_args__": (UniqueConstraint("name", "user", name="_name_user_uc"),),
        },
    )
    _mp_file_group_models[index_id] = model
    return model
