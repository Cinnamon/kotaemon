import gradio as gr
from ktem.app import BasePage


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        self.chatbot = gr.Chatbot(
            label="Kotaemon",
            # placeholder="This is the beginning of a new conversation.",
            show_label=True,
            elem_id="main-chat-bot",
            show_copy_button=True,
            likeable=True,
            bubble_full_width=False,
        )
        with gr.Row():
            self.text_input = gr.Text(
                placeholder="Chat input",
                scale=15,
                container=False,
            )
            self.submit_btn = gr.Button(
                value="Send",
                scale=1,
                min_width=10,
                variant="primary",
                elem_classes=["cap-height"],
            )
            self.regen_btn = gr.Button(
                value="Regen",
                scale=1,
                min_width=10,
                elem_classes=["cap-height"],
            )

    def submit_msg(self, chat_input, chat_history):
        """Submit a message to the chatbot"""
        return "", chat_history + [(chat_input, None)]
