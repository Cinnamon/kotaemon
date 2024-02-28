import gradio as gr
from ktem.app import BasePage


class FileUpload(BasePage):
    def __init__(self, app):
        self._app = app
        self._supported_file_types = [
            "image",
            ".pdf",
            ".txt",
            ".csv",
            ".xlsx",
            ".doc",
            ".docx",
            ".pptx",
            ".html",
            ".zip",
        ]
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="File upload", open=False):
            gr.Markdown(
                f"Supported file types: {', '.join(self._supported_file_types)}",
            )
            self.files = gr.File(
                file_types=self._supported_file_types,
                file_count="multiple",
                container=False,
                height=50,
            )
            with gr.Accordion("Advanced indexing options", open=False):
                with gr.Row():
                    self.reindex = gr.Checkbox(
                        value=False, label="Force reindex file", container=False
                    )

            self.upload_button = gr.Button("Upload and Index")
            self.file_output = gr.File(
                visible=False, label="Output files (debug purpose)"
            )


class DirectoryUpload(BasePage):
    def __init__(self, app):
        self._app = app
        self._supported_file_types = [
            "image",
            ".pdf",
            ".txt",
            ".csv",
            ".xlsx",
            ".doc",
            ".docx",
            ".pptx",
            ".html",
            ".zip",
        ]
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Directory upload", open=False):
            gr.Markdown(
                f"Supported file types: {', '.join(self._supported_file_types)}",
            )
            self.path = gr.Textbox(
                placeholder="Directory path...", lines=1, max_lines=1, container=False
            )
            with gr.Accordion("Advanced indexing options", open=False):
                with gr.Row():
                    self.reindex = gr.Checkbox(
                        value=False, label="Force reindex file", container=False
                    )

            self.upload_button = gr.Button("Upload and Index")
            self.file_output = gr.File(
                visible=False, label="Output files (debug purpose)"
            )
