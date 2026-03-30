import gradio as gr
from ktem.app import BasePage
from theflow.settings import settings as flowsettings

from ...utils.lang import get_ui_text
from ..settings import get_current_language

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def _get_placeholder_text(self, lang_code: str) -> str:
        if not KH_DEMO_MODE:
            return get_ui_text("chat.beginning_conversation", lang_code)
        else:
            return (
                "Welcome to Kotaemon Demo. "
                "Start by browsing preloaded conversations to get onboard.\n"
                "Check out Hint section for more tips."
            )

    def on_building_ui(self):
        _lang = get_current_language()
        self.chatbot = gr.Chatbot(
            label=self._app.app_name,
            placeholder=self._get_placeholder_text(_lang),
            show_label=False,
            elem_id="main-chat-bot",
            show_copy_button=True,
            likeable=True,
            bubble_full_width=False,
        )
        with gr.Row():
            self.text_input = gr.MultimodalTextbox(
                interactive=True,
                scale=20,
                file_count="multiple",
                placeholder=get_ui_text("chat.type_message", _lang),
                container=False,
                show_label=False,
                elem_id="chat-input",
            )

    def submit_msg(self, chat_input, chat_history):
        """Submit a message to the chatbot"""
        return "", chat_history + [(chat_input, None)]
