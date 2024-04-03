import gradio as gr
from ktem.app import BasePage
from theflow.settings import settings as flowsettings


class ChatSuggestion(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        chat_samples = getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION_SAMPLES", [])
        chat_samples = [[each] for each in chat_samples]
        with gr.Accordion(label="Chat Suggestion", open=False) as self.accordion:
            self.example = gr.DataFrame(
                value=chat_samples,
                headers=["Sample"],
                interactive=False,
                wrap=True,
            )

    def as_gradio_component(self):
        return self.example

    def select_example(self, ev: gr.SelectData):
        return ev.value
