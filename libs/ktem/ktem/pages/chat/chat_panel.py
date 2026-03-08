import gradio as gr
from ktem.app import BasePage
from theflow.settings import settings as flowsettings

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)

if not KH_DEMO_MODE:
    PLACEHOLDER_TEXT = (
        "This is the beginning of a new conversation.\n"
        "Start by uploading a file or a web URL. "
        "Visit Files tab for more options (e.g: GraphRAG)."
    )
else:
    PLACEHOLDER_TEXT = (
        "Welcome to Kotaemon Demo. "
        "Start by browsing preloaded conversations to get onboard.\n"
        "Check out Hint section for more tips."
    )


class ChatPanel(BasePage):
    def __init__(self, app):
        self._app = app
        self.text_input = None
        self.on_building_ui()

    def on_building_ui(self):
        self.chatbot = gr.Chatbot(
            label=self._app.app_name,
            placeholder=PLACEHOLDER_TEXT,
            show_label=False,
            elem_id="main-chat-bot",
            show_copy_button=True,
            likeable=True,
            bubble_full_width=False,
            visible=False,
            latex_delimiters=[
                {"left": "$$", "right": "$$", "display": True},
                {"left": "$", "right": "$", "display": False},
                {"left": "\\(", "right": "\\)", "display": False},
                {"left": "\\[", "right": "\\]", "display": True},
            ],
        )

        self.pdf_preview = gr.HTML(
            value=(
                "<div class='pdf-preview-shell'>"
                "<iframe id='main-pdf-preview-frame' title='PDF Preview' loading='lazy'></iframe>"
                "<img id='main-pdf-preview-image' class='pdf-preview-image' alt='PDF page preview' />"
                "<div id='main-pdf-preview-empty' class='pdf-preview-empty'>Select a PDF file to preview.</div>"
                "</div>"
            ),
            elem_id="main-pdf-preview",
        )
        self.pdf_preview_src = gr.Textbox(value="", visible=False, elem_id="main-pdf-preview-src")
        self.preview_refresh_timer = gr.Timer(value=1.5, active=True)

    def render_notice_and_pager(self):
        self.pdf_preview_notice = gr.HTML(
            value="<div class='pdf-preview-notice'>Select a PDF file to preview.</div>",
            elem_id="pdf-preview-notice",
        )

        with gr.Row(equal_height=True, elem_id="pdf-pager-row"):
            self.prev_page_btn = gr.Button("◀ Prev", scale=1, min_width=80)
            self.page_number = gr.Number(
                value=1,
                precision=0,
                minimum=1,
                scale=1,
                min_width=100,
                container=False,
                show_label=False,
                elem_id="pdf-page-number",
            )
            self.next_page_btn = gr.Button("Next ▶", scale=1, min_width=80)

    def render_input(self):
        with gr.Row(elem_id="chat-input-row"):
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
