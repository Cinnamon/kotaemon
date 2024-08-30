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


def generate_docs_for_examples_readme(
    examples_dir: Path, target_doc_folder: str, ignored_modules: Iterable[Any] = []
):
    if not examples_dir.is_dir():
        raise ModuleNotFoundError(str(examples_dir))

    nav = mkdocs_gen_files.Nav()

    for path in sorted(examples_dir.rglob("*README.md")):
        # ignore modules with name starts with underscore (i.e. __init__)
        if path.name.startswith("_") or path.name.startswith("test"):
            continue

        module_path = path.parent.relative_to(examples_dir).with_suffix("")
        doc_path = path.parent.relative_to(examples_dir).with_suffix(".md")
        full_doc_path = Path(target_doc_folder, doc_path)

        parts = list(module_path.parts)
        identifier = ".".join(parts)

        if "tests" in parts:
            continue

        ignore = False
        for each_module in ignored_modules:
            if identifier.startswith(each_module):
                ignore = True
                break
        if ignore:
            continue

        nav_titles = [name.replace("_", " ").title() for name in parts]
        nav[nav_titles] = doc_path.as_posix()

        with mkdocs_gen_files.open(full_doc_path, "w") as f:
            f.write(f'--8<-- "{path.relative_to(examples_dir.parent)}"')

        mkdocs_gen_files.set_edit_path(
            full_doc_path, Path("..") / path.relative_to(examples_dir.parent)
        )

    with mkdocs_gen_files.open(f"{target_doc_folder}/NAV.md", "w") as nav_file:
        nav_file.writelines(nav.build_literate_nav())


generate_docs_for_examples_readme(
    examples_dir=doc_dir.parent / "examples",
    target_doc_folder="examples",
)
