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
            self.regen_btn = gr.Button(value="Regen", scale=1, min_width=10)

    def submit_msg(self, chat_input, chat_history):
        """Submit a message to the chatbot"""
        return "", chat_history + [(chat_input, None)]

    def activate_rewrite(self, setting_state):
        setting_state["reasoning.options.simple.rewrite_question"] = True
        return setting_state
