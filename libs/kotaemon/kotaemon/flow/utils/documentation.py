"""Utility modules to extract documentation from the source Function."""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys

from ..base import Function, NodeAttr, ParamAttr


def get_function_documentation(func: type[Function]) -> dict:
    """Return the documentation of the Function.

    Returns:
        Dictionary description of the Function, suitable to be parsed. Sample:
            {
                "desc": "Description of the flow",
                "nodes": {
                    "node_1": {
                        "desc": "Description of the node",
                        "type": "Default type of the node",
                        "input": "The input interface",
                        "output": "The output interface"
                    },
                },
                "params": {
                    "param_1": {
                        "desc": "Description of the parameter",
                        "type": "Default type of the parameter",
                        "default": "Default value of the parameter"
                    },
                }
            }
    """
    params, nodes = {}, {}
    for name in dir(func):
        attr = getattr(func, name)
        if isinstance(attr, ParamAttr):
            params[name] = {
                "desc": attr._help,
                "type": attr._type,
                "default": attr._default,
                "depends_on": attr._depends_on,
            }
        elif isinstance(attr, NodeAttr):
            nodes[name] = {
                "desc": attr._help,
                "type": attr._default,
                "input": attr._input,
                "output": attr._output,
                "depends_on": attr._depends_on,
            }

    return {
        "desc": func.__doc__ or "",
        "params": params,
        "nodes": nodes,
    }


def get_functions_from_module(module_path: str, recursive: bool = True) -> dict:
    """Get all Functions from module

    Args:
        module_path: The path to the module

    Returns:
        A dictionary of Functions, with the key being the name of the function and the
        value being the Functions class itself.
    """
    funcs: dict = {}
    module = sys.modules.get(module_path)
    if not (
        module
        and (spec := getattr(module, "__spec__", None))
        and getattr(spec, "_initializing", False) is False
    ):
        module = importlib.import_module(module_path)

    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, Function) and obj != Function:
            if not obj.__module__.startswith(module_path):
                # irrelevant import
                continue
            funcs[f"{obj.__module__}.{obj.__name__}"] = obj

    if recursive and "__path__" in dir(module):
        for _, name, _ in pkgutil.iter_modules(module.__path__):
            funcs.update(
                get_functions_from_module(f"{module_path}.{name}", recursive=True)
            )

    return funcs


def get_function_documentation_from_module(
    module_path: str, recursive: bool = True
) -> dict:
    """Get all functions documenations from module

    Args:
        module_path: The path to the module
        recursive: Whether to recursively search for functions in submodules

    Returns:
        A dictionary of functions, with the key being the name of the function and the
        value being the function documentation
    """
    funcs = get_functions_from_module(module_path, recursive=recursive)
    return {name: get_function_documentation(func) for name, func in funcs.items()}
