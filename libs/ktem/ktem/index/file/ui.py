import html
import json
import os
import shutil
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Generator
import datetime

import gradio as gr
import pandas as pd
from gradio.data_classes import FileData
from gradio.utils import NamedString
from ktem.app import BasePage
from ktem.db.engine import engine
from ktem.utils.render import Render
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings

from ...utils.commands import WEB_SEARCH_COMMAND
from ...utils.rate_limit import check_rate_limit
from .utils import download_arxiv_pdf, is_arxiv_url

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_SSO_ENABLED = getattr(flowsettings, "KH_SSO_ENABLED", False)
DOWNLOAD_MESSAGE = "Start download"
MAX_FILENAME_LENGTH = 20
MAX_FILE_COUNT = 200

ASSETS_DIR = "assets/icons"
if not os.path.isdir(ASSETS_DIR):
    ASSETS_DIR = "libs/ktem/ktem/assets/icons"


chat_input_focus_js = """
function() {
    let chatInput = document.querySelector("#chat-input textarea");
    chatInput.focus();
}
"""

chat_input_focus_js_with_submit = """
function() {
    let chatInput = document.querySelector("#chat-input textarea");
    let chatInputSubmit = document.querySelector("#chat-input button.submit-button");
    chatInputSubmit.click();
    chatInput.focus();
}
"""

update_file_list_js = """
function(file_list) {
    var values = [];
    for (var i = 0; i < file_list.length; i++) {
        values.push({
            key: file_list[i][0],
            value: '"' + file_list[i][0] + '"',
        });
    }

    // manually push web search tag
    values.push({
        key: "web_search",
        value: '"web_search"',
    });

    var tribute = new Tribute({
        values: values,
        noMatchTemplate: "",
        allowSpaces: true,
    })
    input_box = document.querySelector('#chat-input textarea');
    tribute.detach(input_box);
    tribute.attach(input_box);
}
""".replace(
    "web_search", WEB_SEARCH_COMMAND
)

class File(gr.File):
    """Subclass from gr.File to maintain the original filename

    The issue happens when user uploads file with name like: !@#$%%^&*().pdf
    """

    def _process_single_file(self, f: FileData) -> NamedString | bytes:
        file_name = f.path
        if self.type == "filepath":
            if f.orig_name and Path(file_name).name != f.orig_name:
                file_name = str(Path(file_name).parent / f.orig_name)
                os.rename(f.path, file_name)
            file = tempfile.NamedTemporaryFile(delete=False, dir=self.GRADIO_CACHE)
            file.name = file_name
            return NamedString(file_name)
        elif self.type == "binary":
            with open(file_name, "rb") as file_data:
                return file_data.read()
        else:
            raise ValueError(
                "Unknown type: "
                + str(type)
                + ". Please choose from: 'filepath', 'binary'."
            )


class DirectoryUpload(BasePage):
    def __init__(self, app, index):
        super().__init__(app)
        self._index = index
        self._supported_file_types_str = self._index.config.get(
            "supported_file_types", ""
        )
        self._supported_file_types = [
            each.strip() for each in self._supported_file_types_str.split(",")
        ]
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Directory upload", open=False):
            gr.Markdown(f"Supported file types: {self._supported_file_types_str}")
            self.path = gr.Textbox(
                placeholder="Directory path...", lines=1, max_lines=1, container=False
            )
            with gr.Accordion("Advanced indexing options", open=False):
                with gr.Row():
                    self.reindex = gr.Checkbox(
                        value=False, label="Force reindex file", container=False
                    )

            self.upload_button = gr.Button("Upload and Index")


