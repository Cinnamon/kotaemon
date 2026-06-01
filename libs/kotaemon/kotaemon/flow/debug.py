from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Function


def has_cycle(graph: dict[str, list[str]]) -> bool:
    """Check if a graph has cycle

    Args:
        graph: A graph represented by an adjacency list

    Returns:
        True if the graph has cycle, False otherwise
    """
    visited: set[str] = set()
    path: set[str] = set()

    def visit(vertex):
        if vertex in visited:
            return False
        visited.add(vertex)
        path.add(vertex)
        for neighbour in graph.get(vertex, []):
            if neighbour in path or visit(neighbour):
                return True
        path.remove(vertex)
        return False

    return any(visit(v) for v in graph)


def has_cyclic_dependency(cls: type["Function"]):
    """Check if a component's nodes and params has cyclic dependency

    Args:
        cls: A function

    Returns:
        True if the function has cyclic dependency, False otherwise
    """
    params, nodes = cls._collect_registered_params_and_nodes()
    specs: dict[str, dict] = {}
    graph: dict[str, list[str]] = {}

    # construct dependency graph
    for attr in nodes + params:
        graph[attr] = []
        spec: dict = specs.get(attr, {}) or getattr(cls, attr).to_dict()
        if spec["auto_callback"] or spec["default_callback"]:
            if not spec["depends_on"]:
                continue
            for src in spec["depends_on"]:
                src_spec: dict = specs.get(src, {}) or getattr(cls, src).to_dict()
                if src_spec["auto_callback"] or src_spec["default_callback"]:
                    graph[attr].append(src)

    return has_cycle(graph)


def likely_cyclic_pipeline(a: "Function", max_node_connections: int = 100):
    """Check if a pipeline is likely to have circular loop

    Note, this heuristic assumes that if a pipeline has a lot of node connections, then
    it is likely to have circular loop.

    Args:
        a: A function
        max_node_connections: Maximum number of nodes to check
    """
    from collections import defaultdict

    counter: defaultdict[tuple[str, str, str], int] = defaultdict(int)

    threshold_idx = 0
    to_do_idx = 0
    to_dos = [a]
    while threshold_idx < max_node_connections and to_do_idx < len(to_dos):
        to_do = to_dos[to_do_idx]
        for node in to_do._ff_nodes:
            target = to_do.get_from_path(node)
            if not target:
                continue
            to_dos.append(target)
            triples = (
                f"{to_do.__module__}.{to_do.__class__.__name__}",
                node,
                f"{target.__module__}.{target.__class__.__name__}",
            )
            threshold_idx += 1
            counter[triples] += 1
        to_do_idx += 1

    result = list(counter.items())
    result = sorted(result, key=lambda x: x[1], reverse=True)

    return threshold_idx == max_node_connections, result
