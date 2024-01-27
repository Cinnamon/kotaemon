import gradio as gr
from ktem.app import BasePage


class FileUpload(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="File upload", open=False):
            gr.Markdown(
                "Supported file types: image, pdf, txt, csv, xlsx, docx, doc, pptx.",
            )
            self.files = gr.File(
                file_types=[
                    "image",
                    ".pdf",
                    ".txt",
                    ".csv",
                    ".xlsx",
                    ".doc",
                    ".docx",
                    ".pptx",
                ],
                file_count="multiple",
                container=False,
                height=50,
            )
            with gr.Accordion("Advanced indexing options", open=False):
                with gr.Row():
                    with gr.Column():
                        self.reindex = gr.Checkbox(
                            value=False, label="Force reindex file", container=False
                        )
                    with gr.Column():
                        self.parser = gr.Dropdown(
                            choices=[
                                ("PDF text parser", "normal"),
                                ("lib-table", "table"),
                                ("lib-table + OCR", "ocr"),
                                ("MathPix", "mathpix"),
                            ],
                            value="normal",
                            label="Use advance PDF parser (table+layout preserving)",
                            container=True,
                        )

            self.upload_button = gr.Button("Upload and Index")
            self.file_output = gr.File(
                visible=False, label="Output files (debug purpose)"
            )
