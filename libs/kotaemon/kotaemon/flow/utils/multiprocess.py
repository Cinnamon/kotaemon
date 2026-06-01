import multiprocessing
import multiprocessing.managers
from typing import TYPE_CHECKING, Dict, List, cast

if TYPE_CHECKING:
    from ..base import Function


def _run_node(task):
    obj: "Function" = task[0]
    child_name: str = task[1]
    params: Dict = task[2]
    lock = task[3]

    with lock:
        node = getattr(obj, child_name)
    return node(**params)


def parallel(obj: "Function", child_name: str, tasks: List[Dict], **kwargs):
    """Run a node in parallel with multiprocessing.

    This helper function allows accurately keeping track of the the number of time the
    `child_name` node is called from the `obj` parent.

    Args:
        obj (Function): Function object
        child_name (str): Child name
        tasks (List[Dict]): List of parameters for each task
        kwargs: Keyword arguments for multiprocessing.Pool
    """
    manager = None
    try:
        manager = multiprocessing.Manager()
        obj._ff_childs_called = cast("dict", manager.dict(obj._ff_childs_called))
        lock = manager.Lock()

        tasks_mp = [(obj, child_name, task, lock) for task in tasks]
        with multiprocessing.Pool(**kwargs) as pool:
            yield from pool.imap(_run_node, tasks_mp)
    finally:
        if isinstance(obj._ff_childs_called, multiprocessing.managers.DictProxy):
            obj._ff_childs_called = obj._ff_childs_called.copy()
        if manager is not None:
            manager.shutdown()
