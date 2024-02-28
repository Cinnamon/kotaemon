import gradio as gr
from ktem.app import BasePage

from .chat_panel import ChatPanel
from .control import ConversationControl
from .data_source import DataSource
from .events import (
    chat_fn,
    index_fn,
    is_liked,
    load_files,
    regen_fn,
    update_data_source,
)
from .report import ReportIssue
from .upload import FileUpload


class ChatPage(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Row():
            with gr.Column(scale=1):
                self.chat_control = ConversationControl(self._app)
                self.data_source = DataSource(self._app)
                self.file_upload = FileUpload(self._app)
                self.report_issue = ReportIssue(self._app)
            with gr.Column(scale=6):
                self.chat_panel = ChatPanel(self._app)
            with gr.Column(scale=3):
                with gr.Accordion(label="Information panel", open=True):
                    self.info_panel = gr.Markdown(elem_id="chat-info-panel")

    def on_register_events(self):
        self.chat_panel.submit_btn.click(
            self.chat_panel.submit_msg,
            inputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            outputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            show_progress="hidden",
        ).then(
            fn=chat_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self.data_source.files,
                self._app.settings_state,
            ],
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.info_panel,
            ],
            show_progress="minimal",
        ).then(
            fn=update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.data_source.files,
                self.chat_panel.chatbot,
            ],
            outputs=None,
        )

        self.chat_panel.text_input.submit(
            self.chat_panel.submit_msg,
            inputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            outputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            show_progress="hidden",
        ).then(
            fn=chat_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self.data_source.files,
                self._app.settings_state,
            ],
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.info_panel,
            ],
            show_progress="minimal",
        ).then(
            fn=update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.data_source.files,
                self.chat_panel.chatbot,
            ],
            outputs=None,
        )

        self.chat_panel.regen_btn.click(
            fn=regen_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self.data_source.files,
                self._app.settings_state,
            ],
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.info_panel,
            ],
            show_progress="minimal",
        ).then(
            fn=update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.data_source.files,
                self.chat_panel.chatbot,
            ],
            outputs=None,
        )

        self.chat_panel.chatbot.like(
            fn=is_liked,
            inputs=[self.chat_control.conversation_id],
            outputs=None,
        )

        self.chat_control.conversation.change(
            self.chat_control.select_conv,
            inputs=[self.chat_control.conversation],
            outputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
                self.data_source.files,
                self.chat_panel.chatbot,
            ],
            show_progress="hidden",
        )

        self.report_issue.report_btn.click(
            self.report_issue.report,
            inputs=[
                self.report_issue.correctness,
                self.report_issue.issues,
                self.report_issue.more_detail,
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self.data_source.files,
                self._app.settings_state,
                self._app.user_id,
            ],
            outputs=None,
        )

        self.data_source.files.input(
            fn=update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.data_source.files,
                self.chat_panel.chatbot,
            ],
            outputs=None,
        )

        self.file_upload.upload_button.click(
            fn=index_fn,
            inputs=[
                self.file_upload.files,
                self.file_upload.reindex,
                self.data_source.files,
                self._app.settings_state,
            ],
            outputs=[self.file_upload.file_output, self.data_source.files],
        )

        self._app.app.load(
            lambda: gr.update(choices=load_files()),
            inputs=None,
            outputs=[self.data_source.files],
        )
