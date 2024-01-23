import gradio as gr
from ktem.app import BasePage


class DataSource(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Data source", open=True):
            self.files = gr.Dropdown(
                label="Files",
                choices=[],
                multiselect=True,
                container=False,
                interactive=True,
            )
