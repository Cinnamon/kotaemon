from pathlib import Path

import gradio as gr


class HelpPage:
    def __init__(self, app):
        self._app = app
        self.dir_md = Path(__file__).parent.parent / "assets" / "md"

        with gr.Accordion("Changelogs"):
            gr.Markdown(self.get_changelogs())

        with gr.Accordion("About Kotaemon (temporary)"):
            with (self.dir_md / "about_kotaemon.md").open() as fi:
                gr.Markdown(fi.read())

        with gr.Accordion("About Cinnamon AI (temporary)", open=False):
            with (self.dir_md / "about_cinnamon.md").open() as fi:
                gr.Markdown(fi.read())

    def get_changelogs(self):
        with (self.dir_md / "changelogs.md").open() as fi:
            return fi.read()
