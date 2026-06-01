import importlib
import inspect
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Generic, Optional, Type, TypeVar

logger = logging.getLogger(__name__)
NATIVE_TYPE = (dict, list, tuple, str, int, float, bool, type(None))


def import_dotted_string(
    dotted_string: str, /, safe=True, allowed_modules: Optional[Dict[str, Type]] = None
):
    """Import a dotted string

    Args:
        dotted_string: the dotted string to import
        safe: if True, only allowed modules can be imported
        allowed_modules: dict of allowed modules

    Returns:
        the imported object
    """
    if safe:
        if allowed_modules is None:
            raise ValueError("Must provide allowed_modules when safe=True")

        if dotted_string not in allowed_modules:
            raise ValueError(
                f"Module {dotted_string} is not allowed. "
                f"Allowed modules are {list(allowed_modules.keys())}"
            )

        return allowed_modules[dotted_string]

    module_name, obj_name = dotted_string.rsplit(".", 1)
    module = sys.modules.get(module_name)

    if not (
        module
        and (spec := getattr(module, "__spec__", None))
        and getattr(spec, "_initializing", False) is False
    ):
        module = importlib.import_module(module_name)

    return getattr(module, obj_name)


def serialize_path(path: Path) -> dict:
    """Serialize a Path object.

    For cross-platform compatibility, the type will be "pathlib.Path" rather than
    "posixpath" or "ntpath".
    """
    return {"__type__": "pathlib.Path", "path": str(path)}


SERIALIZE_BY_TYPES = {
    Path: serialize_path,
}


def import_modules(*module_names: str) -> tuple:
    """Import a module by string name, raise exception if not found

    Args:
        module_name: the module name to import

    Returns:
        the imported module

    Raises:
        ImportError: if any of the module cannot be imported
    """
    errors: list[str] = []
    modules = []
    for module_name in module_names:
        try:
            module = sys.modules.get(module_name)

            if not (
                module
                and (spec := getattr(module, "__spec__", None))
                and getattr(spec, "_initializing", False) is False
            ):
                module = importlib.import_module(module_name)
            modules.append(module)
        except ImportError as e:
            errors.append(module_name)
            logger.warn(f"Cannot import module {module_name}: {e}")

    if errors:
        raise ImportError(f"Cannot import modules: {', '.join(errors)}")

    return tuple(modules)


def serialize(value: Any) -> Any:
    """Serialize a value to a JSON-serializable object"""
    if isinstance(value, dict):
        return {key: serialize(val) for key, val in value.items()}

    if isinstance(value, list):
        return [serialize(val) for val in value]

    if isinstance(value, tuple):
        return tuple(serialize(val) for val in value)

    if isinstance(value, NATIVE_TYPE):
        return value

    if inspect.isfunction(value) or inspect.isclass(value):
        if value.__name__ == "<lambda>":
            raise ValueError("Cannot serialize lambda functions")
        return f"{{{{ {value.__module__}.{value.__name__} }}}}"

    if hasattr(value, "__persist_flow__"):
        d = value.__persist_flow__()
        return d

    for base in value.__class__.mro()[:-1]:
        if base in SERIALIZE_BY_TYPES:
            return SERIALIZE_BY_TYPES[base](value)

    if value.__module__ == "builtins":
        return f"{{{{ {value.__module__}.{value.__name__} }}}}"

    if value.__module__ == "typing":
        name = ""
        if hasattr(value, "__name__"):
            name = value.__name__
        elif hasattr(value, "_name"):
            name = value._name
        else:
            raise ValueError(f"Cannot serialize {value}. Unknown name")
        return f"{{{{ {value.__module__}.{name} }}}}"

    raise ValueError(
        f"Cannot serialize {value}. Consider implementing __persist_flow__"
    )


