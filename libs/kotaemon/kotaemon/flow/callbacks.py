import time

from theflow.base import Function


def run_id__timestamp(obj: Function) -> str:
    return str(time.time()).replace(".", "")


def store_result__pipeline_name(obj: Function) -> str:
    return f"{obj.__module__}.{obj.__class__.__qualname__}"


def function_name__class_name(obj: Function) -> str:
    return f"{obj.__class__.__module__}.{obj.__class__.__qualname__}"
