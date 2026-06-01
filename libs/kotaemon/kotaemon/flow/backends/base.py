import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import Function


class Backend:
    """Track the running state of a Function in a thread-safe manner"""

    def __init__(self):
        self._ff_in_run: dict[
            int, bool
        ] = {}  # whether the pipeline is in the run process
        self._ff_prefix: dict[int, str] = {}  # only root node has prefix as empty ""
        self._ff_name: dict[int, str] = {}  # only root node has name as empty ""
        self._ff_run_id: dict[int, str] = {}  # the current run id
        self._ff_flow_name: dict[int, str] = {}  # the run name
        self._func: "Function"

    @property
    def in_run(self) -> bool:
        """Whether the node is in run process"""
        return self._ff_in_run.get(threading.get_ident(), False)

    @in_run.setter
    def in_run(self, value: bool):
        self._ff_in_run[threading.get_ident()] = value

    @in_run.deleter
    def in_run(self):
        del self._ff_in_run[threading.get_ident()]

    @property
    def prefix(self) -> str:
        """Prefix of the execution flow"""
        return self._ff_prefix.get(threading.get_ident(), "")

    @prefix.setter
    def prefix(self, value: str):
        self._ff_prefix[threading.get_ident()] = value

    @prefix.deleter
    def prefix(self):
        del self._ff_prefix[threading.get_ident()]

    @property
    def name(self) -> str:
        """Name of the function in the function flow"""
        return self._ff_name.get(threading.get_ident(), "")

    @name.setter
    def name(self, value: str):
        self._ff_name[threading.get_ident()] = value

    @name.deleter
    def name(self):
        del self._ff_name[threading.get_ident()]

    @property
    def run_id(self) -> str:
        """Return execution id"""
        return self._ff_run_id.get(threading.get_ident(), "")

    @run_id.setter
    def run_id(self, value: str):
        self._ff_run_id[threading.get_ident()] = value

    @run_id.deleter
    def run_id(self):
        self._ff_run_id.pop(threading.get_ident(), None)

    @property
    def flow_name(self) -> str:
        """Name of the execution flow"""
        return self._ff_flow_name.get(threading.get_ident(), "")

    @flow_name.setter
    def flow_name(self, value: str):
        self._ff_flow_name[threading.get_ident()] = value

    @flow_name.deleter
    def flow_name(self):
        self._ff_flow_name.pop(threading.get_ident(), None)

    @property
    def qualidx(self) -> str:
        """Return the qualified execution ids for this node"""

        return f"{self.flow_name}|{self.run_id}|{self.abs_path}"

    @property
    def parent_qualidx(self) -> str:
        """Return the qualified execution ids for the parent node"""
        ident = threading.get_ident()
        return f"{self.flow_name}|{self.run_id}|{self._ff_prefix.get(ident, '')}"

    @property
    def flow_qualidx(self):
        """Return the qualified execution flow id"""
        return f"{self.flow_name}|{self.run_id}"

    @property
    def abs_path(self) -> str:
        """Get the node absolute path in execution flow.

        Note: only available during execution

        Path to node is similar to path to folder:
            .: root node
            .a: to node a
            .a.a1.a2: travel from root node to node a2

        Returns:
            str: absolute path of the node
        """
        ident = threading.get_ident()

        if self._ff_prefix.get(ident, "") == ".":
            return f".{self._ff_name.get(ident, '')}"

        return f"{self._ff_prefix.get(ident, '')}.{self._ff_name.get(ident, '')}"

    def track(self, **kwargs):
        """Track node info

        TODO: this operation is heavily depended on _prepare_child.exec, should make
        that piece of code relate to this Backend. Otherwise, tough job to maintain 2
        pieces of code that relate to each other in 2 different places that do not
        look relate to each other.
        """
        ident = threading.get_ident()

        self._ff_in_run[ident] = True
        self._ff_prefix[ident] = kwargs.get("prefix", "")
        self._ff_name[ident] = kwargs.get("name", "")
        self._ff_run_id[ident] = kwargs.get("run_id", "")
        self._ff_flow_name[ident] = kwargs.get("flow_name", "")

    def clear(self):
        """Clear the tracking info"""
        ident = threading.get_ident()
        self._ff_in_run.pop(ident, None)
        self._ff_prefix.pop(ident, None)
        self._ff_name.pop(ident, None)
        self._ff_run_id.pop(ident, None)
        self._ff_flow_name.pop(ident, None)

    def exec(self, run, args, kwargs):
        """Execute the pipeline's run"""
        return run(*args, **kwargs)

    def attach(self, func: "Function"):
        self._func = func
