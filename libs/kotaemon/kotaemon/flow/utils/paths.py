import re
from pathlib import Path
from typing import List, Optional, Union

THEFLOW_DIR = ".theflow"


def project_root(loc: Optional[Union[str, Path]] = None) -> Path:
    """Get the root directory of the project (contains .git/). Return cwd if .git/
    doesn't exist

    Args:
        loc: the location to start searching for the root directory. If None,
            assume the current working directory

    Returns:
        the root directory of the project, or None if not found
    """
    if loc is None:
        loc = Path.cwd()
    loc = Path(loc)
    while loc != loc.parent:
        if (loc / ".git").exists():
            return loc
        loc = loc.parent

    return Path.cwd()


def get_theflow_path(loc: Optional[Union[str, Path]]) -> Optional[Path]:
    """Get the theflow directory (contains .theflow/)

    Args:
        loc: the location to start searching for the theflow directory. If None,
            assume the current working directory

    Returns:
        the theflow directory, or None if not found
    """
    loc = Path.cwd() if loc is None else Path(loc)
    while loc != loc.parent:
        if (loc / THEFLOW_DIR).exists():
            return loc / THEFLOW_DIR
        loc = loc.parent

    return None


def default_theflow_path(
    loc: Union[None, str, Path] = None, create: bool = False
) -> Path:
    """Get the theflow directory (.theflow/) or create it if not exists

    It travels up the directory tree until it finds the theflow directory. If not
    found, it creates the theflow directory in the project root folder. If there
    isn't project root folder, it creates the theflow directory in the current
    working directory.

    Args:
        loc: the location to start searching for the theflow directory. If None,
            assume the current working directory
        create: whether to create the theflow directory if not exists

    Returns:
        the theflow directory
    """
    if loc is None:
        loc = Path.cwd()
    loc = Path(loc)
    flow_path = get_theflow_path(loc)
    if flow_path is not None:
        return flow_path

    flow_path = project_root(loc) / THEFLOW_DIR
    if create:
        flow_path.mkdir(exist_ok=True, parents=True)

    return flow_path


def temp_path() -> str:
    """Get the default temporary directory

    Returns:
        the default temporary directory
    """
    import getpass
    import os
    import tempfile

    default: str = os.environ.get("THEFLOW_TEMP_PATH", "")
    if not default:
        try:
            username = getpass.getuser()
        except Exception:
            username = ""
        path = Path(tempfile.gettempdir(), f"theflow_{username}")
    else:
        path = Path(default)
    path.mkdir(exist_ok=True, parents=True)
    return str(path)


def is_name_matched(name: str, pattern: str) -> bool:
    """Check if a name matches a pattern

    This method matches simple pattern with wildcard character "*". For example, the
    pattern "a.*.b" matches "a.c.b" but not "a.b.c.b".

    Args:
        name: the name to check
        pattern: the pattern to match

    Returns:
        True if the name matches the pattern, False otherwise
    """
    pattern_parts: List[str] = [re.escape(part) for part in pattern.split("*")]
    regex_pattern: str = r"^" + r"[^.]+".join(pattern_parts) + r"$"
    return re.findall(regex_pattern, name) != []


def is_parent_of_child(parent: str, child: str) -> bool:
    """Check if a name is a direct parent of another name

    Example:
        >> is_parent_of_child(".main.pipeline_A1", ".main.pipeline_A1.*")
        True
        >> is_parent_of_child(".main.pipeline_A1", ".main.pipeline_A1.pipeline_B1")
        True
        >> is_parent_of_child(".main.pipeline_A1", ".main.pipeline_A2")
        False

    Args:
        parent: the parent name
        child: the child name. The child can be a wildcard pattern

    Returns:
        True if the parent is a parent of the child, False otherwise
    """
    parent, child = parent.strip("."), child.strip(".")
    pattern = ".".join(child.split(".")[:-1])
    return is_name_matched(parent, pattern)


if __name__ == "__main__":
    names = [
        "",
        ".main",
        ".main.pipeline_A1" ".main.pipeline_A1.pipeline_B1",
        ".main.pipeline_A1.pipeline_B1.pipeline_C1",
        ".main.pipeline_A1.pipeline_B1.pipeline_C1.step_a",
        ".main.pipeline_A1.pipeline_B1.pipeline_C1.step_b",
        ".main.pipeline_A1.pipeline_B1.pipeline_C1.step_c",
        ".main.pipeline_A1.pipeline_B2",
        ".main.pipeline_A1.pipeline_B2.pipeline_C2",
        ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_a",
        ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_b",
        ".main.pipeline_A1.pipeline_B2.pipeline_C2.step_c",
        ".main.pipeline_A2",
        ".main.pipeline_A2.pipeline_B1",
        ".main.pipeline_A2.pipeline_B1.pipeline_C1",
        ".main.pipeline_A2.pipeline_B1.pipeline_C1.step_a",
        ".main.pipeline_A2.pipeline_B1.pipeline_C1.step_b",
        ".main.pipeline_A2.pipeline_B1.pipeline_C1.step_c",
        ".main.pipeline_A2.pipeline_B2",
        ".main.pipeline_A2.pipeline_B2.pipeline_C2",
        ".main.pipeline_A2.pipeline_B2.pipeline_C2.step_a",
        ".main.pipeline_A2.pipeline_B2.pipeline_C2.step_b",
        ".main.pipeline_A2.pipeline_B2.pipeline_C2.step_c",
        ".main.next_step",
    ]

    # pattern  = ".main.*.p*.*.step_a"
    # pattern = ".main.*.*.pipeline_C1"
    # pattern = ".main.pipeline_A2"
    pattern = ".*.pipeline*"
    # for name in names:
    #     if is_name_matched(name, pattern):
    #         print(name)

    for name in names:
        if is_parent_of_child(name, pattern):
            print(name, "is parent of", pattern)
