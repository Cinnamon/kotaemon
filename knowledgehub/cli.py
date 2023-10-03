import os

import click
import yaml


# check if the output is not a .yml file -> raise error
def check_config_format(config):
    if os.path.exists(config):
        if isinstance(config, str):
            with open(config) as f:
                yaml.safe_load(f)
        else:
            raise ValueError("config must be yaml format.")


@click.group()
def main():
    pass


@click.group()
def promptui():
    pass


main.add_command(promptui)


@promptui.command()
@click.argument("export_path", nargs=1)
@click.option("--output", default="promptui.yml", required=False)
def export(export_path, output):
    import sys

    from theflow.utils.modules import import_dotted_string

    from kotaemon.contribs.promptui.config import export_pipeline_to_config

    sys.path.append(os.getcwd())
    cls = import_dotted_string(export_path, safe=False)
    export_pipeline_to_config(cls, output)
    check_config_format(output)


@promptui.command()
@click.argument("run_path", required=False, default="promptui.yml")
def run(run_path):
    from kotaemon.contribs.promptui.ui import build_from_dict

    build_from_dict(run_path)
    check_config_format(run_path)


@main.command()
@click.option(
    "--template",
    default="project-default",
    required=False,
    help="Template name",
    show_default=True,
)
def start_project(template):
    """Start a project from a template.

    Important: the value for --template corresponds to the name of the template folder,
    which is located at https://github.com/Cinnamon/kotaemon/tree/main/templates
    The default value is "project-default", which should work when you are starting a
    client project.
    """

    print("Retrieving template...")
    os.system(
        "cookiecutter git@github.com:Cinnamon/kotaemon.git "
        f"--directory='templates/{template}'"
    )


if __name__ == "__main__":
    main()
