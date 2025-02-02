import gradio as gr
from ktem.app import BasePage
from pandas import DataFrame

from ...utils.hf_papers import fetch_papers


class PaperListPage(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        self.papers_state = gr.State(None)
        with gr.Accordion(
            label="Browse popular daily papers",
            open=True,
        ) as self.accordion:
            self.examples = gr.DataFrame(
                value=[],
                headers=["title", "url", "upvotes"],
                column_widths=[60, 30, 10],
                interactive=False,
                elem_id="paper-suggestion",
                wrap=True,
            )
        return self.examples

    def load(self):
        papers = fetch_papers(top_n=5)
        papers_df = DataFrame(papers)
        return (papers_df, papers)

    def _on_app_created(self):
        self._app.app.load(
            self.load,
            outputs=[self.examples, self.papers_state],
        )

    def select_example(self, state, ev: gr.SelectData):
        return state[ev.index[0]]["url"]
