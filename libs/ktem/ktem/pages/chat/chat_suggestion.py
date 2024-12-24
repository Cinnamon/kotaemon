import gradio as gr
from ktem.app import BasePage
from theflow.settings import settings as flowsettings


class ChatSuggestion(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        chat_samples = getattr(
            flowsettings,
            "KH_FEATURE_CHAT_SUGGESTION_SAMPLES",
            [
                "Summary this document",
                "Generate a FAQ for this document",
                "Identify the main highlights in this text",
            ],
        )
        self.chat_samples = [[each] for each in chat_samples]
        with gr.Accordion(
            label="Chat Suggestion",
            visible=getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION", False),
        ) as self.accordion:
            self.examples = gr.DataFrame(
                value=self.chat_samples,
                headers=["Next Question"],
                interactive=False,
                elem_id="chat-suggestion",
                wrap=True,
            )

    def as_gradio_component(self):
        return self.examples

    def select_example(self, ev: gr.SelectData):
        return {"text": ev.value}
