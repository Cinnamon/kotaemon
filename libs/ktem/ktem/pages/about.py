import gradio as gr

class AboutPage:
    def __init__(
        self,
        app,
        # doc_dir: str = settings.KH_DOC_DIR,
        # remote_content_url: str = "https://raw.githubusercontent.com/Cinnamon/kotaemon",
        # app_version: str | None = settings.KH_APP_VERSION,
        # changelogs_cache_dir: str
        # | Path = (Path(settings.KH_APP_DATA_DIR) / "changelogs"),
    ):

        self._app = app

        md = """
Our mission -- democratize patient discovery.
"""
        gr.Markdown(md)