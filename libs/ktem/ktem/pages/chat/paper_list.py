import gradio as gr
from ktem.app import BasePage
from pandas import DataFrame

from ...utils.hf_papers import fetch_papers


class PaperListPage(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(
            label="Browse daily top papers",
            open=False,
        ) as self.accordion:
            self.papers = fetch_papers(top_n=5)
            self.examples = gr.DataFrame(
                value=DataFrame(self.papers),
                headers=["title", "url", "upvotes"],
                column_widths=[60, 30, 10],
                interactive=False,
                elem_id="paper-suggestion",
                wrap=True,
            )
        return self.examples

    def select_example(self, ev: gr.SelectData):
        print("Selected index", ev.index[0])
        return self.papers[ev.index[0]]["url"]
