import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import gradio as gr
import pandas as pd
from theflow.storage import storage

from kotaemon.contribs.promptui.base import get_component
from kotaemon.contribs.promptui.export import export

from ..logs import ResultLog

USAGE_INSTRUCTION = """## How to use:

1. Set the desired parameters.
2. Set the desired inputs.
3. Click "Run" to execute the pipeline with the supplied parameters and inputs
4. The pipeline output will show up in the output panel.
5. Repeat from step 1.
6. To compare the result of different run, click "Export" to get an Excel
    spreadsheet summary of different run.

## Support:

In case of errors, you can:

- PromptUI instruction:
    https://github.com/Cinnamon/kotaemon/wiki/Utilities#prompt-engineering-ui
- Create bug fix and make PR at: https://github.com/Cinnamon/kotaemon
- Ping any of @john @tadashi @ian @jacky in Slack channel #llm-productization

## Contribute:

- Follow installation at: https://github.com/Cinnamon/kotaemon/
"""


def construct_pipeline_ui(
    config, func_run, func_save, func_load_params, func_activate_params, func_export
) -> gr.Blocks:
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
            component.label = f"Output {idx}"  # type: ignore

        outputs.append(component)

    exported_file = gr.File(label="Output file", show_label=True)
    history_dataframe = gr.DataFrame(wrap=True)

    temp = gr.Tab
    with gr.Blocks(analytics_enabled=False, title="Welcome to PromptUI") as demo:
        with gr.Accordion(label="HOW TO", open=False):
            gr.Markdown(USAGE_INSTRUCTION)
        with gr.Accordion(label="Params History", open=False):
            with gr.Row():
                save_btn = gr.Button("Save params")
                save_btn.click(func_save, inputs=params, outputs=history_dataframe)
                load_params_btn = gr.Button("Reload params")
                load_params_btn.click(
                    func_load_params, inputs=[], outputs=history_dataframe
                )
            history_dataframe.render()
            history_dataframe.select(
                func_activate_params, inputs=params, outputs=params
            )
        with gr.Row():
            run_btn = gr.Button("Run")
            run_btn.click(func_run, inputs=inputs + params, outputs=outputs)
            export_btn = gr.Button(
                "Export (Result will be in Exported file next to Output)"
            )
            export_btn.click(func_export, inputs=[], outputs=exported_file)
        with gr.Row():
            with gr.Column():
                if params:
                    with temp("Params"):
                        for component in params:
                            component.render()
                if inputs:
                    with temp("Inputs"):
                        for component in inputs:
                            component.render()
                if not params and not inputs:
                    gr.Text("No params or inputs")
            with gr.Column():
                with temp("Outputs"):
                    for component in outputs:
                        component.render()
                with temp("Exported file"):
                    exported_file.render()

    return demo


def load_saved_params(path: str) -> Dict:
    """Load the saved params from path to a dataframe"""
    # get all pickle files
    files = list(sorted(Path(path).glob("*.pkl")))
    data: Dict[str, Any] = {"_id": [None] * len(files)}
    for idx, each_file in enumerate(files):
        with open(each_file, "rb") as f:
            each_data = pickle.load(f)
        data["_id"][idx] = Path(each_file).stem
        for key, value in each_data.items():
            if key not in data:
                data[key] = [None] * len(files)
            data[key][idx] = value

    return data


def build_pipeline_ui(config: dict, pipeline_def):
    """Build a tab from config file"""
    inputs_name = list(config.get("inputs", {}).keys())
    params_name = list(config.get("params", {}).keys())
    outputs_def = config.get("outputs", [])

    output_dir: Path = Path(storage.url(pipeline_def().config.store_result))
    exported_dir = output_dir.parent / "exported"
    exported_dir.mkdir(parents=True, exist_ok=True)

    save_dir = (
        output_dir.parent
        / "saved"
        / f"{pipeline_def.__module__}.{pipeline_def.__name__}"
    )
    save_dir.mkdir(parents=True, exist_ok=True)

    resultlog = getattr(pipeline_def, "_promptui_resultlog", ResultLog)
    allowed_resultlog_callbacks = {i for i in dir(resultlog) if not i.startswith("__")}

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
        with storage.open(
            storage.url(
                pipeline.config.store_result, pipeline.last_run.id(), "params.pkl"
            ),
            "wb",
        ) as f:
            pickle.dump(params, f)
        if outputs_def:
            outputs = []
            for output_def in outputs_def:
                output = pipeline.last_run.logs(output_def["step"])
                getter = output_def.get("getter", None)
                if getter and getter in allowed_resultlog_callbacks:
                    output = getattr(resultlog, getter)(output)
                outputs.append(output)
            if len(outputs_def) == 1:
                return outputs[0]
            return outputs

    def save_func(*args):
        params = {name: value for name, value in zip(params_name, args)}
        filename = save_dir / f"{int(time.time())}.pkl"
        with open(filename, "wb") as f:
            pickle.dump(params, f)
        gr.Info("Params saved")

        data = load_saved_params(str(save_dir))
        return pd.DataFrame(data)

    def load_params_func():
        data = load_saved_params(str(save_dir))
        return pd.DataFrame(data)

    def activate_params_func(ev: gr.SelectData, *args):
        data = load_saved_params(str(save_dir))
        output_args = [each for each in args]
        if ev.value is None:
            gr.Info(f'Blank value: "{ev.value}". Skip')
            return output_args

        column = list(data.keys())[ev.index[1]]

        if column not in params_name:
            gr.Info(f'Column "{column}" not in params. Skip')
            return output_args

        value = data[column][ev.index[0]]
        if value is None:
            gr.Info(f'Blank value: "{ev.value}". Skip')
            return output_args

        output_args[params_name.index(column)] = value

        return output_args

    def export_func():
        name = (
            f"{pipeline_def.__module__}.{pipeline_def.__name__}_{datetime.now()}.xlsx"
        )
        path = str(exported_dir / name)
        gr.Info(f"Begin exporting {name}...")
        try:
            export(config=config, pipeline_def=pipeline_def, output_path=path)
        except Exception as e:
            raise gr.Error(f"Failed to export. Please contact project's AIR: {e}")
        gr.Info(f"Exported {name}. Please go to the `Exported file` tab to download")
        return path

    return construct_pipeline_ui(
        config, run_func, save_func, load_params_func, activate_params_func, export_func
    )
