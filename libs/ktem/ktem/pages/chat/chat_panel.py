import gradio as gr
from ktem.app import BasePage

from theflow.settings import settings as flowsettings


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        self.chatbot = gr.Chatbot(
            label=self._app.app_name,
            placeholder=(
                getattr(
                    flowsettings, 
                    "KH_CHAT_CUSTOM_PLACEHOLDER", 
                    "This is the beginning of a new conversation.\nIf you are new, "
                    "visit the Help tab for quick instructions.",
                )
            ),
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
                placeholder=(
                    "Type a message, search the @web, or tag a file with @filename"
                ),
                container=False,
                show_label=False,
                elem_id="chat-input",
            )

    def submit_msg(self, chat_input, chat_history):
        """Submit a message to the chatbot"""
        return "", chat_history + [(chat_input, None)]
