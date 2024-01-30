"""Get config from Pipeline"""
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Type, Union

import yaml

from kotaemon.base import BaseComponent
from kotaemon.chatbot import BaseChatBot

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

    ui_component = param.get("component_ui", "")
    if not ui_component:
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
        if isinstance(param_def["auto_callback"], str):
            continue
        if param_def.get("ignore_ui", False):
            continue
        config[name] = handle_param(param_def)
    for name, node_def in node.get("nodes", {}).items():
        if isinstance(node_def["auto_callback"], str):
            continue
        if node_def.get("ignore_ui", False):
            continue
        for key, value in handle_node(node_def["default"]).items():
            config[f"{name}.{key}"] = value
        for key, value in node_def.get("default_kwargs", {}).items():
            config[f"{name}.{key}"] = config_from_value(value)

    return config


def handle_input(pipeline: Union[BaseComponent, Type[BaseComponent]]) -> dict:
    """Get the input from the pipeline"""
    signature = inspect.signature(pipeline.run)
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
    ui_type = "chat" if isinstance(pipeline, BaseChatBot) else "simple"
    if ui_type == "chat":
        params = {f".bot.{k}": v for k, v in handle_node(pipeline_def).items()}
        params["system_message"] = {"component": "text", "params": {"value": ""}}
        outputs = []
        if hasattr(pipeline, "_promptui_outputs"):
            outputs = pipeline._promptui_outputs
        config_obj: dict = {
            "ui-type": ui_type,
            "params": params,
            "inputs": {},
            "outputs": outputs,
            "logs": {
                "full_pipeline": {
                    "input": {
                        "step": ".",
                        "getter": "_get_input",
                    },
                    "output": {
                        "step": ".",
                        "getter": "_get_output",
                    },
                    "preference": {
                        "step": "preference",
                    },
                }
            },
        }
    else:
        outputs = [{"step": ".", "getter": "_get_output", "component": "text"}]
        if hasattr(pipeline, "_promptui_outputs"):
            outputs = pipeline._promptui_outputs
        config_obj = {
            "ui-type": ui_type,
            "params": handle_node(pipeline_def),
            "inputs": handle_input(pipeline),
            "outputs": outputs,
            "logs": {
                "full_pipeline": {
                    "input": {
                        "step": ".",
                        "getter": "_get_input",
                    },
                    "output": {
                        "step": ".",
                        "getter": "_get_output",
                    },
                },
            },
        }

    config = {f"{pipeline.__module__}.{pipeline.__class__.__name__}": config_obj}
    if path is not None:
        old_config = config
        if Path(path).is_file():
            with open(path) as f:
                old_config = yaml.safe_load(f)
                old_config.update(config)
        with open(path, "w") as f:
            yaml.safe_dump(old_config, f, sort_keys=False)

    return config
