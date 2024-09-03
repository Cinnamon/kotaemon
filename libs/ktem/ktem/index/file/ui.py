import html
import os
import shutil
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Generator

import gradio as gr
import pandas as pd
from gradio.data_classes import FileData
from gradio.utils import NamedString
from ktem.app import BasePage
from ktem.db.engine import engine
from ktem.utils.render import Render
from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings

DOWNLOAD_MESSAGE = "Press again to download"


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
        self.on_building_ui()

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

    def on_building_ui(self):
        """Build the UI of the app"""
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## File Upload")
                with gr.Column() as self.upload:
                    self.files = File(
                        file_types=self._supported_file_types,
                        file_count="multiple",
                        container=True,
                        show_label=False,
                    )

                    msg = self.upload_instruction()
                    if msg:
                        gr.Markdown(msg)

                    with gr.Accordion("Advanced indexing options", open=True):
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

                gr.Markdown("## File List")
                self.filter = gr.Textbox(
                    value="",
                    label="Filter by name:",
                    info=(
                        "(1) Case-insensitive. "
                        "(2) Search with empty string to show all files."
                    ),
                )
                self.file_list_state = gr.State(value=None)
                self.file_list = gr.DataFrame(
                    headers=[
                        "id",
                        "name",
                        "size",
                        "tokens",
                        "loader",
                        "date_created",
                    ],
                    column_widths=["0%", "50%", "8%", "7%", "15%", "20%"],
                    interactive=False,
                    wrap=False,
                    elem_id="file_list_view",
                )

                with gr.Row():
                    self.deselect_button = gr.Button(
                        "Close",
                        visible=False,
                    )
                    self.delete_button = gr.Button(
                        "Delete",
                        variant="stop",
                        visible=False,
                    )
                with gr.Row():
                    self.is_zipped_state = gr.State(value=False)
                    self.download_all_button = gr.DownloadButton(
                        "Download all files",
                        visible=True,
                    )
                    self.download_single_button = gr.DownloadButton(
                        "Download file",
                        visible=False,
                    )

                with gr.Row() as self.selection_info:
                    self.selected_file_id = gr.State(value=None)
                    with gr.Column(scale=2):
                        self.selected_panel = gr.Markdown(self.selected_panel_false)

                self.chunks = gr.HTML(visible=False)

    def on_subscribe_public_events(self):
        """Subscribe to the declared public event of the app"""
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
        if file_id is not None:
            # get the chunks

            Index = self._index._resources["Index"]
            with Session(engine) as session:
                matches = session.execute(
                    select(Index).where(
                        Index.source_id == file_id,
                        Index.relation_type == "document",
                    )
                )
                doc_ids = [doc.target_id for (doc,) in matches]
                docs = self._index._docstore.get(doc_ids)
                docs = sorted(
                    docs, key=lambda x: x.metadata.get("page_label", float("inf"))
                )

                for idx, doc in enumerate(docs):
                    title = html.escape(
                        f"{doc.text[:50]}..." if len(doc.text) > 50 else doc.text
                    )
                    doc_type = doc.metadata.get("type", "text")
                    content = ""
                    if doc_type == "text":
                        content = html.escape(doc.text)
                    elif doc_type == "table":
                        content = Render.table(doc.text)
                    elif doc_type == "image":
                        content = Render.image(
                            url=doc.metadata.get("image_origin", ""), text=doc.text
                        )

                    header_prefix = f"[{idx+1}/{len(docs)}]"
                    if doc.metadata.get("page_label"):
                        header_prefix += f" [Page {doc.metadata['page_label']}]"

                    chunks.append(
                        Render.collapsible(
                            header=f"{header_prefix} {title}",
                            content=content,
                        )
                    )
        return (
            gr.update(value="".join(chunks), visible=file_id is not None),
            gr.update(visible=file_id is not None),
            gr.update(visible=file_id is not None),
            gr.update(visible=file_id is not None),
        )

    def delete_event(self, file_id):
        file_name = ""
        with Session(engine) as session:
            source = session.execute(
                select(self._index._resources["Source"]).where(
                    self._index._resources["Source"].id == file_id
                )
            ).first()
            if source:
                file_name = source[0].name
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

    def on_register_events(self):
        """Register all events to the app"""
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
                fn=self.file_selected,
                inputs=[self.selected_file_id],
                outputs=[
                    self.chunks,
                    self.deselect_button,
                    self.delete_button,
                    self.download_single_button,
                ],
                show_progress="hidden",
            )
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onDeleted = onDeleted.then(**event)

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
            ],
            show_progress="hidden",
        )

        self.download_all_button.click(
            fn=self.download_all_files,
            inputs=[],
            outputs=self.download_all_button,
            show_progress="hidden",
        )

        self.download_single_button.click(
            fn=self.download_single_file,
            inputs=[self.is_zipped_state, self.selected_file_id],
            outputs=[self.is_zipped_state, self.download_single_button],
            show_progress="hidden",
        )

        onUploaded = self.upload_button.click(
            fn=lambda: gr.update(visible=True),
            outputs=[self.upload_progress_panel],
        ).then(
            fn=self.index_fn,
            inputs=[
                self.files,
                self.reindex,
                self._app.settings_state,
                self._app.user_id,
            ],
            outputs=[self.upload_result, self.upload_info],
            concurrency_limit=20,
        )

        try:
            # quick file upload event registration of first Index only
            if self._index.id == 1:
                self.quick_upload_state = gr.State(value=[])
                print("Setting up quick upload event")
                quickUploadedEvent = (
                    self._app.chat_page.quick_file_upload.upload(
                        fn=lambda: gr.update(
                            value="Please wait for the indexing process "
                            "to complete before adding your question."
                        ),
                        outputs=self._app.chat_page.quick_file_upload_status,
                    )
                    .then(
                        fn=self.index_fn_with_default_loaders,
                        inputs=[
                            self._app.chat_page.quick_file_upload,
                            gr.State(value=False),
                            self._app.settings_state,
                            self._app.user_id,
                        ],
                        outputs=self.quick_upload_state,
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
                for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
                    quickUploadedEvent = quickUploadedEvent.then(**event)

                quickUploadedEvent.success(
                    fn=lambda x: x,
                    inputs=self.quick_upload_state,
                    outputs=self._app.chat_page._indices_input[1],
                ).then(
                    fn=lambda: gr.update(value="Indexing completed."),
                    outputs=self._app.chat_page.quick_file_upload_status,
                ).then(
                    fn=self.list_file,
                    inputs=[self._app.user_id, self.filter],
                    outputs=[self.file_list_state, self.file_list],
                    concurrency_limit=20,
                )

        except Exception as e:
            print(e)

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
            inputs=[self.file_list],
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
            ],
            show_progress="hidden",
        )

        self.filter.submit(
            fn=self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
            show_progress="hidden",
        )

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_file,
            inputs=[self._app.user_id, self.filter],
            outputs=[self.file_list_state, self.file_list],
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
        self, files, reindex: bool, settings, user_id
    ) -> Generator[tuple[str, str], None, None]:
        """Upload and index the files

        Args:
            files: the list of files to be uploaded
            reindex: whether to reindex the files
            selected_files: the list of files already selected
            settings: the settings of the app
        """
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
                        outputs.append(f"\u2705 | {response.content['file_path'].name}")
                    elif response.content["status"] == "failed":
                        outputs.append(
                            f"\u274c | {response.content['file_path'].name}: "
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

    def index_fn_with_default_loaders(
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
            _iter = self.index_fn(to_process_files, reindex, settings, user_id)
            try:
                while next(_iter):
                    pass
            except StopIteration as e:
                returned_ids = e.value

        return exist_ids + returned_ids

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

        yield from self.index_fn(files, reindex, settings, user_id)

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
                        "id": "-",
                        "name": "-",
                        "size": "-",
                        "tokens": "-",
                        "loader": "-",
                        "date_created": "-",
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
            results = [
                {
                    "id": each[0].id,
                    "name": each[0].name,
                    "size": self.format_size_human_readable(each[0].size),
                    "tokens": self.format_size_human_readable(
                        each[0].note.get("tokens", "-"), suffix=""
                    ),
                    "loader": each[0].note.get("loader", "-"),
                    "date_created": each[0].date_created.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for each in session.execute(statement).all()
            ]

        if results:
            file_list = pd.DataFrame.from_records(results)
        else:
            file_list = pd.DataFrame.from_records(
                [
                    {
                        "id": "-",
                        "name": "-",
                        "size": "-",
                        "tokens": "-",
                        "loader": "-",
                        "date_created": "-",
                    }
                ]
            )

        print(f"{len(results)=}, {len(file_list)=}")
        return results, file_list

    def interact_file_list(self, list_files, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No file is uploaded")
            return None, self.selected_panel_false

        if not ev.selected:
            return None, self.selected_panel_false

        return list_files["id"][ev.index[0]], self.selected_panel_true.format(
            name=list_files["name"][ev.index[0]]
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
            return "disabled", [], -1
        return "disabled", [], 1

    def on_building_ui(self):
        default_mode, default_selector, user_id = self.default()

        self.mode = gr.Radio(
            value=default_mode,
            choices=[
                ("Search All", "all"),
                ("Search In File(s)", "select"),
            ],
            container=False,
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
        self.selector_user_id = gr.State(value=user_id)

    def on_register_events(self):
        self.mode.change(
            fn=lambda mode, user_id: (gr.update(visible=mode == "select"), user_id),
            inputs=[self.mode, self._app.user_id],
            outputs=[self.selector, self.selector_user_id],
        )

    def as_gradio_component(self):
        return [self.mode, self.selector, self.selector_user_id]

    def get_selected_ids(self, components):
        mode, selected, user_id = components[0], components[1], components[2]
        if user_id is None:
            return []

        if mode == "disabled":
            return []
        elif mode == "select":
            return selected

        file_ids = []
        with Session(engine) as session:
            statement = select(self._index._resources["Source"].id)
            if self._index.config.get("private", False):
                statement = statement.where(
                    self._index._resources["Source"].user == user_id
                )
            results = session.execute(statement).all()
            for (id,) in results:
                file_ids.append(id)

        return file_ids

    def load_files(self, selected_files, user_id):
        options: list = []
        available_ids = []
        if user_id is None:
            # not signed in
            return gr.update(value=selected_files, choices=options)

        with Session(engine) as session:
            statement = select(self._index._resources["Source"])
            if self._index.config.get("private", False):

                statement = statement.where(
                    self._index._resources["Source"].user == user_id
                )

            results = session.execute(statement).all()
            for result in results:
                available_ids.append(result[0].id)
                options.append((result[0].name, result[0].id))

        if selected_files:
            available_ids_set = set(available_ids)
            selected_files = [
                each for each in selected_files if each in available_ids_set
            ]

        return gr.update(value=selected_files, choices=options)

    def _on_app_created(self):
        self._app.app.load(
            self.load_files,
            inputs=[self.selector, self._app.user_id],
            outputs=[self.selector],
        )

    def on_subscribe_public_events(self):
        self._app.subscribe_event(
            name=f"onFileIndex{self._index.id}Changed",
            definition={
                "fn": self.load_files,
                "inputs": [self.selector, self._app.user_id],
                "outputs": [self.selector],
                "show_progress": "hidden",
            },
        )
        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.load_files,
                    "inputs": [self.selector, self._app.user_id],
                    "outputs": [self.selector],
                    "show_progress": "hidden",
                },
            )
            self._app.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": self.load_files,
                    "inputs": [self.selector, self._app.user_id],
                    "outputs": [self.selector],
                    "show_progress": "hidden",
                },
            )
