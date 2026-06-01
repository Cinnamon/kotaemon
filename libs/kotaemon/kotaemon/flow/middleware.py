import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .base import Function

logger = logging.getLogger(__name__)


class Middleware:
    """Middleware template to work on the input and output of a node"""

    def __init__(self, obj: "Function", next_call: Callable):
        if obj is None:
            raise ValueError("obj must be specified")
        self.obj = obj
        self.next_call = next_call

    @abstractmethod
    def __call__(self, *args, **kwargs):
        """Execute the middleware"""
        ...


class SkipComponentMiddleware(Middleware):
    """Skip executing the component if the user specifies so

    This middleware utilizes the following context key:
        - good_to_run: if True, the component can be run
        - from: skip components in a pipeline earlier than the specified component
        - to: skip components in a pipeline later than the specified component (only
            valid for parallel)

    This middleware utilizes the following context name:
        - __from_run__: this context store the output of the previous run, specified
        by the user

    This middleware reserves these kwargs when calling run:
        - _ff_from_run: the path to the past run tracker, which will be used to
        substitute output of skipped steps
        - _ff_from: skip the steps earlier than the specified step
        - _ff_to: skip the steps later than the specified step (only valid for parallel)

    """

    def __call__(self, *args, **kwargs):
        """Run the middleware in the context of a wrapping step

        If the step is marked as good_to_run. Run the step as usual.
        If the step is not marked as good_to_run:
            - Check if the step name matches the name from `from`. If so, it means that
            we would want to run this step (as probably all the steps before this step
            in the pipeline have been skipped). So we will run this step, and mark
            good_to_run as True so that later step will be run as normal.
            - Check if the step name matchs the name from `to`. If so, we will run this
            step and mark good_to_run as False so that later step will be skipped.
        """
        from .runs.base import RunTracker

        # Gather the from, to and from_run from the root pipeline
        if _ff_from := kwargs.pop("_ff_from", None):
            self.obj.context.set("from", _ff_from, context=self.obj.fl.flow_qualidx)
        if _ff_to := kwargs.pop("_ff_to", None):
            self.obj.context.set("to", _ff_to, context=self.obj.fl.flow_qualidx)
        if _ff_from_run := kwargs.pop("_ff_from_run", None):
            from_run = RunTracker(self.obj, "__from_run__")
            from_run.load(run_path=_ff_from_run)

        self.obj.context.get("from", context=self.obj.fl.flow_qualidx)
        if _from := self.obj.context.get("from", context=self.obj.fl.flow_qualidx):
            from .utils.paths import is_parent_of_child

            if is_parent_of_child(self.obj.fl.name, _from):
                self.obj.context.set("good_to_run", False, context=self.obj.fl.qualidx)

        # Decide whether to run or fetch from the cache
        _ff_name = self.obj.fl.abs_path

        good_to_run: bool = True
        if self.obj.context.has_context(context=self.obj.fl.parent_qualidx):
            good_to_run = self.obj.context.get(
                "good_to_run", default=True, context=self.obj.fl.parent_qualidx
            )

        if good_to_run is False:
            from .utils.paths import is_name_matched

            if is_name_matched(
                _ff_name, self.obj.context.get("from", context=self.obj.fl.flow_qualidx)
            ):
                self.obj.context.set(
                    "good_to_run", True, context=self.obj.fl.parent_qualidx
                )
                logger.info(f"Run {_ff_name}. Turn good_to_run from False to True")
                self.obj.log_progress(_ff_name, status="run")
                return self.next_call(*args, **kwargs)

            try:
                from_run = RunTracker(self.obj, which_progress="__from_run__")
                output = from_run.output(name=_ff_name)
                logger.info(f"Cached {_ff_name}")
                self.obj.log_progress(_ff_name, status="cached")
                return output
            except Exception as e:
                logger.warning(f"Failed to get output from run: {e}")
                self.obj.log_progress(_ff_name, status="run")
                return self.next_call(*args, **kwargs)

        if (
            self.obj.context.get("to", None, context=self.obj.fl.flow_qualidx)
            == _ff_name
        ):
            self.obj.context.set("good_to_run", False, context=self.obj.fl.flow_qualidx)

        self.obj.log_progress(_ff_name, status="run")
        return self.next_call(*args, **kwargs)


class TrackProgressMiddleware(Middleware):
    """Store all information of the current run to the context

    A node can have 1 of the 3 states:
        - run: the node is run normally
        - cached: the node is not run, and the output is retrieved from the last run
    """

    def __call__(self, *args, **kwargs):
        import inspect

        abs_pathx = self.obj.fl.abs_path
        if abs_pathx == ".":
            from .runs.base import RunTracker

            last_run = RunTracker(self.obj)
            last_run.config = self.obj.config.dump()
            self.obj.last_run = last_run

        _input = {"args": args, "kwargs": kwargs}
        try:
            _output = self.next_call(*args, **kwargs)
        except Exception as e:
            self.obj.log_progress(abs_pathx, input=_input, output=None, error=str(e))
            raise e from None

        if not (
            inspect.isgenerator(_output)
            or inspect.isasyncgen(_output)
            or inspect.iscoroutine(_output)
            or inspect.isawaitable(_output)
        ):
            try:
                self.obj.log_progress(abs_pathx, input=_input, output=_output)
            except Exception as e:
                import traceback

                logger.warning(f"Failed to log progress: {e}: {traceback.format_exc()}")

        if abs_pathx == ".":
            # will be set by the previous code
            last_run.persist()  # type: ignore

        return _output


class CachingMiddleware(Middleware):
    """Cache the output of a function and reuse that output if the input and
    function definition is the same
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from .settings import settings
        from .utils.modules import deserialize

        self._cache = deserialize(settings.CACHE, safe=False)

    def __call__(self, *args, **kwargs):
        try:
            hash_key = self.create_key(*args, **kwargs)
            if hash_key in self._cache:
                return self._cache[hash_key]
        except Exception as e:
            logger.exception(f"Failed to create key: {e}")
            return self.next_call(*args, **kwargs)

        output = self.next_call(*args, **kwargs)
        self._cache[hash_key] = output
        return output

    def create_key(self, *args, **kwargs) -> str:
        """Create a key based on the input and Function's definition

        Specifically, it depends on:
            - the `run`'s input
            - the Function's class name
            - the Function's dump

        Args:
            *args: positional arguments of the run
            **kwargs: keyword arguments of the run

        Returns:
            str: the key
        """
        from .utils.hashes import naivehash

        hasher = naivehash()
        content = {
            "input": {"args": args, "kwargs": kwargs},
            "definition": self.obj.dump(),
            "name": self.obj.__class__.__name__,
        }
        return hasher(content)
