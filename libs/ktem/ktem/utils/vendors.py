import sys
from typing import Type

from theflow.base import ParamAttr


def vendor_allowlist(vendors: list[Type]) -> dict[str, Type]:
    """Return the dotted class paths that model deserialization may instantiate.

    A vendor class is allowed under its defining module and under every parent
    package that re-exports the same class object, so stored specs such as
    ``kotaemon.llms.ChatOpenAI`` and ``kotaemon.llms.chats.LCAnthropicChat`` keep
    loading while any other ``__type__`` is rejected.

    Args:
        vendors: Registered vendor classes.

    Returns:
        Mapping of allowed dotted paths to their classes.
    """
    allowed: dict[str, Type] = {"theflow.base.ParamAttr": ParamAttr}
    for vendor in vendors:
        parts = vendor.__module__.split(".")
        for depth in range(1, len(parts) + 1):
            package = ".".join(parts[:depth])
            if getattr(sys.modules.get(package), vendor.__qualname__, None) is vendor:
                allowed[f"{package}.{vendor.__qualname__}"] = vendor
    return allowed
