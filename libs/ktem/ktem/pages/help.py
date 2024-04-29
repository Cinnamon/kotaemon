from importlib.metadata import version
from pathlib import Path

import gradio as gr
import requests
from theflow.settings import settings


def get_remote_doc(url):
    try:
        res = requests.get(url)
        return res.text
    except Exception as e:
        print(f"Failed to fetch document from {url}: {e}")
        return ""


def get_changelogs(version):
    release_url = f"https://api.github.com/repos/Cinnamon/kotaemon/releases/{version}"
    try:
        res = requests.get(release_url).json()
        changelogs = res.get("body", "")

        return changelogs
    except Exception as e:
        print(f"Failed to fetch changelogs from {release_url}: {e}")
        return ""


class HelpPage:
    def __init__(self, app):
        self._app = app
        self.doc_dir = Path(settings.KH_DOC_DIR)
        self.remote_content_url = "https://raw.githubusercontent.com/Cinnamon/kotaemon"

        self.app_version = None
        try:
            # Caution: This might produce the wrong version
            # https://stackoverflow.com/a/59533071
            self.app_version = version("kotaemon_app")
        except Exception as e:
            print(f"Failed to get app version: {e}")

        about_md_dir = self.doc_dir / "about.md"
        if about_md_dir.exists():
            with (self.doc_dir / "about.md").open(encoding="utf-8") as fi:
                about_md = fi.read()
        else:  # fetch from remote
            about_md = get_remote_doc(
                f"{self.remote_content_url}/v{self.app_version}/docs/about.md"
            )
        if about_md:
            with gr.Accordion("About"):
                gr.Markdown(about_md)

        user_guide_md_dir = self.doc_dir / "usage.md"
        if user_guide_md_dir.exists():
            with (self.doc_dir / "usage.md").open(encoding="utf-8") as fi:
                user_guide_md = fi.read()
        else:  # fetch from remote
            user_guide_md = get_remote_doc(
                f"{self.remote_content_url}/v{self.app_version}/docs/usage.md"
            )
        if user_guide_md:
            with gr.Accordion("User Guide"):
                gr.Markdown(user_guide_md)

        if self.app_version:
            changelogs = get_changelogs("tags/v" + self.app_version)
            if changelogs:
                with gr.Accordion(f"Changelogs (v{self.app_version})"):
                    gr.Markdown(changelogs)
