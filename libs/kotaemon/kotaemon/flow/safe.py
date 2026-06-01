"""Construct a flow declaratively in a safe manner."""
import logging
from typing import Dict, Optional, Type

from .base import Function
from .utils.modules import deserialize, import_dotted_string

logger = logging.getLogger(__name__)


def load(
    obj: dict,
    /,
    safe=True,
    allowed_modules: Optional[Dict[str, Type]] = None,
) -> Function:
    """Construct flow from exported dict

    Args:
        obj: flow configuration exported with Flow.dump()
        safe: if True, only allowed modules can be imported
        modules: dict of allowed modules

    Returns:
        Function: flow
    """
    cls: Type["Function"]
    if safe:
        if allowed_modules is None:
            raise ValueError("A dict of allowed modules not provided when safe=True")
        if obj["function"] not in allowed_modules:
            raise ValueError(
                f"Module {obj['function']} not allowed. "
                f"Allowed modules are {list(allowed_modules.keys())}"
            )
        cls = allowed_modules[obj["function"]]
    else:
        cls = import_dotted_string(
            obj["function"], safe=safe, allowed_modules=allowed_modules
        )

    params: dict = {}
    for name, value in obj["params"].items():
        try:
            params[name] = deserialize(
                value, safe=safe, allowed_modules=allowed_modules
            )
        except Exception as e:
            logger.warn(e)
            continue

    nodes: dict = {
        key: load(value, safe=safe, allowed_modules=allowed_modules)
        for key, value in obj["nodes"].items()
    }

    func = cls(**params, **nodes)
    func._ff_config.update(obj.get("configs", {}))
    func._initialize()

    return func


def create(
    obj: dict,
    /,
    safe=True,
    allowed_modules: Optional[Dict[str, Type]] = None,
) -> Optional[Type[Function]]:
    pass
