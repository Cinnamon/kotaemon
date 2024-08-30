# import shutil
from pathlib import Path
from typing import Any, Iterable

import mkdocs_gen_files

# get the root source code directory
doc_dir_name = "docs"
doc_dir = Path(__file__)
while doc_dir.name != doc_dir_name and doc_dir != doc_dir.parent:
    doc_dir = doc_dir.parent

if doc_dir == doc_dir.parent:
    raise ValueError(f"root_name ({doc_dir_name}) not in path ({str(Path(__file__))}).")

nav_title_map = {"cli": "CLI", "llms": "LLMs"}


def generate_docs_for_src_code(
    code_dir: Path, target_doc_folder: str, ignored_modules: Iterable[Any] = []
):
    if not code_dir.is_dir():
        raise ModuleNotFoundError(str(code_dir))

    nav = mkdocs_gen_files.Nav()

    for path in sorted(code_dir.rglob("*.py")):
        # ignore modules with name starts with underscore (i.e. __init__)
        # if path.name.startswith("_") or path.name.startswith("test"):
        #     continue

        module_path = path.relative_to(code_dir).with_suffix("")
        doc_path = path.relative_to(code_dir).with_suffix(".md")
        full_doc_path = Path(target_doc_folder, doc_path)

        parts = list(module_path.parts)

        if parts[-1] == "__init__":
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
            parts.pop()

        if not parts:
            continue

        if "tests" in parts:
            continue

        identifier = ".".join(parts)
        ignore = False
        for each_module in ignored_modules:
            if identifier.startswith(each_module):
                ignore = True
                break
        if ignore:
            continue

        nav_titles = [
            nav_title_map.get(name, name.replace("_", " ").title()) for name in parts
        ]
        nav[nav_titles] = doc_path.as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as f:
            f.write(f"::: {identifier}")

        # this method works in docs folder
        mkdocs_gen_files.set_edit_path(
            full_doc_path, Path("..") / path.relative_to(code_dir.parent)
        )

    with mkdocs_gen_files.open(f"{target_doc_folder}/Summary.md", "w") as nav_file:
        nav_file.writelines(nav.build_literate_nav())


generate_docs_for_src_code(
    code_dir=doc_dir.parent / "libs" / "kotaemon" / "kotaemon",
    target_doc_folder="reference",
    ignored_modules={"contribs"},
)
