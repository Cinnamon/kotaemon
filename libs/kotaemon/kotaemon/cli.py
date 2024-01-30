import os

import click
import yaml
from trogon import tui


# check if the output is not a .yml file -> raise error
def check_config_format(config):
    if os.path.exists(config):
        if isinstance(config, str):
            with open(config) as f:
                yaml.safe_load(f)
        else:
            raise ValueError("config must be yaml format.")


@tui(command="ui", help="Open the terminal UI")  # generate the terminal UI
@click.group()
def main():
    pass


@click.group()
def promptui():
    pass


main.add_command(promptui)


@promptui.command()
@click.argument("export_path", nargs=1)
@click.option("--output", default="promptui.yml", show_default=True, required=False)
def export(export_path, output):
    """Export a pipeline to a config file"""
    import sys

    from theflow.utils.modules import import_dotted_string

    from kotaemon.contribs.promptui.config import export_pipeline_to_config

    sys.path.append(os.getcwd())
    cls = import_dotted_string(export_path, safe=False)
    export_pipeline_to_config(cls, output)
    check_config_format(output)


@promptui.command()
@click.argument("run_path", required=False, default="promptui.yml")
@click.option(
    "--share",
    is_flag=True,
    show_default=True,
    default=False,
    help="Share the app through Gradio. Requires --username to enable authentication.",
)
@click.option(
    "--username",
    required=False,
    help=(
        "Username for the user. If not provided, the promptui will not have "
        "authentication."
    ),
)
@click.option(
    "--password",
    required=False,
    help="Password for the user. If not provided, will be prompted.",
)
@click.option(
    "--appname",
    required=False,
    help="The share app subdomain. Requires --share and --username",
)
@click.option(
    "--port",
    required=False,
    help="Port to run the app. If not provided, will $GRADIO_SERVER_PORT (7860)",
)
def run(run_path, share, username, password, appname, port):
    """Run the UI from a config file

    Examples:

        \b
        # Run with default config file
        $ kh promptui run

        \b
        # Run with username and password supplied
        $ kh promptui run --username admin --password password

        \b
        # Run with username and prompted password
        $ kh promptui run --username admin

        # Run and share to promptui
        # kh promptui run --username admin --password password --share --appname hey \
                --port 7861
    """
    import sys

    from kotaemon.contribs.promptui.ui import build_from_dict

    sys.path.append(os.getcwd())

    check_config_format(run_path)
    demo = build_from_dict(run_path)

    params: dict = {}
    if username is not None:
        if password is not None:
            auth = (username, password)
        else:
            auth = (username, click.prompt("Password", hide_input=True))
        params["auth"] = auth

    port = int(port) if port else int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    params["server_port"] = port

    if share:
        if username is None:
            raise ValueError(
                "Username must be provided to enable authentication for sharing"
            )
        if appname:
            from kotaemon.contribs.promptui.tunnel import Tunnel

            tunnel = Tunnel(
                appname=str(appname), username=str(username), local_port=port
            )
            url = tunnel.run()
            print(f"App is shared at {url}")
        else:
            params["share"] = True
            print("App is shared at Gradio")

    demo.launch(**params)


@main.command()
@click.argument("module", required=True)
@click.option(
    "--output", default="docs.md", required=False, help="The output markdown file"
)
@click.option(
    "--separation-level", required=False, default=1, help="Organize markdown layout"
)
def makedoc(module, output, separation_level):
    """Make documentation for module `module`

    Example:

        \b
        # Make component documentation for kotaemon library
        $ kh makedoc kotaemon
    """
    from kotaemon.contribs.docs import make_doc

    make_doc(module, output, separation_level)
    print(f"Documentation exported to {output}")


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
