import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import gradio as gr
import pandas as pd
from gradio.data_classes import FileData
from gradio.utils import NamedString
from ktem.app import BasePage
from ktem.db.engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings

from ...utils.commands import WEB_SEARCH_COMMAND

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_SSO_ENABLED = getattr(flowsettings, "KH_SSO_ENABLED", False)
DOWNLOAD_MESSAGE = "Start download"
MAX_FILENAME_LENGTH = 20
MAX_FILE_COUNT = 200

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
""".replace("web_search", WEB_SEARCH_COMMAND)


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
    def __init__(self, app: Any, index: Any) -> None:
        super().__init__(app)
        self._index = index
        self._supported_file_types_str = self._index.config.get(
            "supported_file_types", ""
        )
        self._supported_file_types = [
            each.strip() for each in self._supported_file_types_str.split(",")
        ]
        self.on_building_ui()

    def on_building_ui(self) -> None:
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
    def __init__(self, app: Any, index: Any) -> None:
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

    def upload_instruction(self) -> str:
        msgs: list[str] = []
        if self._supported_file_types:
            msgs.append(f"- Supported file types: {self._supported_file_types_str}")

        if max_file_size := self._index.config.get("max_file_size", 0):
            msgs.append(f"- Maximum file size: {max_file_size} MB")

        if max_number_of_files := self._index.config.get("max_number_of_files", 0):
            msgs.append(f"- The index can have maximum {max_number_of_files} files")

        if msgs:
            return "\n".join(msgs)

        return ""

    def render_file_list(self) -> None:
        self.filter = gr.Textbox(
            value="",
            label="Filter by name:",
            info=(
                "(1) Case-insensitive. (2) Search with empty string to show all files."
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

        with gr.Row() as self.selection_info:
            self.selected_file_id = gr.State(value=None)
            with gr.Column(scale=2):
                self.selected_panel = gr.Markdown(self.selected_panel_false)

        self.chunks = gr.HTML(visible=False)

        with gr.Accordion("Advance options", open=False):
            with gr.Row():
                if not KH_SSO_ENABLED:
                    self.download_all_button = gr.DownloadButton(
                        "Download all files",
                    )
                self.delete_all_button = gr.Button(
                    "Delete all files",
                    variant="stop",
                    visible=True,
                )
                self.delete_all_button_confirm = gr.Button(
                    "Confirm delete", variant="stop", visible=False
                )
                self.delete_all_button_cancel = gr.Button("Cancel", visible=False)

    def render_group_list(self) -> None:
        self.group_list_state = gr.State(value=None)
        self.group_list = gr.DataFrame(
            headers=[
                "id",
                "name",
                "files",
                "date_created",
            ],
            column_widths=["0%", "25%", "55%", "20%"],
            interactive=False,
            wrap=False,
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

    def on_building_ui(self) -> None:
        """Build the UI of the app"""
        with gr.Row():
            with gr.Column(scale=1):
                with gr.Column() as self.upload:
                    with gr.Tab("Upload Files"):
                        self.files = File(
                            file_types=self._supported_file_types,
                            file_count="multiple",
                            container=True,
                            show_label=False,
                        )

                        msg = self.upload_instruction()
                        if msg:
                            gr.Markdown(msg)

                    with gr.Tab("Use Web Links"):
                        self.urls = gr.Textbox(
                            label="Input web URLs",
                            lines=8,
                        )
                        gr.Markdown("(separated by new line)")

                    with gr.Accordion("Advanced indexing options", open=False):
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

                with gr.Tab("Files"):
                    self.render_file_list()

                with gr.Tab("Groups"):
                    self.render_group_list()

    def format_size_human_readable(self, num: float | str, *, suffix: str = "B") -> str:
        """Format file size in human readable format"""
        try:
            num = float(num)
        except ValueError:
            return str(num)

        for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
            if abs(num) < 1024.0:
                return f"{num:3.0f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.0f}Yi{suffix}"

    def validate_files(self, files: list[str]) -> list[str]:
        """Validate if the files are valid"""
        if not files:
            return []

        paths = [Path(file) for file in files]
        errors: list[str] = []

        if max_file_size := self._index.config.get("max_file_size", 0):
            errors_max_size: list[str] = []
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

    def validate_urls(self, urls: list[str]) -> list[str]:
        """Validate if the urls are valid"""
        if not urls:
            return []

        errors: list[str] = []
        for url in urls:
            if not url.startswith("http") and not url.startswith("https"):
                errors.append(f"Invalid url `{url}`")
        return errors

    def list_file(
        self, user_id: str | None, name_pattern: str = ""
    ) -> tuple[list[dict[str, Any]], pd.DataFrame]:
        """List files for the user"""
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

        return results, file_list

    def index_fn(
        self,
        files: list[str] | None,
        urls: str | None,
        *,
        reindex: bool,
        settings: dict[str, Any],
        user_id: str | None,
    ) -> Generator[tuple[str, str], None, None]:
        """Upload and index the files

        Args:
            files: the list of files to be uploaded
            urls: list of web URLs to be indexed
            reindex: whether to reindex the files
            settings: the settings of the app
            user_id: the user ID
        """
        if urls:
            files = [it.strip() for it in urls.split("\n")]
            errors = self.validate_urls(files)
        else:
            if not files:
                gr.Info("No uploaded file")
                yield "", ""
                return
            files, unzip_errors = self._may_extract_zip(
                files, flowsettings.KH_ZIP_INPUT_DIR
            )
            errors = self.validate_files(files)
            errors.extend(unzip_errors)

        if errors:
            gr.Warning(", ".join(errors))
            yield "", ""
            return

        gr.Info(f"Start indexing {len(files)} files...")

        # get the pipeline
        indexing_pipeline = self._index.get_indexing_pipeline(settings, user_id)

        outputs: list[str] = []
        debugs: list[str] = []
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


class FileSelector(BasePage):
    """File selector UI in the Chat page"""

    def __init__(self, app: Any, index: Any) -> None:
        super().__init__(app)
        self._index = index
        self.on_building_ui()

    def default(self) -> tuple[str, list[Any], int]:
        if self._app.f_user_management:
            return "disabled", [], -1
        return "disabled", [], 1

    def on_building_ui(self) -> None:
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
        self.selector_choices = gr.JSON(
            value=[],
            visible=False,
        )

    def on_register_events(self) -> None:
        self.mode.change(
            fn=lambda mode, user_id: (gr.update(visible=mode == "select"), user_id),
            inputs=[self.mode, self._app.user_id],
            outputs=[self.selector, self.selector_user_id],
        )
        if self._index.id == 1:
            self.selector_choices.change(
                fn=None,
                inputs=[self.selector_choices],
                js=update_file_list_js,
                show_progress="hidden",
            )

    def as_gradio_component(self) -> list[Any]:
        return [self.mode, self.selector, self.selector_user_id]

    def get_selected_ids(self, components: list[Any]) -> list[Any]:
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

    def load_files(
        self, selected_files: list[Any], user_id: str | None
    ) -> tuple[gr.Dropdown, list[Any]]:
        options: list[Any] = []
        available_ids = []
        if user_id is None:
            return gr.update(value=selected_files, choices=options), options

        with Session(engine) as session:
            statement = select(self._index._resources["Source"])
            if self._index.config.get("private", False):
                statement = statement.where(
                    self._index._resources["Source"].user == user_id
                )

            if KH_DEMO_MODE:
                statement = statement.limit(MAX_FILE_COUNT)

            results = session.execute(statement).all()
            for result in results:
                available_ids.append(result[0].id)
                options.append((result[0].name, result[0].id))

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

    def _on_app_created(self) -> None:
        self._app.app.load(
            self.load_files,
            inputs=[self.selector, self._app.user_id],
            outputs=[self.selector, self.selector_choices],
        )

    def on_subscribe_public_events(self) -> None:
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
