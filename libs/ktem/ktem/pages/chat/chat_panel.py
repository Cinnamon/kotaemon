import gradio as gr
from ktem.app import BasePage


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        self.chatbot = gr.Chatbot(
            elem_id="main-chat-bot",
            show_copy_button=True,
            likeable=True,
            show_label=False,
        )
        with gr.Row():
            self.text_input = gr.Text(
                placeholder="Chat input", scale=15, container=False
            )
            self.submit_btn = gr.Button(value="Send", scale=1, min_width=10)
