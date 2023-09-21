"""Get config from Pipeline"""
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

import yaml

from ...base import BaseComponent
from .base import DEFAULT_COMPONENT_BY_TYPES


def config_from_value(value: Any) -> dict:
    """Get the config from default value

    Args:
        value (Any): default value

    Returns:
        dict: config
    """
    component = DEFAULT_COMPONENT_BY_TYPES.get(type(value).__name__, "text")
    return {
        "component": component,
        "params": {
            "value": value,
        },
    }


def handle_param(param: dict) -> dict:
    """Convert param definition into promptui-compliant config

    Supported gradio's UI components are (https://www.gradio.app/docs/components)
        - CheckBoxGroup: list (multi select)
        - DropDown: list (single select)
        - File
        - Image
        - Number: int / float
        - Radio: list (single select)
        - Slider: int / float
        - TextBox: str
    """
    params = {}
    default = param.get("default", None)
    if isinstance(default, str) and default.startswith("{{") and default.endswith("}}"):
        default = None
    if default is not None:
        params["value"] = default

    type_: str = type(default).__name__ if default is not None else ""
    ui_component = DEFAULT_COMPONENT_BY_TYPES.get(type_, "text")

    return {
        "component": ui_component,
        "params": params,
    }


def handle_node(node: dict) -> dict:
    """Convert node definition into promptui-compliant config"""
    config = {}
    for name, param_def in node.get("params", {}).items():
        if isinstance(param_def["default_callback"], str):
            continue
        config[name] = handle_param(param_def)
    for name, node_def in node.get("nodes", {}).items():
        if isinstance(node_def["default_callback"], str):
            continue
        for key, value in handle_node(node_def["default"]).items():
            config[f"{name}.{key}"] = value
        for key, value in node_def["default_kwargs"].items():
            config[f"{name}.{key}"] = config_from_value(value)

    return config


def handle_input(pipeline: Union[BaseComponent, Type[BaseComponent]]) -> dict:
    """Get the input from the pipeline"""
    if not hasattr(pipeline, "run_raw"):
        return {}
    signature = inspect.signature(pipeline.run_raw)
    inputs: Dict[str, Dict] = {}
    for name, param in signature.parameters.items():
        if name in ["self", "args", "kwargs"]:
            continue
        input_def: Dict[str, Optional[Any]] = {"component": "text"}
        default = param.default
        if default is param.empty:
            inputs[name] = input_def
            continue

        params = {}
        params["value"] = default
        type_ = type(default).__name__ if default is not None else None
        ui_component = None
        if type_ is not None:
            ui_component = "text"

        input_def["component"] = ui_component
        input_def["params"] = params

        inputs[name] = input_def

    return inputs


def export_pipeline_to_config(
    pipeline: Union[BaseComponent, Type[BaseComponent]],
    path: Optional[str] = None,
) -> dict:
    """Export a pipeline to a promptui-compliant config dict"""
    if inspect.isclass(pipeline):
        pipeline = pipeline()

    pipeline_def = pipeline.describe()
    config = {
        f"{pipeline.__module__}.{pipeline.__class__.__name__}": {
            "params": handle_node(pipeline_def),
            "inputs": handle_input(pipeline),
            "outputs": [{"step": ".", "component": "text"}],
        }
    }
    if path is not None:
        old_config = config
        if Path(path).is_file():
            with open(path) as f:
                old_config = yaml.safe_load(f)
                old_config.update(config)
        with open(path, "w") as f:
            yaml.safe_dump(old_config, f)

    return config
