from importlib.metadata import version
from pathlib import Path

import gradio as gr
import requests
from theflow.settings import settings


def get_remote_doc(url: str) -> str:
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.text
    except Exception as e:
        print(f"Failed to fetch document from {url}: {e}")
        return ""


def download_changelogs(release_url: str) -> str:
    try:
        res = requests.get(release_url).json()
        changelogs = res.get("body", "")

        return changelogs
    except Exception as e:
        print(f"Failed to fetch changelogs from {release_url}: {e}")
        return ""


class HelpPage:
    def __init__(
        self,
        app,
        doc_dir: str = settings.KH_DOC_DIR,
        remote_content_url: str = "https://raw.githubusercontent.com/Cinnamon/kotaemon",
        app_version: str | None = settings.KH_APP_VERSION,
        changelogs_cache_dir: str
        | Path = (Path(settings.KH_APP_DATA_DIR) / "changelogs"),
    ):
        self._app = app
        self.doc_dir = Path(doc_dir)
        self.remote_content_url = remote_content_url
        self.app_version = app_version
        self.changelogs_cache_dir = Path(changelogs_cache_dir)

        self.changelogs_cache_dir.mkdir(parents=True, exist_ok=True)

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
                if self.app_version:
                    about_md = f"Version: {self.app_version}\n\n{about_md}"
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
            # try retrieve from cache
            changelogs = ""

            if (self.changelogs_cache_dir / f"{version}.md").exists():
                with open(self.changelogs_cache_dir / f"{version}.md", "r") as fi:
                    changelogs = fi.read()
            else:
                release_url_base = (
                    "https://api.github.com/repos/Cinnamon/kotaemon/releases"
                )
                changelogs = download_changelogs(
                    release_url=f"{release_url_base}/tags/v{self.app_version}"
                )

                # cache the changelogs
                if not self.changelogs_cache_dir.exists():
                    self.changelogs_cache_dir.mkdir(parents=True, exist_ok=True)
                with open(
                    self.changelogs_cache_dir / f"{self.app_version}.md", "w"
                ) as fi:
                    fi.write(changelogs)

            if changelogs:
                with gr.Accordion(f"Changelogs (v{self.app_version})"):
                    gr.Markdown(changelogs)
