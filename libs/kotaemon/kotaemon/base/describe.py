from __future__ import annotations

from dataclasses import MISSING, fields
from typing import TypedDict


class DataclassParamDesc(TypedDict):
    """Metadata for one dataclass field in a describe spec."""

    required: bool
    help: str
    type: str


class DataclassDescribe(TypedDict):
    """Spec description returned by ``describe_dataclass``."""

    type: str
    params: dict[str, DataclassParamDesc]


def describe_dataclass(cls: type) -> DataclassDescribe:
    """Build a spec description from dataclass fields on ``cls``."""
    return {
        "type": f"{cls.__module__}.{cls.__qualname__}",
        "params": {
            field.name: {
                "required": (
                    field.default is MISSING
                    and field.default_factory is MISSING
                ),
                "help": field.metadata.get("description", ""),
                "type": repr(field.type),
            }
            for field in fields(cls)
        },
    }
