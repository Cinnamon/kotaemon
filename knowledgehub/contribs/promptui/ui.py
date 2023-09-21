from typing import Union

import gradio as gr
import yaml
from theflow.utils.modules import import_dotted_string

from kotaemon.contribs.promptui.base import COMPONENTS_CLASS, SUPPORTED_COMPONENTS

USAGE_INSTRUCTION = """In case of errors, you can:

- Create bug fix and make PR at: https://github.com/Cinnamon/kotaemon
- Ping any of @john @tadashi @ian @jacky in Slack channel #llm-productization"""


def get_component(component_def: dict) -> gr.components.Component:
    """Get the component based on component definition"""
    component_cls = None

    if "component" in component_def:
        component = component_def["component"]
        if component not in SUPPORTED_COMPONENTS:
            raise ValueError(
                f"Unsupported UI component: {component}. "
                f"Must be one of {SUPPORTED_COMPONENTS}"
            )

        component_cls = COMPONENTS_CLASS[component]
    else:
        raise ValueError(
            f"Cannot decide the component from {component_def}. "
            "Please specify `component` with 1 of the following "
            f"values: {SUPPORTED_COMPONENTS}"
        )

    return component_cls(**component_def.get("params", {}))


def construct_ui(config, func_run, func_export) -> gr.Blocks:
    """Create UI from config file. Execute the UI from config file

    - Can do now: Log from stdout to UI
    - In the future, we can provide some hooks and callbacks to let developers better
    fine-tune the UI behavior.
    """
    inputs, outputs, params = [], [], []
    for name, component_def in config.get("inputs", {}).items():
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = True
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = name  # type: ignore

        inputs.append(component)

    for name, component_def in config.get("params", {}).items():
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = True
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = name  # type: ignore

        params.append(component)

    for idx, component_def in enumerate(config.get("outputs", [])):
        if "params" not in component_def:
            component_def["params"] = {}
        component_def["params"]["interactive"] = False
        component = get_component(component_def)
        if hasattr(component, "label") and not component.label:  # type: ignore
            component.label = f"Output {idx}"

        outputs.append(component)

    temp = gr.Tab
    with gr.Blocks(analytics_enabled=False, title="Welcome to PromptUI") as demo:
        with gr.Accordion(label="Usage", open=False):
            gr.Markdown(USAGE_INSTRUCTION)
        with gr.Row():
            run_btn = gr.Button("Run")
            run_btn.click(func_run, inputs=inputs + params, outputs=outputs)
            export_btn = gr.Button("Export")
            export_btn.click(func_export, inputs=None, outputs=None)
        with gr.Row():
            with gr.Column():
                with temp("Inputs"):
                    for component in inputs:
                        component.render()
                with temp("Params"):
                    for component in params:
                        component.render()
            with gr.Column():
                for component in outputs:
                    component.render()

    return demo


def build_pipeline_ui(config: dict, pipeline_def):
    """Build a tab from config file"""
    inputs_name = list(config.get("inputs", {}).keys())
    params_name = list(config.get("params", {}).keys())
    outputs_def = config.get("outputs", [])

    def run_func(*args):
        inputs = {
            name: value for name, value in zip(inputs_name, args[: len(inputs_name)])
        }
        params = {
            name: value for name, value in zip(params_name, args[len(inputs_name) :])
        }
        pipeline = pipeline_def()
        pipeline.set(params)
        pipeline(**inputs)
        if outputs_def:
            outputs = []
            for output_def in outputs_def:
                output = pipeline.last_run.logs(output_def["step"])
                if "item" in output_def:
                    output = output[output_def["item"]]
                outputs.append(output)
            return outputs

    # TODO: export_func is None for now
    return construct_ui(config, run_func, None)


def build_from_dict(config: Union[str, dict]):
    """Build a full UI from YAML config file"""

    if isinstance(config, str):
        with open(config) as f:
            config_dict: dict = yaml.safe_load(f)
    elif isinstance(config, dict):
        config_dict = config
    else:
        raise ValueError(
            f"config must be either a yaml path or a dict, got {type(config)}"
        )

    demos = []
    for key, value in config_dict.items():
        pipeline_def = import_dotted_string(key, safe=False)
        demos.append(build_pipeline_ui(value, pipeline_def))
    if len(demos) == 1:
        demo = demos[0]
    else:
        demo = gr.TabbedInterface(demos, list(config_dict.keys()))

    return demo
