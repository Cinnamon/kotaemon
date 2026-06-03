from textwrap import dedent

import gradio as gr
from ktem.app import BasePage


class HintPage(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Hint", open=False):
            gr.Markdown(
                dedent(
                    """
                - You can select any text from the chat answer to **highlight relevant citation(s)** on the right panel.
                - **Citations** can be viewed on both PDF viewer and raw text.
                - You can tweak the citation format and use advance (CoT) reasoning in **Chat settings** menu.
                - Want to **explore more**? Check out the **Help** section to create your private space.
            """  # noqa
                )
            )
