"""Export logs into Excel file"""
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Type, Union

import pandas as pd
import yaml
from theflow.storage import storage
from theflow.utils.modules import import_dotted_string

from kotaemon.base import BaseComponent

from .logs import ResultLog


def from_log_to_dict(pipeline_cls: Type[BaseComponent], log_config: dict) -> dict:
    """Export the log to panda dataframes

    Args:
        pipeline_cls (Type[BaseComponent]): Pipeline class
        log_config (dict): Log config

    Returns:
        dataframe
    """
    # get the directory
    pipeline_log_path = storage.url(pipeline_cls().config.store_result)
    dirs = list(sorted([f.path for f in os.scandir(pipeline_log_path) if f.is_dir()]))

    # get resultlog callback
    resultlog = getattr(pipeline_cls, "_promptui_resultlog", ResultLog)
    allowed_resultlog_callbacks = {i for i in dir(resultlog) if not i.startswith("__")}

    ids = []
    params: Dict[str, List[Any]] = {}
    logged_infos: Dict[str, List[Any]] = {}

    for idx, each_dir in enumerate(dirs):
        ids.append(str(Path(each_dir).name))

        # get the params
        params_file = os.path.join(each_dir, "params.pkl")
        if os.path.exists(params_file):
            with open(params_file, "rb") as f:
                each_params = pickle.load(f)
            for key, value in each_params.items():
                if key not in params:
                    params[key] = [None] * len(dirs)
                params[key][idx] = value

        # get the progress
        progress_file = os.path.join(each_dir, "progress.pkl")
        if os.path.exists(progress_file):
            with open(progress_file, "rb") as f:
                progress = pickle.load(f)

            for name, col_info in log_config.items():
                step = col_info["step"]
                getter = col_info.get("getter", None)
                if name not in logged_infos:
                    logged_infos[name] = [None] * len(dirs)

                if step not in progress:
                    continue

                info = progress[step]
                if getter:
                    if getter in allowed_resultlog_callbacks:
                        info = getattr(resultlog, getter)(info)
                else:
                    implicit_name = f"get_{name}"
                    if implicit_name in allowed_resultlog_callbacks:
                        info = getattr(resultlog, implicit_name)(info)
                logged_infos[name][idx] = info

    return {"ids": ids, **params, **logged_infos}


def export(config: dict, pipeline_def, output_path):
    """Export from config to Excel file"""

    pipeline_name = f"{pipeline_def.__module__}.{pipeline_def.__name__}"

    # export to Excel
    if not config.get("logs", {}):
        raise ValueError(f"Pipeline {pipeline_name} has no logs to export")

    pds: Dict[str, pd.DataFrame] = {}
    for log_name, log_def in config["logs"].items():
        pds[log_name] = pd.DataFrame(from_log_to_dict(pipeline_def, log_def))

    # from the list of pds, export to Excel to output_path
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:  # type: ignore
        for log_name, df in pds.items():
            df.to_excel(writer, sheet_name=log_name)


def export_from_dict(
    config: Union[str, dict],
    pipeline: Union[str, Type[BaseComponent]],
    output_path: str,
):
    """CLI to export the logs of a pipeline into Excel file

    Args:
        config_path (str): Path to the config file
        pipeline_name (str): Name of the pipeline
        output_path (str): Path to the output Excel file
    """
    # get the pipeline class and the relevant config dict
    config_dict: dict
    if isinstance(config, str):
        with open(config) as f:
            config_dict = yaml.safe_load(f)
    elif isinstance(config, dict):
        config_dict = config
    else:
        raise TypeError(f"`config` must be str or dict, not {type(config)}")

    pipeline_name: str
    pipeline_cls: Type[BaseComponent]
    pipeline_config: dict
    if isinstance(pipeline, str):
        if pipeline not in config_dict:
            raise ValueError(f"Pipeline {pipeline} not found in config file")
        pipeline_name = pipeline
        pipeline_cls = import_dotted_string(pipeline, safe=False)
        pipeline_config = config_dict[pipeline]
    elif isinstance(pipeline, type) and issubclass(pipeline, BaseComponent):
        pipeline_name = f"{pipeline.__module__}.{pipeline.__name__}"
        if pipeline_name not in config_dict:
            raise ValueError(f"Pipeline {pipeline_name} not found in config file")
        pipeline_cls = pipeline
        pipeline_config = config_dict[pipeline_name]
    else:
        raise TypeError(
            f"`pipeline` must be str or subclass of BaseComponent, not {type(pipeline)}"
        )

    export(pipeline_config, pipeline_cls, output_path)