def deserialize(
    value: Any, /, safe=True, allowed_modules: Optional[Dict[str, Type]] = None
) -> Any:
    """Deserialize a JSON-serializable object to a Python object

    Args:
        value: the value to deserialize
        safe: if True, only allowed modules can be imported
        allowed_modules: dict of allowed modules
    """
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        return import_dotted_string(
            value[2:-2].strip(), safe=safe, allowed_modules=allowed_modules
        )

    if isinstance(value, dict) and "__type__" in value:
        cls = import_dotted_string(
            value["__type__"], safe=safe, allowed_modules=allowed_modules
        )
        params: dict = {}
        for key, val in value.items():
            if key == "__type__":
                continue
            params[key] = deserialize(val, safe=safe, allowed_modules=allowed_modules)
        return cls(**params)

    if isinstance(value, dict) and "__type__" not in value:
        return {
            key: deserialize(val, safe=safe, allowed_modules=allowed_modules)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            deserialize(val, safe=safe, allowed_modules=allowed_modules)
            for val in value
        ]

    if isinstance(value, tuple):
        return tuple(
            deserialize(val, safe=safe, allowed_modules=allowed_modules)
            for val in value
        )

    if isinstance(value, NATIVE_TYPE):
        return value

    raise ValueError(f"Cannot deserialize type {type(value)} ({value})")


T = TypeVar("T")


class lazy(Generic[T]):
    """Declare the init parameters to initialize an object

    This will declare an object and initialize it later, useful to set default
    values of a class parameter.
    """

    def __init__(self, cls: Type[T], **params):
        self._cls: Type[T] = cls
        self._params: dict = params

    def __call__(self) -> T:
        """Initialize the object"""
        params = {}
        for key, val in self._params.items():
            if isinstance(val, lazy):
                params[key] = val()
            else:
                params[key] = val

        return self._cls(**params)

    def withx(self, **params) -> "lazy[T]":
        """Continue declaring the object with additional parameters"""
        return lazy(self._cls, **{**self._params, **params})

    @classmethod
    def from_serialized(cls, d: dict):
        """Convert a dict-serialized object into an lazy object"""
        target_cls = import_dotted_string(d.pop("__type__"), safe=False)
        for key, value in d.items():
            if isinstance(value, dict) and "__type__" in value:
                d[key] = cls.from_serialized(value)
        return lazy(target_cls, **d)

    def __persist_flow__(self) -> dict:
        """Express the object as a dict"""
        params = {}
        for key, value in self._params.items():
            params[key] = value.__persist_flow__() if isinstance(value, lazy) else value

        return {"__type__": f"{self._cls.__module__}.{self._cls.__name__}", **params}

    def __rshift__(self, other: "lazy[T]") -> Any:
        """Chain two lazy objects together"""
        from theflow.base import Function, SequentialFunction

        if not isinstance(other, lazy):
            raise ValueError(f"Cannot chain lazy and non-lazy objects: {other}")

        if not issubclass(other._cls, Function) or not issubclass(self._cls, Function):
            raise ValueError("Can only chain lazy Function")

        funcs = []
        if issubclass(self._cls, SequentialFunction):
            funcs.extend(self._params.get("funcs", []))
        else:
            funcs.append(self)

        if issubclass(other._cls, SequentialFunction):
            funcs.extend(other._params.get("funcs", []))
        else:
            funcs.append(other)

        return lazy(SequentialFunction, funcs=funcs)

    def __floordiv__(self, other: "lazy[T]") -> Any:
        """Chain two lazy objects together"""
        from theflow.base import ConcurrentFunction, Function

        if not isinstance(other, lazy):
            raise ValueError(f"Cannot chain lazy and non-lazy objects: {other}")

        if not issubclass(other._cls, Function) or not issubclass(self._cls, Function):
            raise ValueError("Can only chain lazy Function")

        funcs = []
        if issubclass(self._cls, ConcurrentFunction):
            funcs.extend(self._params.get("funcs", []))
        else:
            funcs.append(self)

        if issubclass(other._cls, ConcurrentFunction):
            funcs.extend(other._params.get("funcs", []))
        else:
            funcs.append(other)

        return lazy(ConcurrentFunction, funcs=funcs)
