"""Typing utilities

These utilities support introspection of nodes and params through type annotations.
Consider these as experimental due to very naive implementation that for sure cannot
handle uncommon cases.
"""
import inspect
from typing import _GenericAlias  # type: ignore
from typing import Any, Callable, Union, get_args, get_origin


def is_union_type(annotation) -> bool:
    """Check if the annotation is a Union type"""
    return annotation is Union or (
        isinstance(annotation, _GenericAlias) and annotation.__origin__ is Union
    )


def expand_types(annotation) -> list:
    """Expand the type from source to target"""
    result = []
    if is_union_type(annotation):
        childs = get_args(annotation)
        for child in childs:
            result += expand_types(child)
        return result

    origin = get_origin(annotation)
    if origin:
        result.append(origin)
    else:
        result.append(annotation)
    return result


def is_compatible_with(type1, type2) -> bool:
    """Check if the annotation type1 is at slightest compatible with type2

    Slightest compatibility happens when there is at least 1 type in type1 that is
    a subclass of at least 1 type in type2
    """
    type1s = expand_types(type1)
    type2s = expand_types(type2)
    if Any in type1s:
        return True
    if Any in type2s:
        return True

    for each_1 in type1s:
        for each_2 in type2s:
            try:
                if issubclass(each_1, each_2):
                    return True
            except Exception:
                continue

    return False


def input_signature(
    func: Callable, ignore_bound: bool = True
) -> tuple[dict, bool, bool]:
    """Get the input signature of a function or method

    Args:
        func: the function or method to get the signature
        ignore_bound: ignore the first argument if it is self or cls

    Returns:
        - a dict of {argument_name: argument_type}
        - a bool indicating if the function has *args
        - a bool indicating if the function has **kwargs
    """
    args = inspect.signature(func).parameters
    type_annotation = {}
    bounds = {"self", "cls"}
    has_args, has_kwargs = False, False
    for name, arg in args.items():
        if name in bounds and ignore_bound:
            continue
        if arg.kind == inspect.Parameter.VAR_POSITIONAL:
            has_args = True
            continue
        if arg.kind == inspect.Parameter.VAR_KEYWORD:
            has_kwargs = True
            continue
        if arg.annotation is not inspect.Parameter.empty:
            type_annotation[name] = arg.annotation
            continue
        if arg.default is not inspect.Parameter.empty and arg.default is not None:
            type_annotation[name] = type(arg.default)
            continue
        type_annotation[name] = Any

    return type_annotation, has_args, has_kwargs


def output_signature(func: Callable) -> Any:
    """Get the output signature of a function or method

    Args:
        func: the function or method to get the signature

    Returns:
        the return type annotation
    """
    annot = inspect.signature(func).return_annotation
    if annot is inspect.Signature.empty:
        annot = Any
    return annot
