from __future__ import annotations

import pickle
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from ..base import Function
    from ..context import Context

from ..storage import storage


class RunStructure:
    """The structure of a run directory"""

    progress = "progress.pkl"
    input = "input.pkl"
    output = "output.pkl"
    config = "config.yaml"
    # kwargs = "kwargs.pkl" ----> Should consolidate with config.yaml? Plug-n-play
    # pipeline = "pipeline.yaml" ---> Should consolidate with config.yaml? Plug-n-play
    # pipeline_visualization = "pipeline_visualization.dot"
    # run_visualization = "run_visualization.dot"


class RunManager:
    def __init__(self, dir: str):
        self.dir: Path = Path(dir)

    def list(self) -> list:
        """List all runs"""
        # import pandas as pd  # TODO: reimplement json_normalize

        # output = []
        # for each_dir in self.dir.iterdir():
        #     if not each_dir.is_dir():
        #         continue

        #     run_info = {"name": each_dir.name}
        #     with (each_dir / RunStructure.output).open("rb") as fi:
        #         run_info.update(
        #             pd.json_normalize({"output": pickle.load(fi)}).to_dict(
        #                 orient="records"
        #             )[0]
        #         )
        #     with (each_dir / RunStructure.input).open("rb") as fi:
        #         input_ = pickle.load(fi)
        #         input_ = {"input": {"args": input_["args"], **input_["kwargs"]}}
        #         run_info.update(pd.json_normalize(input_).to_dict(orient="records")[0])

        #     output.append(run_info)

        # return output
        return []

    def get(self):
        pass

    def delete(self, name: str):
        """Delete a run base a name

        Args:
            name: the name of the run
        """
        shutil.rmtree(self.dir / name)


class RunTracker:
    """Define run-related methods to track the information in the run

    Args:
        obj: the Function that contains necessary information to log info
        which_progress: the name of the progress to store the run information. Can be
            useful to track multiple progresses in the same run. Default to
            "__progress__" which refers to the current progress.
        config: the config of the run
    """

    def __init__(self, obj: Function, which_progress: str = "__progress__"):
        self._obj = obj
        self._context: Context = obj.context

        self._config: dict = {}
        self._progress = f"{obj.fl.flow_name}|{obj.fl.run_id}|{which_progress}"
        self._context.create_context(self._progress, exist_ok=True)

        if not obj.fl.prefix:
            # root pipeline
            self._context.set("name", obj.fl.flow_name, context=self._progress)
            self._context.set("id", obj.fl.run_id, context=self._progress)

    def log_progress(self, name: str, **kwargs):
        """Set the input and output of the step

        Args:
            name: name of the step
            kwargs: will be logged to the step progress as key, value
        """
        value = self._context.get(name, default={}, context=self._progress)
        value.update(kwargs)
        self._context.set(name, value, context=self._progress)

    def logs(self, name: str | None = None) -> dict:
        """Get the information of each step

        Args:
            name: name of the pipeline or step. If None, get progress of all steps

        Returns:
            input and output of the respective pipeline or step
        """
        return self._context.get(name, context=self._progress)

    def steps(self) -> list[str]:
        """Get the steps of the run

        Returns:
            the steps of the run
        """
        return list(self.logs(name=None).keys())

    def input(self, name: str = ".") -> Any:
        """Get the input of a pipeline

        Args:
            name: name of the pipeline or step.

        Returns:
            input of the respective pipeline
        """
        return self.logs(name=name)["input"]

    def output(self, name: str = ".") -> Any:
        """Get the output of a pipeline

        Args:
            name: name of the pipeline or step.

        Returns:
            output of the respective pipeline
        """
        return self.logs(name=name)["output"]

    def persist(self):
        """Persist the run result to a store"""
        dir = storage.join(self._obj.config.store_result, self.id())
        with storage.open(storage.join(dir, "progress.pkl"), "wb") as fo:
            pickle.dump(self.logs(name=None), fo)
        with storage.open(storage.join(dir, "config.yml"), "w") as fo:
            yaml.dump(self._config, fo)

    def id(self) -> str:
        """Get the id of the run

        Returns:
            the id of the run
        """
        return self._context.get("id", context=self._progress)

    def load(self, run_path: str | Path):
        """Load a run

        Args:
            run_path: the path to the run
        """
        run_path = Path(run_path)
        with (run_path / "progress.pkl").open("rb") as fi:
            progress = pickle.load(fi)

        for key, value in progress.items():
            self._context.set(key, value, context=self._progress)

    @property
    def config(self) -> dict | None:
        """Get the config of the run

        Returns:
            the config of the run
        """
        return self._config

    @config.setter
    def config(self, config: dict):
        """Set the config of the run

        Args:
            config: the config of the run
        """
        self._config = config
