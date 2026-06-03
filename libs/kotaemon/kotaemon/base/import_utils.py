"""Import helpers replacing theflow.utils.modules."""

from __future__ import annotations

import importlib
from typing import Any


def import_dotted_string(dotted: str, *, safe: bool = True) -> Any:
    """Import an object from a dotted ``module.path.Name`` string."""
    module_path, _, name = dotted.rpartition(".")
    if not module_path or not name:
        raise ValueError(f"Invalid dotted path: {dotted!r}")

    module = importlib.import_module(module_path)
    obj = getattr(module, name)
    if safe and not (isinstance(obj, type) or callable(obj)):
        raise TypeError(f"{dotted!r} is not a type or callable")
    return obj