class FileIndexPage(BasePage):
    def __init__(self, app, index):
        super().__init__(app)
        self._index = index
        self._supported_file_types_str = self._index.config.get(
            "supported_file_types", ""
        )
        self._supported_file_types = [
            each.strip() for each in self._supported_file_types_str.split(",")
        ]
        self.selected_panel_false = "Selected file: (please select above)"
        self.selected_panel_true = "Selected file: {name}"
        # TODO: on_building_ui is not correctly named if it's always called in
        # the constructor
        self.public_events = [f"onFileIndex{index.id}Changed"]

        if not KH_DEMO_MODE:
            self.on_building_ui()
        
    # new dataframe filter
    def filter_file_list(self, file_list_state, name, company, date_start, date_end):
        import pandas as pd

        if file_list_state is None or not isinstance(file_list_state, list):
            return gr.update()
        df = pd.DataFrame(file_list_state)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if name:
            df = df[df['name'].str.contains(name, case=False, na=False)]
        if company:
            df = df[df['company'].str.contains(company, case=False, na=False)]
        if date_start:
            date_start_dt = pd.to_datetime(date_start, errors='coerce')
            df = df[df['date'] >= date_start_dt]
        if date_end:
            date_end_dt = pd.to_datetime(date_end, errors='coerce')
            df = df[df['date'] <= date_end_dt]
            
        if 'id' in df.columns:
            df = df.drop(columns=['id'])

        if 'date' in df.columns:
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')            
        
        return gr.update(value=df)
        
    # Event clear filter: kosongkan filter dan refresh file list
    def clear_filters_and_refresh(self, file_list_state):
        # Kosongkan semua filter dan refresh
        print("Clearing filters...")  # Debug
        return self.filter_file_list(file_list_state, "", "", "", ""), "", "", "", ""

    def upload_instruction(self) -> str:
        msgs = []
        if self._supported_file_types:
            msgs.append(f"- Supported file types: {self._supported_file_types_str}")

        if max_file_size := self._index.config.get("max_file_size", 0):
            msgs.append(f"- Maximum file size: {max_file_size} MB")

        if max_number_of_files := self._index.config.get("max_number_of_files", 0):
            msgs.append(f"- The index can have maximum {max_number_of_files} files")

        if msgs:
            return "\n".join(msgs)

        return ""
    
    #new filter
    
    def render_file_list(self):
        gr.Markdown("## List Files")
        
        # Initialize state and DataFrame before using in events
        self.file_list_state = gr.State(value=None)

        with gr.Row(elem_classes=["docu-panel-primary"]):
            self.name_filter = gr.Textbox(
                value="",
                placeholder="File Name",
                show_label=False,
                scale=9,
                info="file name",
                interactive=True
            )
            self.company_filter = gr.Textbox(
                value="",
                placeholder="Company",
                scale=9,
                show_label=False,
                info="company",
                interactive=True
            )
            self.date_start_filter = gr.DateTime(
                include_time=False,
                type="datetime",
                show_label=False,
                info="start date",
                scale=10,
                elem_classes="datepick-file",
            )
            self.date_end_filter = gr.DateTime(
                include_time=False,
                type="datetime",
                show_label=False,
                info="end date",
                scale=10,
                elem_classes="datepick-file",
            )
            self.btn_sch = gr.Button(
                value="",
                icon=f"{ASSETS_DIR}/docu-search.svg",
                min_width=2,
                scale=1,
                size="sm",
                elem_classes=["no-background", "body-text-color", "no-shadow-button-icon", "filter-action-button"],
            )
            self.btn_clr = gr.Button(
                value="",
                icon=f"{ASSETS_DIR}/filter-off.svg",
                min_width=2,
                scale=1,
                size="sm",
                elem_classes=["no-background", "body-text-color", "no-shadow-button-icon", "filter-action-button"],
            )

            self.pdf_modal = gr.HTML(
                visible=False,
                elem_id="pdf-modal-container"
            )
            
            # Hidden button to close modal (triggered by JavaScript)
            self.close_modal_button = gr.Button(
                "Close Modal",
                visible=False,
                elem_id="close-modal-button"
            )
    
        self.file_list = gr.DataFrame(
            headers=[
                "name",
                "company",
                "size",
                "date",
            ],
            column_widths=["20%", "30%", "7%", "7%"],
            interactive=False,
            wrap=True,
            elem_id="file_list_view",
        )       
       
        with gr.Row(visible=False):
            self.filter = gr.Textbox(
                value="",
                placeholder="Name",
                show_label=False,
                scale=0,
            )
            # Event filter search
            self.btn_sch.click(
                fn=self.filter_file_list,
                inputs=[self.file_list_state, self.name_filter, self.company_filter, self.date_start_filter, self.date_end_filter],
                outputs=[self.file_list],
                show_progress="hidden"
            )

            self.btn_clr.click(
                fn=self.clear_filters_and_refresh,
                inputs=[self.file_list_state],
                outputs=[
                    self.file_list,
                    self.name_filter, self.company_filter, self.date_start_filter, self.date_end_filter
                ],
            )
 
       # new file action
        with gr.Row():
            with gr.Column():
                pass 
            with gr.Column(): 
                with gr.Row():
                    self.show_selected_button = gr.DownloadButton(
                        "Show",
                        variant="primary",
                        interactive=False,
                        visible=True,
                    )
                    self.delete_selected_button = gr.Button(
                        "Delete",
                        variant="stop",
                        interactive=False,
                        visible=True,
                    )
        #end //hamam

        with gr.Row():
            self.chat_button = gr.Button(
                "Go to Chat",
                visible=False,
            )
            self.is_zipped_state = gr.State(value=False)
            self.download_single_button = gr.DownloadButton(
                "Download",
                visible=False,
            )
            self.delete_button = gr.Button(
                "Delete",
                variant="stop",
                visible=False,
            )
            self.deselect_button = gr.Button(
                "Close",
                visible=False,
            )

        with gr.Row(visible=False) as self.selection_info:
            self.selected_file_id = gr.State(value=None)
            with gr.Column(scale=2):
                self.selected_panel = gr.Markdown(self.selected_panel_false)

        self.chunks = gr.HTML(visible=False)

        with gr.Accordion("Advance options", open=False, visible=False):
            with gr.Row(visible=False):
                if not KH_SSO_ENABLED:
                    self.download_all_button = gr.DownloadButton(
                        "Download all files",
                    )
                self.delete_all_button = gr.Button(
                    "Delete all files",
                    variant="stop",
                    visible=False,
                )
                self.delete_all_button_confirm = gr.Button(
                    "Confirm delete", variant="stop", visible=False
                )
                self.delete_all_button_cancel = gr.Button("Cancel", visible=False)

    def render_group_list(self):
        self.group_list_state = gr.State(value=None)
        self.group_list = gr.DataFrame(
            headers=[
                "name",
                "company",
                "size",
                "date",
            ],
            column_widths=["20%", "30%", "7%", "7%"],
            interactive=False,
            wrap=True,
        )

        with gr.Row():
            self.group_add_button = gr.Button(
                "Add",
                variant="primary",
            )
            self.group_chat_button = gr.Button(
                "Go to Chat",
                visible=False,
            )
            self.group_delete_button = gr.Button(
                "Delete",
                variant="stop",
                visible=False,
            )
            self.group_close_button = gr.Button(
                "Close",
                visible=False,
            )

        with gr.Column(visible=False) as self._group_info_panel:
            self.selected_group_id = gr.State(value=None)
            self.group_label = gr.Markdown()
            self.group_name = gr.Textbox(
                label="Group name",
                placeholder="Group name",
                lines=1,
                max_lines=1,
            )
            self.group_files = gr.Dropdown(
                label="Attached files",
                multiselect=True,
            )
            self.group_save_button = gr.Button(
                "Save",
                variant="primary",
            )

    def show_pdf_modal(self, file_id):
        if not file_id:
            return gr.update(visible=False)
        
        Source = self._index._resources["Source"]
        with Session(engine) as session:
            file = session.query(Source).filter(Source.id == file_id).first()
            
            if not file or not file.path:
                return gr.update(visible=False)
            
            BASE_PATH = os.environ.get("GR_FILE_ROOT_PATH", "")
            pdf_url = f"{BASE_PATH}/file={file.path}"
            
            # Buat modal HTML dengan iframe untuk PDF dan JavaScript yang lebih sederhana
            modal_html = f"""
            <div id="pdf-modal-file" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 9999;
            " onclick="
                document.getElementById('pdf-modal-file').style.display='none';
                document.getElementById('close-modal-button').click();
            ">
                <div style="
                    position: relative;
                    width: 80%;
                    height: 100%;
                    background: white;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                    display: flex;
                    flex-direction: column;
                " onclick="event.stopPropagation()">
                    <div style="
                        padding: 4px 12px;
                        background: #fff;
                        border-bottom: 1px solid #ddd;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <span style="font-weight: 500; font-size: 1.1em; color: #333;">{file.name}</span>
                        <button onclick="
                            document.getElementById('pdf-modal-file').style.display='none';
                            document.getElementById('close-modal-button').click();
                        " style="
                            background: none;
                            border: none;
                            font-size: 1.5em;
                            cursor: pointer;
                            color: #333;
                            padding: 5px 10px;
                            font-weight: bold;
                        ">×</button>
                    </div>
                    <iframe 
                        src="{pdf_url}" 
                        style="
                            flex-grow: 1;
                            border: none;
                            border-radius: 0 0 8px 8px;
                        " 
                        frameborder="0">
                    </iframe>
                </div>
            </div>
            """
            
            return gr.update(value=modal_html, visible=True)
        
    def close_pdf_modal(self):
        """Close the PDF modal by returning empty HTML"""
        return gr.update(value="", visible=False)

    def on_building_ui(self):
        """Build the UI of the app"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## File Upload")
                with gr.Column() as self.upload:
                    with gr.Column("Upload Files"):
                        self.files = File(
                            file_types=self._supported_file_types,
                            file_count="multiple",
                            container=False,
                            show_label=False,
                        )

                        msg = self.upload_instruction()
                        if msg:
                            gr.Markdown(msg)

                    with gr.Column("Use Web Links", visible=False):
                        self.urls = gr.Textbox(
                            label="Input web URLs",
                            lines=8,
                        )
                        gr.Markdown("(separated by new line)")

                    with gr.Accordion("Advanced indexing options", visible=False, open=False):
                        with gr.Row():
                            self.reindex = gr.Checkbox(
                                value=False, label="Force reindex file", container=False
                            )

                    self.upload_button = gr.Button(
                        "Upload and Index", variant="primary"
                    )

            with gr.Column(scale=4):
                with gr.Column(visible=False) as self.upload_progress_panel:
                    gr.Markdown("## Upload Progress")
                    with gr.Row():
                        self.upload_result = gr.Textbox(
                            lines=1, max_lines=20, label="Upload result"
                        )
                        self.upload_info = gr.Textbox(
                            lines=1, max_lines=20, label="Upload info"
                        )
                    self.btn_close_upload_progress_panel = gr.Button(
                        "Clear Upload Info and Close",
                        variant="secondary",
                        elem_classes=["right-button"],
                    )

                with gr.Column("Files"):
                    self.render_file_list()

                with gr.Tab("Groups", visible=False):
                    self.render_group_list()

    def on_subscribe_public_events(self):
        """Subscribe to the declared public event of the app"""
        if KH_DEMO_MODE:
            return

        self._app.subscribe_event(
            name=f"onFileIndex{self._index.id}Changed",
            definition={
                "fn": self.list_file_names,
                "inputs": [self.file_list_state],
                "outputs": [self.group_files],
                "show_progress": "hidden",
            },
        )

        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.list_file,
                    "inputs": [self._app.user_id],
                    "outputs": [self.file_list_state, self.file_list],
                    "show_progress": "hidden",
                },
            )
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.list_group,
                    "inputs": [self._app.user_id, self.file_list_state],
                    "outputs": [self.group_list_state, self.group_list],
                    "show_progress": "hidden",
                },
            )
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.list_file_names,
                    "inputs": [self.file_list_state],
                    "outputs": [self.group_files],
                    "show_progress": "hidden",
                },
            )
            self._app.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": self.list_file,
                    "inputs": [self._app.user_id],
                    "outputs": [self.file_list_state, self.file_list],
                    "show_progress": "hidden",
                },
            )

    def file_selected(self, file_id):
        chunks = []
        # if file_id is not None:
            # get the chunks

            # Index = self._index._resources["Index"]
            # with Session(engine) as session:
            #     matches = session.execute(
            #         select(Index).where(
            #             Index.source_id == file_id,
            #             Index.relation_type == "document",
            #         )
            #     )
            #     doc_ids = [doc.target_id for (doc,) in matches]
            #     docs = self._index._docstore.get(doc_ids)
            #     docs = sorted(
            #         docs, key=lambda x: x.metadata.get("page_label", float("inf"))
            #     )

            #     for idx, doc in enumerate(docs):
            #         title = html.escape(
            #             f"{doc.text[:50]}..." if len(doc.text) > 50 else doc.text
            #         )
            #         doc_type = doc.metadata.get("type", "text")
            #         content = ""
            #         if doc_type == "text":
            #             content = html.escape(doc.text)
            #         elif doc_type == "table":
            #             content = Render.table(doc.text)
            #         elif doc_type == "image":
            #             content = Render.image(
            #                 url=doc.metadata.get("image_origin", ""), text=doc.text
            #             )

            #         header_prefix = f"[{idx+1}/{len(docs)}]"
            #         if doc.metadata.get("page_label"):
            #             header_prefix += f" [Page {doc.metadata['page_label']}]"

            #         chunks.append(
            #             Render.collapsible(
            #                 header=f"{header_prefix} {title}",
            #                 content=content,
            #             )
            #         )
        return (
            gr.update(value="".join(chunks), visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(interactive=file_id is not None),
            gr.update(interactive=file_id is not None),
        )

    def delete_event(self, file_id):
        import os
        file_name = ""
        with Session(engine) as session:
            source = session.execute(
                select(self._index._resources["Source"]).where(
                    self._index._resources["Source"].id == file_id
                )
            ).first()
            if source:
                file_name = source[0].name
                # Hapus file fisik jika ada
                # Coba cari di folder gradio_tmp dan folder chunks/markdown jika perlu
                try:
                    # Folder utama gradio_tmp
                    gradio_tmp_dir = getattr(flowsettings, "KH_GRADIO_TMP_DIR", None)
                    if gradio_tmp_dir:
                        file_path = os.path.join(gradio_tmp_dir, file_name)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    # Folder chunks
                    chunks_dir = getattr(flowsettings, "KH_CHUNKS_OUTPUT_DIR", None)
                    if chunks_dir:
                        for f in os.listdir(chunks_dir):
                            if file_name in f:
                                try:
                                    os.remove(os.path.join(chunks_dir, f))
                                except Exception:
                                    pass
                    # Folder markdown
                    markdown_dir = getattr(flowsettings, "KH_MARKDOWN_OUTPUT_DIR", None)
                    if markdown_dir:
                        for f in os.listdir(markdown_dir):
                            if file_name in f:
                                try:
                                    os.remove(os.path.join(markdown_dir, f))
                                except Exception:
                                    pass
                except Exception as e:
                    print(f"[WARNING] Failed to remove file: {e}")
                session.delete(source[0])

            vs_ids, ds_ids = [], []
            index = session.execute(
                select(self._index._resources["Index"]).where(
                    self._index._resources["Index"].source_id == file_id
                )
            ).all()
            for each in index:
                if each[0].relation_type == "vector":
                    vs_ids.append(each[0].target_id)
                elif each[0].relation_type == "document":
                    ds_ids.append(each[0].target_id)
                session.delete(each[0])
            session.commit()

        if vs_ids:
            self._index._vs.delete(vs_ids)
        self._index._docstore.delete(ds_ids)

        gr.Info(f"File {file_name} has been deleted")

        return None, self.selected_panel_false

    def delete_no_event(self):
        return (
            gr.update(visible=True),
            gr.update(visible=False),
        )

    def download_single_file(self, is_zipped_state, file_id):
        with Session(engine) as session:
            source = session.execute(
                select(self._index._resources["Source"]).where(
                    self._index._resources["Source"].id == file_id
                )
            ).first()
        if source:
            target_file_name = Path(source[0].name)
        zip_files = []
        for file_name in os.listdir(flowsettings.KH_CHUNKS_OUTPUT_DIR):
            if target_file_name.stem in file_name:
                zip_files.append(
                    os.path.join(flowsettings.KH_CHUNKS_OUTPUT_DIR, file_name)
                )
        for file_name in os.listdir(flowsettings.KH_MARKDOWN_OUTPUT_DIR):
            if target_file_name.stem in file_name:
                zip_files.append(
                    os.path.join(flowsettings.KH_MARKDOWN_OUTPUT_DIR, file_name)
                )
        zip_file_path = os.path.join(
            flowsettings.KH_ZIP_OUTPUT_DIR, target_file_name.stem
        )
        with zipfile.ZipFile(f"{zip_file_path}.zip", "w") as zipMe:
            for file in zip_files:
                zipMe.write(file, arcname=os.path.basename(file))

        if is_zipped_state:
            new_button = gr.DownloadButton(label="Download", value=None)
        else:
            new_button = gr.DownloadButton(
                label=DOWNLOAD_MESSAGE, value=f"{zip_file_path}.zip"
            )

        return not is_zipped_state, new_button

    def download_single_file_simple(self, is_zipped_state, file_html, file_id):
        with Session(engine) as session:
            source = session.execute(
                select(self._index._resources["Source"]).where(
                    self._index._resources["Source"].id == file_id
                )
            ).first()
        if source:
            target_file_name = Path(source[0].name)

        # create a temporary file with a path to export
        output_file_path = os.path.join(
            flowsettings.KH_ZIP_OUTPUT_DIR, target_file_name.stem + ".html"
        )
        with open(output_file_path, "w") as f:
            f.write(file_html)

        if is_zipped_state:
            new_button = gr.DownloadButton(label="Download", value=None)
        else:
            # export the file path
            new_button = gr.DownloadButton(
                label=DOWNLOAD_MESSAGE,
                value=output_file_path,
            )

        return not is_zipped_state, new_button

    def download_all_files(self):
        if self._index.config.get("private", False):
            raise gr.Error("This feature is not available for private collection.")

        zip_files = []
        for file_name in os.listdir(flowsettings.KH_CHUNKS_OUTPUT_DIR):
            zip_files.append(os.path.join(flowsettings.KH_CHUNKS_OUTPUT_DIR, file_name))
        for file_name in os.listdir(flowsettings.KH_MARKDOWN_OUTPUT_DIR):
            zip_files.append(
                os.path.join(flowsettings.KH_MARKDOWN_OUTPUT_DIR, file_name)
            )
        zip_file_path = os.path.join(flowsettings.KH_ZIP_OUTPUT_DIR, "all")
        with zipfile.ZipFile(f"{zip_file_path}.zip", "w") as zipMe:
            for file in zip_files:
                arcname = Path(file)
                zipMe.write(file, arcname=arcname.name)
        return gr.DownloadButton(label=DOWNLOAD_MESSAGE, value=f"{zip_file_path}.zip")

    def delete_all_files(self, file_list):
        for file_id in file_list.id.values:
            self.delete_event(file_id)

    def set_file_id_selector(self, selected_file_id):
        return [selected_file_id, "select", gr.Tabs(selected="chat-tab")]

    def show_delete_all_confirm(self, file_list):
        # when the list of files is empty it shows a single line with id equal to -
        if len(file_list) == 0 or (
            len(file_list) == 1 and file_list.id.values[0] == "-"
        ):
            gr.Info("No file to delete")
            return [
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ]
        else:
            return [
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=True),
            ]

    def on_register_quick_uploads(self):
        try:
            # quick file upload event registration of first Index only
            if self._index.id == 1:
                self.quick_upload_state = gr.State(value=[])
                print("Setting up quick upload event")

                # override indexing function from chat page
                self._app.chat_page.first_indexing_url_fn = (
                    self.index_fn_url_with_default_loaders
                )

                if not KH_DEMO_MODE:
                    quickUploadedEvent = (
                        self._app.chat_page.quick_file_upload.upload(
                            fn=lambda: gr.update(
                                value="Please wait for the indexing process "
                                "to complete before adding your question."
                            ),
                            outputs=self._app.chat_page.quick_file_upload_status,
                        )
                        .then(
                            fn=self.index_fn_file_with_default_loaders,
                            inputs=[
                                self._app.chat_page.quick_file_upload,
                                gr.State(value=False),
                                self._app.settings_state,
                                self._app.user_id,
                            ],
                            outputs=self.quick_upload_state,
                            concurrency_limit=10,
                        )
                        .success(
                            fn=lambda: [
                                gr.update(value=None),
                                gr.update(value="select"),
                            ],
                            outputs=[
                                self._app.chat_page.quick_file_upload,
                                self._app.chat_page._indices_input[0],
                            ],
                        )
                    )
                    for event in self._app.get_event(
                        f"onFileIndex{self._index.id}Changed"
                    ):
                        quickUploadedEvent = quickUploadedEvent.then(**event)

                    quickUploadedEvent = (
                        quickUploadedEvent.success(
                            fn=lambda x: x,
                            inputs=self.quick_upload_state,
                            outputs=self._app.chat_page._indices_input[1],
                        )
                        .then(
                            fn=lambda: gr.update(value="Indexing completed."),
                            outputs=self._app.chat_page.quick_file_upload_status,
                        )
                        .then(
                            fn=self.list_file,
                            inputs=[self._app.user_id, self.filter],
                            outputs=[self.file_list_state, self.file_list],
                            concurrency_limit=20,
                        )
                        .then(
                            fn=lambda: True,
                            inputs=None,
                            outputs=None,
                            js=chat_input_focus_js_with_submit,
                        )
                    )

                quickURLUploadedEvent = (
                    self._app.chat_page.quick_urls.submit(
                        fn=lambda: gr.update(
                            value="Please wait for the indexing process "
                            "to complete before adding your question."
                        ),
                        outputs=self._app.chat_page.quick_file_upload_status,
                    )
                    .then(
                        fn=self.index_fn_url_with_default_loaders,
                        inputs=[
                            self._app.chat_page.quick_urls,
                            gr.State(value=False),
                            self._app.settings_state,
                            self._app.user_id,
                        ],
                        outputs=self.quick_upload_state,
                        concurrency_limit=10,
                    )
                    .success(
                        fn=lambda: [
                            gr.update(value=None),
                            gr.update(value="select"),
                        ],
                        outputs=[
                            self._app.chat_page.quick_urls,
                            self._app.chat_page._indices_input[0],
                        ],
                    )
                )
                for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
                    quickURLUploadedEvent = quickURLUploadedEvent.then(**event)

                quickURLUploadedEvent = quickURLUploadedEvent.success(
                    fn=lambda x: x,
                    inputs=self.quick_upload_state,
                    outputs=self._app.chat_page._indices_input[1],
                ).then(
                    fn=lambda: gr.update(value="Indexing completed."),
                    outputs=self._app.chat_page.quick_file_upload_status,
                )

                if not KH_DEMO_MODE:
                    quickURLUploadedEvent = quickURLUploadedEvent.then(
                        fn=self.list_file,
                        inputs=[self._app.user_id, self.filter],
                        outputs=[self.file_list_state, self.file_list],
                        concurrency_limit=20,
                    )

                quickURLUploadedEvent = quickURLUploadedEvent.then(
                    fn=lambda: True,
                    inputs=None,
                    outputs=None,
                    js=chat_input_focus_js_with_submit,
                )

        except Exception as e:
            print(e)

    def on_register_events(self):
        """Register all events to the app"""
        self.on_register_quick_uploads()

        if KH_DEMO_MODE:
            return

        import pandas as pd
        onDeleted = (
            self.delete_button.click(
                fn=self.delete_event,
                inputs=[self.selected_file_id],
                outputs=None,
            )
            .then(
                fn=lambda: (None, self.selected_panel_false),
                inputs=[],
                outputs=[self.selected_file_id, self.selected_panel],
                show_progress="hidden",
            )
            .then(
                fn=self.list_file,
                inputs=[self._app.user_id, self.filter],
                outputs=[self.file_list_state, self.file_list],
            )
            .then(
                fn=lambda: [
                    gr.update(value=None),  # clear selection/focus on DataFrame
                    gr.update(value=""),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(selected=None),  # only clear selection, not value
                ],
                inputs=[],
                outputs=[
                    self.chunks,
                    self.selected_panel,
                    self.deselect_button,
                    self.delete_button,
                    self.download_single_button,
                    self.chat_button,
                    self.selected_file_id,
                    self.file_list,
                ],
                show_progress="hidden",
            )
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onDeleted = onDeleted.then(**event)
        
        # showing selected file
        self.show_selected_button.click(
            fn=self.show_pdf_modal,
            inputs=[self.selected_file_id],
            outputs=[self.pdf_modal],
            show_progress="hidden"
        )
        
        # close modal event
        self.close_modal_button.click(
            fn=self.close_pdf_modal,
            inputs=[],
            outputs=[self.pdf_modal],
            show_progress="hidden"
        )

        #deleting selected file
        onDeleteSelected = (
            self.delete_selected_button.click(
                fn=self.delete_event,
                inputs=[self.selected_file_id],
                outputs=None,
            )
            .then(
                fn=lambda: (None, self.selected_panel_false),
                inputs=[],
                outputs=[self.selected_file_id, self.selected_panel],
                show_progress="hidden",
            )
            .then(
                fn=self.list_file,
                inputs=[self._app.user_id, self.filter],
                outputs=[self.file_list_state, self.file_list],
            )
            .then(
                fn=lambda: [
                    gr.update(interactive=False, visible=True),
                    gr.update(interactive=False, visible=True),
                    gr.update(selected=None),  # only clear selection, not value
                ],
                inputs=[],
                outputs=[self.delete_selected_button, self.show_selected_button, self.file_list],
                show_progress="hidden",
            )
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onDeleteSelected = onDeleteSelected.then(**event)
        #end
        

        self.deselect_button.click(
            fn=lambda: (None, self.selected_panel_false),
            inputs=[],
            outputs=[self.selected_file_id, self.selected_panel],
            show_progress="hidden",
        ).then(
            fn=self.file_selected,
            inputs=[self.selected_file_id],
            outputs=[
                self.chunks,
                self.deselect_button,
                self.delete_button,
                self.download_single_button,
                self.chat_button,
            ],
            show_progress="hidden",
        )

        self.chat_button.click(
            fn=self.set_file_id_selector,
            inputs=[self.selected_file_id],
            outputs=[
                self._index.get_selector_component_ui().selector,
                self._index.get_selector_component_ui().mode,
                self._app.tabs,
            ],
        )

        if not KH_SSO_ENABLED:
            self.download_all_button.click(
                fn=self.download_all_files,
                inputs=[],
                outputs=self.download_all_button,
                show_progress="hidden",
            )

        self.delete_all_button.click(
            self.show_delete_all_confirm,
            [self.file_list],
            [
                self.delete_all_button,
                self.delete_all_button_confirm,
                self.delete_all_button_cancel,
            ],
        )
        self.delete_all_button_cancel.click(
            lambda: [
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
            ],
            None,
            [
                self.delete_all_button,
                self.delete_all_button_confirm,
                self.delete_all_button_cancel,
            ],
        )

        self.delete_all_button_confirm.click(
            fn=self.delete_all_files,
            inputs=[self.file_list],
            outputs=[],
            show_progress="hidden",
        ).then(
            fn=self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
        ).then(
            lambda: [
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
            ],
            None,
            [
                self.delete_all_button,
                self.delete_all_button_confirm,
                self.delete_all_button_cancel,
            ],
        )

        if not KH_SSO_ENABLED:
            self.download_single_button.click(
                fn=self.download_single_file,
                inputs=[self.is_zipped_state, self.selected_file_id],
                outputs=[self.is_zipped_state, self.download_single_button],
                show_progress="hidden",
            )
        else:
            self.download_single_button.click(
                fn=self.download_single_file_simple,
                inputs=[self.is_zipped_state, self.chunks, self.selected_file_id],
                outputs=[self.is_zipped_state, self.download_single_button],
                show_progress="hidden",
            )

        onUploaded = (
            self.upload_button.click(
                fn=lambda: gr.update(visible=True),
                outputs=[self.upload_progress_panel],
            )
            .then(
                fn=self.index_fn,
                inputs=[
                    self.files,
                    self.urls,
                    self.reindex,
                    self._app.settings_state,
                    self._app.user_id,
                ],
                outputs=[self.upload_result, self.upload_info],
                concurrency_limit=20,
            )
            .then(
                fn=lambda: gr.update(value=""),
                outputs=[self.urls],
            )
        )

        uploadedEvent = onUploaded.then(
            fn=self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
            concurrency_limit=20,
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            uploadedEvent = uploadedEvent.then(**event)

        _ = onUploaded.success(
            fn=lambda: None,
            outputs=[self.files],
        )

        self.btn_close_upload_progress_panel.click(
            fn=lambda: (gr.update(visible=False), "", ""),
            outputs=[self.upload_progress_panel, self.upload_result, self.upload_info],
        )

        self.file_list.select(
            fn=self.interact_file_list,
            inputs=[self.file_list_state],
            outputs=[self.selected_file_id, self.selected_panel],
            show_progress="hidden",
        ).then(
            fn=self.file_selected,
            inputs=[self.selected_file_id],
            outputs=[
                self.chunks,
                self.deselect_button,
                self.delete_button,
                self.download_single_button,
                self.chat_button,
                self.show_selected_button,
                self.delete_selected_button,
            ],
            show_progress="hidden",
        )

        self.group_list.select(
            fn=self.interact_group_list,
            inputs=[self.group_list_state],
            outputs=[
                self.group_label,
                self.selected_group_id,
                self.group_name,
                self.group_files,
            ],
            show_progress="hidden",
        ).then(
            fn=lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=True),
            ),
            outputs=[
                self._group_info_panel,
                self.group_add_button,
                self.group_close_button,
                self.group_delete_button,
                self.group_chat_button,
            ],
        )

        self.filter.submit(
            fn=self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
            show_progress="hidden",
        )

        self.group_add_button.click(
            fn=lambda: [
                gr.update(visible=False),
                gr.update(value="### Add new group"),
                gr.update(visible=True),
                gr.update(value=""),
                gr.update(value=[]),
                None,
            ],
            outputs=[
                self.group_add_button,
                self.group_label,
                self._group_info_panel,
                self.group_name,
                self.group_files,
                self.selected_group_id,
            ],
        )

        self.group_chat_button.click(
            fn=self.set_group_id_selector,
            inputs=[self.selected_group_id],
            outputs=[
                self._index.get_selector_component_ui().selector,
                self._index.get_selector_component_ui().mode,
                self._app.tabs,
            ],
        )

        onGroupClosedEvent = {
            "fn": lambda: [
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                None,
            ],
            "outputs": [
                self.group_add_button,
                self._group_info_panel,
                self.group_close_button,
                self.group_delete_button,
                self.group_chat_button,
                self.selected_group_id,
            ],
        }
        self.group_close_button.click(**onGroupClosedEvent)
        onGroupSaved = (
            self.group_save_button.click(
                fn=self.save_group,
                inputs=[
                    self.selected_group_id,
                    self.group_name,
                    self.group_files,
                    self._app.user_id,
                ],
            )
            .then(
                self.list_group,
                inputs=[self._app.user_id, self.file_list_state],
                outputs=[self.group_list_state, self.group_list],
            )
            .then(**onGroupClosedEvent)
        )
        onGroupDeleted = (
            self.group_delete_button.click(
                fn=self.delete_group,
                inputs=[self.selected_group_id],
            )
            .then(
                self.list_group,
                inputs=[self._app.user_id, self.file_list_state],
                outputs=[self.group_list_state, self.group_list],
            )
            .then(**onGroupClosedEvent)
        )

        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onGroupDeleted = onGroupDeleted.then(**event)
            onGroupSaved = onGroupSaved.then(**event)

    def _on_app_created(self):
        """Called when the app is created"""
        if KH_DEMO_MODE:
            return

        self._app.app.load(
            self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
        ).then(
            self.list_group,
            inputs=[self._app.user_id, self.file_list_state],
            outputs=[self.group_list_state, self.group_list],
        ).then(
            self.list_file_names,
            inputs=[self.file_list_state],
            outputs=[self.group_files],
        )

    def _may_extract_zip(self, files, zip_dir: str):
        """Handle zip files"""
        zip_files = [file for file in files if file.endswith(".zip")]
        remaining_files = [file for file in files if not file.endswith("zip")]

        # Clean-up <zip_dir> before unzip to remove old files
        shutil.rmtree(zip_dir, ignore_errors=True)

        for zip_file in zip_files:
            # Prepare new zip output dir, separated for each files
            basename = os.path.splitext(os.path.basename(zip_file))[0]
            zip_out_dir = os.path.join(zip_dir, basename)
            os.makedirs(zip_out_dir, exist_ok=True)
            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(zip_out_dir)

        n_zip_file = 0
        for root, dirs, files in os.walk(zip_dir):
            for file in files:
                ext = os.path.splitext(file)[1]

                # only allow supported file-types ( not zip )
                if ext not in [".zip"] and ext in self._supported_file_types:
                    remaining_files += [os.path.join(root, file)]
                    n_zip_file += 1

        if n_zip_file > 0:
            print(f"Update zip files: {n_zip_file}")

        return remaining_files

    def index_fn(
        self, files, urls, reindex: bool, settings, user_id
    ) -> Generator[tuple[str, str], None, None]:
        """Upload and index the files

        Args:
            files: the list of files to be uploaded
            urls: list of web URLs to be indexed
            reindex: whether to reindex the files
            selected_files: the list of files already selected
            settings: the settings of the app
        """
        if urls:
            files = [it.strip() for it in urls.split("\n")]
            errors = []
        else:
            if not files:
                gr.Info("No uploaded file")
                yield "", ""
                return

            files = self._may_extract_zip(files, flowsettings.KH_ZIP_INPUT_DIR)

            errors = self.validate(files)
            if errors:
                gr.Warning(", ".join(errors))
                yield "", ""
                return

        gr.Info(f"Start indexing {len(files)} files...")

        # get the pipeline
        indexing_pipeline = self._index.get_indexing_pipeline(settings, user_id)

        outputs, debugs = [], []
        # stream the output
        output_stream = indexing_pipeline.stream(files, reindex=reindex)
        try:
            while True:
                response = next(output_stream)
                if response is None:
                    continue
                if response.channel == "index":
                    if response.content["status"] == "success":
                        outputs.append(f"\u2705 | {response.content['file_name']}")
                    elif response.content["status"] == "failed":
                        outputs.append(
                            f"\u274c | {response.content['file_name']}: "
                            f"{response.content['message']}"
                        )
                elif response.channel == "debug":
                    debugs.append(response.text)
                yield "\n".join(outputs), "\n".join(debugs)
        except StopIteration as e:
            results, index_errors, docs = e.value
        except Exception as e:
            debugs.append(f"Error: {e}")
            yield "\n".join(outputs), "\n".join(debugs)
            return

        n_successes = len([_ for _ in results if _])
        if n_successes:
            gr.Info(f"Successfully index {n_successes} files")
        n_errors = len([_ for _ in errors if _])
        if n_errors:
            gr.Warning(f"Have errors for {n_errors} files")

        return results

    def index_fn_file_with_default_loaders(
        self, files, reindex: bool, settings, user_id
    ) -> list["str"]:
        """Function for quick upload with default loaders

        Args:
            files: the list of files to be uploaded
            reindex: whether to reindex the files
            selected_files: the list of files already selected
            settings: the settings of the app
        """
        print("Overriding with default loaders")
        exist_ids = []
        to_process_files = []
        for str_file_path in files:
            file_path = Path(str(str_file_path))
            exist_id = (
                self._index.get_indexing_pipeline(settings, user_id)
                .route(file_path)
                .get_id_if_exists(file_path)
            )
            if exist_id:
                exist_ids.append(exist_id)
            else:
                to_process_files.append(str_file_path)

        returned_ids = []
        settings = deepcopy(settings)
        settings[f"index.options.{self._index.id}.reader_mode"] = "default"
        settings[f"index.options.{self._index.id}.quick_index_mode"] = True
        if to_process_files:
            _iter = self.index_fn(to_process_files, [], reindex, settings, user_id)
            try:
                while next(_iter):
                    pass
            except StopIteration as e:
                returned_ids = e.value

        return exist_ids + returned_ids

    def index_fn_url_with_default_loaders(
        self,
        urls,
        reindex: bool,
        settings,
        user_id,
        request: gr.Request,
    ):
        if KH_DEMO_MODE:
            check_rate_limit("file_upload", request)

        returned_ids: list[str] = []
        settings = deepcopy(settings)
        settings[f"index.options.{self._index.id}.reader_mode"] = "default"
        settings[f"index.options.{self._index.id}.quick_index_mode"] = True

        if KH_DEMO_MODE:
            urls_splitted = urls.split("\n")
            if not all(is_arxiv_url(url) for url in urls_splitted):
                raise ValueError("All URLs must be valid arXiv URLs")

            output_files = [
                download_arxiv_pdf(
                    url,
                    output_path=os.environ.get("GRADIO_TEMP_DIR", "/tmp"),
                )
                for url in urls_splitted
            ]

            exist_ids = []
            to_process_files = []
            for str_file_path in output_files:
                file_path = Path(str_file_path)
                exist_id = (
                    self._index.get_indexing_pipeline(settings, user_id)
                    .route(file_path)
                    .get_id_if_exists(file_path)
                )
                if exist_id:
                    exist_ids.append(exist_id)
                else:
                    to_process_files.append(str_file_path)

            returned_ids = []
            if to_process_files:
                _iter = self.index_fn(to_process_files, [], reindex, settings, user_id)
                try:
                    while next(_iter):
                        pass
                except StopIteration as e:
                    returned_ids = e.value

            returned_ids = exist_ids + returned_ids
        else:
            if urls:
                _iter = self.index_fn([], urls, reindex, settings, user_id)
                try:
                    while next(_iter):
                        pass
                except StopIteration as e:
                    returned_ids = e.value

        return returned_ids

    def index_files_from_dir(
        self, folder_path, reindex, settings, user_id
    ) -> Generator[tuple[str, str], None, None]:
        """This should be constructable by users

        It means that the users can build their own index.
        Build your own index:
            - Input:
                - Type: based on the type, then there are ranges of. Use can select
                multiple panels:
                    - Panels
                    - Data sources
                    - Include patterns
                    - Exclude patterns
                - Indexing functions. Can be a list of indexing functions. Each declared
                function is:
                    - Condition (the source that will go through this indexing function)
                    - Function (the pipeline that run this)
            - Output: artifacts that can be used to -> this is the artifacts that we
            wish
                - Build the UI
                    - Upload page: fixed standard, based on the type
                    - Read page: fixed standard, based on the type
                    - Delete page: fixed standard, based on the type
                - Build the index function
                - Build the chat function

        Step:
            1. Decide on the artifacts
            2. Implement the transformation from artifacts to UI
        """
        if not folder_path:
            yield "", ""
            return

        import fnmatch
        from pathlib import Path

        include_patterns: list[str] = []
        exclude_patterns: list[str] = ["*.png", "*.gif", "*/.*"]
        if include_patterns and exclude_patterns:
            raise ValueError("Cannot have both include and exclude patterns")

        # clean up the include patterns
        for idx in range(len(include_patterns)):
            if include_patterns[idx].startswith("*"):
                include_patterns[idx] = str(Path.cwd() / "**" / include_patterns[idx])
            else:
                include_patterns[idx] = str(
                    Path.cwd() / include_patterns[idx].strip("/")
                )

        # clean up the exclude patterns
        for idx in range(len(exclude_patterns)):
            if exclude_patterns[idx].startswith("*"):
                exclude_patterns[idx] = str(Path.cwd() / "**" / exclude_patterns[idx])
            else:
                exclude_patterns[idx] = str(
                    Path.cwd() / exclude_patterns[idx].strip("/")
                )

        # get the files
        files: list[str] = [str(p) for p in Path(folder_path).glob("**/*.*")]
        if include_patterns:
            for p in include_patterns:
                files = fnmatch.filter(names=files, pat=p)

        if exclude_patterns:
            for p in exclude_patterns:
                files = [f for f in files if not fnmatch.fnmatch(name=f, pat=p)]

        yield from self.index_fn(files, [], reindex, settings, user_id)

    def format_size_human_readable(self, num: float | str, suffix="B"):
        try:
            num = float(num)
        except ValueError:
            return num

        for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
            if abs(num) < 1024.0:
                return f"{num:3.0f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.0f}Yi{suffix}"

    def list_file(self, user_id, name_pattern=""):
        if user_id is None:
            # not signed in
            return [], pd.DataFrame.from_records(
                [
                    {
                        "name": "-",
                        "company": "-",
                        "size": "-",
                        "date": "-",
                    }
                ]
            )

        Source = self._index._resources["Source"]
        with Session(engine) as session:
            statement = select(Source)
            if self._index.config.get("private", False):
                statement = statement.where(Source.user == user_id)
            if name_pattern:
                statement = statement.where(Source.name.ilike(f"%{name_pattern}%"))

            results = []
            for each in session.execute(statement).all():
                item = each[0]
                note = getattr(item, 'note', {}) or {}
                date_val =  item.date_from_file_name or item.date_from_content or item.date_created
                formatted_date = date_val.strftime("%Y-%m-%d")
                # date_val = note.get('date_from_file_name') or note.get('date_from_content') or item.date_created.strftime("%Y-%m-%d")
                # date_val = (str(note.get('date_from_file_name')) if note and note.get('date_from_file_name')
                #     else str(note.get('date_from_content')) if note and note.get('date_from_content') 
                #     else item.date_created.strftime("%Y-%m-%d")
                # )
                company_val = "-"
                if hasattr(item, 'company') and isinstance(item.company, list) and len(item.company) > 0:
                    company_val = " ".join(f"- {str(c)}" for c in item.company if c)
                results.append({
                    "id": item.id,  # simpan id di state
                    "name": item.name,
                    "company": company_val,
                    "size": self.format_size_human_readable(item.size),
                    "date": formatted_date,
                })

        if results:
            # Hide 'id' from DataFrame shown in Gradio, but keep it in results (state)
            file_list = pd.DataFrame.from_records(
                [
                    {k: v for k, v in item.items() if k != "id"}
                    for item in results
                ]
            )
        else:
            file_list = pd.DataFrame.from_records(
                [
                    {
                        "name": "-",
                        "company": "-",
                        "size": "-",
                        "date": "-",
                    }
                ]
            )

        return results, file_list

    def list_file_names(self, file_list_state):
        if file_list_state:
            file_names = [(item["name"], item["id"]) for item in file_list_state]
        else:
            file_names = []

        return gr.update(choices=file_names)

    def list_group(self, user_id, file_list):
        # supply file_list to display the file names in the group
        if file_list:
            file_id_to_name = {item["id"]: item["name"] for item in file_list}
        else:
            file_id_to_name = {}

        if user_id is None:
            # not signed in
            return [], pd.DataFrame.from_records(
                [
                    {
                        "name": "-",
                        "company": "-",
                        "size": "-",
                        "date": "-",
                    }
                ]
            )

        FileGroup = self._index._resources["FileGroup"]
        with Session(engine) as session:
            statement = select(FileGroup)
            if self._index.config.get("private", False):
                statement = statement.where(FileGroup.user == user_id)

            results = [
                {
                    "id": each[0].id,
                    "name": each[0].name,
                    "files": each[0].data.get("files", []),
                    "date_created": each[0].date_created.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for each in session.execute(statement).all()
            ]

        if results:
            formated_results = deepcopy(results)
            for item in formated_results:
                file_names = [
                    file_id_to_name.get(file_id, "-") for file_id in item["files"]
                ]
                item["files"] = ", ".join(
                    f"'{it[:MAX_FILENAME_LENGTH]}..'"
                    if len(it) > MAX_FILENAME_LENGTH
                    else f"'{it}'"
                    for it in file_names
                )
                item_count = len(file_names)
                item_postfix = "s" if item_count > 1 else ""
                item["files"] = f"[{item_count} item{item_postfix}] " + item["files"]

            group_list = pd.DataFrame.from_records(formated_results)
        else:
            group_list = pd.DataFrame.from_records(
                [
                    {
                        "name": "-",
                        "company": "-",
                        "size": "-",
                        "date": "-",
                    }
                ]
            )

        return results, group_list

    def set_group_id_selector(self, selected_group_id):
        FileGroup = self._index._resources["FileGroup"]

        # check if group_name exist
        with Session(engine) as session:
            current_group = (
                session.query(FileGroup).filter_by(id=selected_group_id).first()
            )

        file_ids = [json.dumps(current_group.data["files"])]
        return [file_ids, "select", gr.Tabs(selected="chat-tab")]

    def save_group(self, group_id, group_name, group_files, user_id):
        FileGroup = self._index._resources["FileGroup"]
        current_group = None

        # check if group_name exist
        with Session(engine) as session:
            if group_id:
                current_group = session.query(FileGroup).filter_by(id=group_id).first()
                # update current group with new info
                current_group.name = group_name
                current_group.data["files"] = group_files  # Update the files
                session.commit()
            else:
                current_group = (
                    session.query(FileGroup)
                    .filter_by(
                        name=group_name,
                        user=user_id,
                    )
                    .first()
                )
                if current_group:
                    raise gr.Error(f"Group {group_name} already exists")

                current_group = FileGroup(
                    name=group_name,
                    data={"files": group_files},  # type: ignore
                    user=user_id,
                )
                session.add(current_group)
                session.commit()

            group_id = current_group.id

        gr.Info(f"Group {group_name} has been saved")
        return group_id

    def delete_group(self, group_id):
        if not group_id:
            raise gr.Error("No group is selected")

        FileGroup = self._index._resources["FileGroup"]
        with Session(engine) as session:
            group = session.execute(
                select(FileGroup).where(FileGroup.id == group_id)
            ).first()
            if group:
                item = group[0]
                group_name = item.name
                session.delete(item)
                session.commit()
                gr.Info(f"Group {group_name} has been deleted")
            else:
                raise gr.Error("No group found")

        return None

    def interact_file_list(self, list_files, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No file is uploaded")
            return None, self.selected_panel_false

        if not ev.selected:
            return None, self.selected_panel_false

        idx = ev.index[0]
        return list_files[idx]["id"], self.selected_panel_true.format(
            name=list_files[idx]["name"]
        )

    def interact_group_list(self, list_groups, ev: gr.SelectData):
        selected_id = ev.index[0]
        if (not ev.value or ev.value == "-") and selected_id == 0:
            raise gr.Error("No group is selected")

        selected_item = list_groups[selected_id]
        selected_group_id = selected_item["id"]
        return (
            "### Group Information",
            selected_group_id,
            selected_item["name"],
            selected_item["files"],
        )

    def validate(self, files: list[str]):
        """Validate if the files are valid"""
        paths = [Path(file) for file in files]
        errors = []
        if max_file_size := self._index.config.get("max_file_size", 0):
            errors_max_size = []
            for path in paths:
                if path.stat().st_size > max_file_size * 1e6:
                    errors_max_size.append(path.name)
            if errors_max_size:
                str_errors = ", ".join(errors_max_size)
                if len(str_errors) > 60:
                    str_errors = str_errors[:55] + "..."
                errors.append(
                    f"Maximum file size ({max_file_size} MB) exceeded: {str_errors}"
                )

        if max_number_of_files := self._index.config.get("max_number_of_files", 0):
            with Session(engine) as session:
                current_num_files = session.query(
                    self._index._resources["Source"].id
                ).count()
            if len(paths) + current_num_files > max_number_of_files:
                errors.append(
                    f"Maximum number of files ({max_number_of_files}) will be exceeded"
                )

        return errors


class FileSelector(BasePage):
    """File selector UI in the Chat page"""

    def __init__(self, app, index):
        super().__init__(app)
        self._index = index
        self.on_building_ui()

    def default(self):
        if self._app.f_user_management:
            return "all", [], "", "", [], -1, "", ""
        return "all", [], "", "", [], 1, "", ""

    def on_building_ui(self):
        default_mode, default_selector, start_date, end_date, filtered_files_ids, user_id, keyword, company = self.default()

        self.mode = gr.Radio(
            value=default_mode,
            choices=[
                ("Search By Date", "date"),
            ],
            container=False,
            visible=False
        )
        self.selector = gr.Dropdown(
            label="Files",
            value=default_selector,
            choices=[],
            multiselect=True,
            container=False,
            interactive=True,
            visible=False,
        )
        self.search_keyword_input = gr.Textbox(
            label="Search Keyword",
            value=keyword,
            visible=True,
            placeholder="Search inside documents"
        )
        self.search_company_input = gr.Textbox(
            label="Company Mentioned",
            value=company,
            visible=True,
            placeholder="Search company name"
        )
        self.start_date_picker = gr.DateTime(
            label="Start Date",
            value=start_date,
            visible=True,
            include_time=False
        )
        self.end_date_picker = gr.DateTime(
            label="End Date",
            value=end_date,
            visible=True,
            include_time=False
        )
        self.apply_filter_button = gr.Button(
            "Apply",
            visible=True,
        )
        self.clear_button = gr.Button(
            "Clear",
            visible=True,
        )
        self.filtered_file_ids = gr.State(value=filtered_files_ids)
        self.selector_user_id = gr.State(value=user_id)
        self.selector_choices = gr.JSON(
            value=[],
            visible=False,
        )

    def on_register_events(self):
        # self.mode.change(
        #     fn=lambda mode, user_id: (
        #         gr.update(visible=mode == "select"), 
        #         gr.update(visible=mode == "date"),
        #         gr.update(visible=mode == "date"),
        #         gr.update(visible=mode == "date"),
        #         user_id
        #     ),
        #     inputs=[self.mode, self._app.user_id],
        #     outputs=[
        #         self.selector,
        #         self.start_date_picker,
        #         self.end_date_picker,
        #         self.apply_date_filter_button,
        #         self.selector_user_id
        #     ],
        # )
        self.apply_filter_button.click(
            fn=self.get_filtered_files_and_list,
            inputs=[
                self.start_date_picker,
                self.end_date_picker,
                self._app.user_id,
                self.search_keyword_input,
                self.search_company_input,
            ],
            outputs=[self.filtered_file_ids],
        )
        self.clear_button.click(
            fn=self.get_all_files,
            inputs=[self._app.user_id],
            outputs=[
                self.filtered_file_ids, 
                self.start_date_picker, 
                self.end_date_picker,
                self.search_keyword_input,
                self.search_company_input
            ],
        )
        # attach special event for the first index
        if self._index.id == 1:
            self.selector_choices.change(
                fn=None,
                inputs=[self.selector_choices],
                js=update_file_list_js,
                show_progress="hidden",
            )

    def as_gradio_component(self):
        return [
            self.mode, 
            self.selector, 
            self.start_date_picker, 
            self.end_date_picker, 
            self.filtered_file_ids,
            self.selector_user_id,
            self.search_keyword_input,
            self.search_company_input
        ]

    def get_selected_ids(self, components):
        mode, selected, start_date, end_date, filtered_file_ids, user_id, keyword, company = components
        if user_id is None:
            return []
        
        if mode == "select":
            return selected
        
        # Use filtered_file_ids if provided
        if len(filtered_file_ids) > 0:
            return filtered_file_ids

        file_ids = []
        with Session(engine) as session:
            Source = self._index._resources["Source"]
            # Use coalesce to prioritize date_from_file_name, then date_from_file, then date_created
            date_column = func.coalesce(
                Source.date_from_file_name,
                Source.date_from_content,
                Source.date_created
            )

            statement = select(Source.id)
            if self._index.config.get("private", False):
                statement = statement.where(Source.user == user_id)
            
            # Querying by date (for Apply Date Filter)
            if start_date and end_date:
                statement = statement.where(date_column >= start_date)
                statement = statement.where(date_column <= end_date)

            # Querying by keyword
            if keyword:
                statement = statement.where(
                    text(
                        f"""EXISTS (
                            SELECT 1 FROM json_each({Source.keywords.key})
                            WHERE LOWER(value) = LOWER(:keyword)
                        )"""
                    )
                ).params(keyword=keyword)

            # Querying by company
            if company:
                statement = statement.where(
                    text(
                        f"""EXISTS (
                            SELECT 1 FROM json_each({Source.company.key})
                            WHERE LOWER(value) LIKE LOWER(:company)
                        )"""
                    )
                ).params(company=f"%{company}%")

            results = session.execute(statement).all()

            for (id,) in results:
                file_ids.append(id)

        return file_ids

    def load_files(self, selected_files, user_id):
        options: list = []
        available_ids = []
        if user_id is None:
            # not signed in
            return gr.update(value=selected_files, choices=options), options

        with Session(engine) as session:
            # get file list from Source table
            statement = select(self._index._resources["Source"])
            if self._index.config.get("private", False):
                statement = statement.where(
                    self._index._resources["Source"].user == user_id
                )

            if KH_DEMO_MODE:
                # limit query by MAX_FILE_COUNT
                statement = statement.limit(MAX_FILE_COUNT)

            results = session.execute(statement).all()
            for result in results:
                available_ids.append(result[0].id)
                options.append((result[0].name, result[0].id))

            # get group list from FileGroup table
            FileGroup = self._index._resources["FileGroup"]
            statement = select(FileGroup)
            if self._index.config.get("private", False):
                statement = statement.where(FileGroup.user == user_id)
            results = session.execute(statement).all()
            for result in results:
                item = result[0]
                options.append(
                    (f"group: '{item.name}'", json.dumps(item.data.get("files", [])))
                )

        if selected_files:
            available_ids_set = set(available_ids)
            selected_files = [
                each for each in selected_files if each in available_ids_set
            ]

        return gr.update(value=selected_files, choices=options), options
        
    def get_filtered_files_and_list(self, start, end, user_id, keyword, company):
        # Convert float timestamps to datetime
        if isinstance(start, (float, int)):
            start = datetime.datetime.fromtimestamp(start)
        if isinstance(end, (float, int)):
            end = datetime.datetime.fromtimestamp(end)

        # Convert date to datetime for filtering
        if isinstance(start, datetime.date) and not isinstance(start, datetime.datetime):
            start = datetime.datetime.combine(start, datetime.time.min)
        # Always force end time to 23:59:59 if time is 00:00:00
        if isinstance(end, datetime.datetime) and end.time() == datetime.time(0, 0, 0):
            end = end.replace(hour=23, minute=59, second=59)
        elif isinstance(end, datetime.date) and not isinstance(end, datetime.datetime):
            end = datetime.datetime.combine(end, datetime.time(23, 59, 59))

        file_ids = self.get_selected_ids(["filter", [], start, end, [], user_id, keyword, company])
        
        return file_ids

    def get_all_files(self, user_id):
        # Show all files for the user (no filters)
        file_ids = self.get_selected_ids(["all", [], "", "", [], user_id, "", ""])
        
        return file_ids, "", "", "", ""

    def _on_app_created(self):
        self._app.app.load(
            self.load_files,
            inputs=[self.selector, self._app.user_id],
            outputs=[self.selector, self.selector_choices],
        )

    def on_subscribe_public_events(self):
        self._app.subscribe_event(
            name=f"onFileIndex{self._index.id}Changed",
            definition={
                "fn": self.load_files,
                "inputs": [self.selector, self._app.user_id],
                "outputs": [self.selector, self.selector_choices],
                "show_progress": "hidden",
            },
        )

        if self._app.f_user_management:
            for event_name in ["onSignIn", "onSignOut"]:
                self._app.subscribe_event(
                    name=event_name,
                    definition={
                        "fn": self.load_files,
                        "inputs": [self.selector, self._app.user_id],
                        "outputs": [self.selector, self.selector_choices],
                        "show_progress": "hidden",
                    },
                )
                # Update filtered_file_ids on sign in
                self._app.subscribe_event(
                    name="onSignIn",
                    definition={
                        "fn": self.get_all_files,
                        "inputs": [self._app.user_id],
                        "outputs": [
                            self.filtered_file_ids, 
                            self.start_date_picker, 
                            self.end_date_picker,
                            self.search_keyword_input,
                            self.search_company_input
                        ],
                        "show_progress": "hidden",
                    },
                )
                # Clear filtered_file_ids on sign out
                self._app.subscribe_event(
                    name="onSignOut",
                    definition={
                        "fn": lambda user_id: ([], "No files found."),
                        "inputs": [self._app.user_id],
                        "outputs": [self.filtered_file_ids],
                        "show_progress": "hidden",
                    },
                )