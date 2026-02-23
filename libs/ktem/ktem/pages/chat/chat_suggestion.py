import gradio as gr
from ktem.app import BasePage
from theflow.settings import settings as flowsettings

from ...utils.lang import get_ui_text
from ..settings import get_current_language


class ChatSuggestion(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def _get_chat_samples(self, lang_code: str) -> list:
        """Get translated chat samples for the given language."""
        custom_samples = getattr(
            flowsettings,
            "KH_FEATURE_CHAT_SUGGESTION_SAMPLES",
            None,
        )
        if custom_samples:
            return custom_samples

        return [
            get_ui_text("chat_suggestion.summary_document", lang_code),
            get_ui_text("chat_suggestion.generate_faq", lang_code),
            get_ui_text("chat_suggestion.identify_highlights", lang_code),
        ]

    def on_building_ui(self):
        _lang = get_current_language()
        chat_samples = self._get_chat_samples(_lang)
        self.chat_samples = [[each] for each in chat_samples]
        with gr.Accordion(
            label=get_ui_text("chat_suggestion.chat_suggestion", _lang),
            visible=getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION", False),
        ) as self.accordion:
            self.default_example = gr.State(
                value=self.chat_samples,
            )
            self.examples = gr.DataFrame(
                value=self.chat_samples,
                headers=[get_ui_text("chat_suggestion.next_question", _lang)],
                interactive=False,
                elem_id="chat-suggestion",
                wrap=True,
            )

    def as_gradio_component(self):
        return self.examples

    def select_example(self, ev: gr.SelectData):
        return {"text": ev.value}
