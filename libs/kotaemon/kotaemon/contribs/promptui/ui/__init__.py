from typing import Union

import gradio as gr
import yaml
from theflow.utils.modules import import_dotted_string

from ..themes import John
from .chat import build_chat_ui
from .pipeline import build_pipeline_ui


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
        if value["ui-type"] == "chat":
            demos.append(build_chat_ui(value, pipeline_def).queue())
        else:
            demos.append(build_pipeline_ui(value, pipeline_def).queue())
    if len(demos) == 1:
        demo = demos[0]
    else:
        demo = gr.TabbedInterface(
            demos,
            tab_names=list(config_dict.keys()),
            title="PromptUI from kotaemon",
            analytics_enabled=False,
            theme=John(),
        )

    demo.queue()

    return demo
