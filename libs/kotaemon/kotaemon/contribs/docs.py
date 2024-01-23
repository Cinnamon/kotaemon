import inspect
from collections import defaultdict

from theflow.utils.documentation import get_function_documentation_from_module


def from_definition_to_markdown(definition: dict) -> str:
    """From definition to markdown"""

    # Handle params
    params = " N/A\n"
    if definition["params"]:
        params = "\n| Name | Description | Type | Default |\n"
        params += "| --- | --- | --- | --- |\n"
        for name, p in definition["params"].items():
            type_ = p["type"].__name__ if inspect.isclass(p["type"]) else p["type"]
            params += f"| {name} | {p['desc']} | {type_} | {p['default']} |\n"

    # Handle nodes
    nodes = " N/A\n"
    if definition["nodes"]:
        nodes = "\n| Name | Description | Type | Input | Output |\n"
        nodes += "| --- | --- | --- | --- | --- |\n"
        for name, n in definition["nodes"].items():
            type_ = n["type"].__name__ if inspect.isclass(n["type"]) else str(n["type"])
            input_ = (
                n["input"].__name__ if inspect.isclass(n["input"]) else str(n["input"])
            )
            output_ = (
                n["output"].__name__
                if inspect.isclass(n["output"])
                else str(n["output"])
            )
            nodes += f"|{name}|{n['desc']}|{type_}|{input_}|{output_}|\n"

    description = inspect.cleandoc(definition["desc"])
    return f"{description}\n\n_**Params:**_{params}\n_**Nodes:**_{nodes}"


def make_doc(module: str, output: str, separation_level: int):
    """Run exporting components to markdown

    Args:
        module (str): module name
        output_path (str): output path to save
        separation_level (int): level of separation
    """
    documentation = sorted(
        get_function_documentation_from_module(module).items(), key=lambda x: x[0]
    )

    entries = defaultdict(list)

    for name, definition in documentation:
        section = name.split(".")[separation_level].capitalize()
        cls_name = name.split(".")[-1]

        markdown = from_definition_to_markdown(definition)
        entries[section].append(f"### {cls_name}\n{markdown}")

    final = "\n".join(
        [f"## {section}\n" + "\n".join(entries[section]) for section in entries]
    )

    with open(output, "w") as f:
        f.write(final)
