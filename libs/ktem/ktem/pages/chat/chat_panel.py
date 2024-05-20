import gradio as gr
from ktem.app import BasePage


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        self.chatbot = gr.Chatbot(
            label=self._app.app_name,
            placeholder=(
                "This is the beginning of a new conversation.\nMake sure to have added"
                " a LLM by following the instructions in the Help tab."
            ),
            show_label=False,
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
                max_lines=10,
            )
            self.submit_btn = gr.Button(
                value="Send",
                scale=1,
                min_width=10,
                variant="primary",
                elem_classes=["cap-button-height"],
            )
            self.regen_btn = gr.Button(
                value="Regen",
                scale=1,
                min_width=10,
                elem_classes=["cap-button-height"],
            )

    def submit_msg(self, chat_input, chat_history):
        """Submit a message to the chatbot"""
        return "", chat_history + [(chat_input, None)]
