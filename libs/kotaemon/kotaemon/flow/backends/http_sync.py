from __future__ import annotations

from typing import TYPE_CHECKING

from ..utils.modules import import_modules
from .base import Backend

if TYPE_CHECKING:
    from litestar.connection import Request
    from litestar.response import Response


def local_only_func_def(func_def: dict) -> dict:
    """Trim the function definition to only contain nodes residing on the same machine

    Nodes on the same machine are those that aren't child of any non-Backend node.
    """

    def is_local_node(node: dict) -> bool:
        return (
            node["configs"]["default_backend"]["__type__"] == "theflow.backends.Backend"
        )

    def handle_child_nodes(node: dict) -> dict:
        if not node["nodes"]:
            return node

        if not is_local_node(node):
            return {
                "function": node["function"],
                "params": node["params"],
                "nodes": {},
                "configs": node["configs"],
            }

        child_nodes = {}
        for name, value in node["nodes"].items():
            child_nodes[name] = handle_child_nodes(value)

        return {
            "function": node["function"],
            "params": node["params"],
            "nodes": child_nodes,
            "configs": node["configs"],
        }

    return handle_child_nodes(func_def)


def general_exception_handler(request: Request, exc: Exception) -> Response:
    import logging

    from litestar.middleware.exceptions.middleware import create_exception_response

    logging.error("Application error:", exc_info=exc)
    return create_exception_response(request, exc)


class HttpSyncBackend(Backend):
    """Execute node through HTTP synchronous request-response model

    Once triggered, the caller node of this backend will store run's args, kwargs and
    node information in the cache with a unique id. It then calls the http endpoint
    with the id, wait for the response. The receiver node will fetch the args, kwargs
    and node information from the cache with the unique id, execute the run like
    normally, and store the result in the cache with the same unique id, and returns
    the unique id to the caller node. The caller node will fetch the result from the
    cache with the unique id and return the result to the parent pipeline.
    """

    def __init__(self, endpoint: str):
        super().__init__()
        self._endpoint = endpoint
        self._reqm, self._uuidm = import_modules("requests", "uuid")

    def exec(self, run, args, kwargs):
        """Execute the pipeline's run remotely"""
        if self._func is None:
            raise RuntimeError(
                "The backend is not attached to a function. If you modify the backend, "
                "please make sure to call `self.fl.attach(self)` in the Function where "
                "you use this backend."
            )

        # store the information in a cache with specific id
        uuid = self._uuidm.uuid4().hex
        self._func.context.set(
            name=uuid,
            value={
                "args": args,
                "kwargs": kwargs,
                "__fl_runstates__": {
                    "name": self.name,
                    "prefix": self.prefix,
                    "run_id": self.run_id,
                    "flow_name": self.flow_name,
                },
            },
        )

        # call the http endpoint with the id, wait for the response
        resp = self._reqm.get(self._endpoint, params={"id": uuid})
        resp.raise_for_status()

        # fetch the result from the cache
        result = self._func.context.get(name=uuid, default=None)
        if result is None:
            raise RuntimeError(
                f"Cannot find the result for {self.name} with id {uuid} in global cache"
            )
        result = result["result"]

        return result

    @classmethod
    def make(cls, func_def: dict | str, minimal: bool = True):
        """Serve the function from a function definition

        Args:
            func_def: The Function definition
            minimal: Whether to remove any unnecessary function from the pipeline
                (those that will be executed remotely). Defaults to True.

        Returns:
            A Litestar app that serves the function
        """
        from theflow import load

        if isinstance(func_def, str):
            import yaml

            with open(func_def) as f:
                func_defd: dict = yaml.safe_load(f)
        else:
            func_defd = func_def

        if minimal:
            func_defd = local_only_func_def(func_defd)

        # load the pipeline from the function definition
        func_defd["configs"]["default_backend"] = {
            "__type__": "theflow.backends.Backend"
        }
        func = load(func_defd, safe=False)

        # wrap the function call into a litestar app
        (ls,) = import_modules("litestar")

        async def predict(id: str) -> str:
            # retrieve info
            context = func.context.get(name=id, default=None)
            if context is None:
                raise RuntimeError(
                    f"Cannot find the context with id {id} in global cache"
                )
            result = func(
                *context["args"],
                **context["kwargs"],
                __fl_runstates__=context["__fl_runstates__"],
            )
            context["result"] = result
            func.context.set(name=id, value=context)

            return id

        app = ls.Litestar(
            route_handlers=[ls.get("/")(predict)],
            exception_handlers={
                Exception: general_exception_handler,
            },
        )

        return app
