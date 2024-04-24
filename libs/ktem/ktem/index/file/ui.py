import os
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd
from gradio.data_classes import FileData
from gradio.utils import NamedString
from ktem.app import BasePage
from ktem.db.engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session


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
            self.file_output = gr.File(
                visible=False, label="Output files (debug purpose)"
            )


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
                    self.file_output = gr.File(
                        visible=False, label="Output files (debug purpose)"
                    )

            with gr.Column(scale=4):
                gr.Markdown("## File List")
                self.file_list_state = gr.State(value=None)
                self.file_list = gr.DataFrame(
                    headers=["id", "name", "size", "text_length", "date_created"],
                    interactive=False,
                )

                with gr.Row() as self.selection_info:
                    self.selected_file_id = gr.State(value=None)
                    with gr.Column(scale=2):
                        self.selected_panel = gr.Markdown(self.selected_panel_false)
                    with gr.Column(scale=1):
                        self.deselect_button = gr.Button(
                            "Deselect",
                            scale=1,
                            visible=False,
                            elem_classes=["right-button"],
                        )

                self.delete_button = gr.Button(
                    "Delete", variant="stop", elem_classes=["right-button"]
                )
                self.delete_yes = gr.Button(
                    "Confirm Delete",
                    variant="stop",
                    visible=False,
                    elem_classes=["right-button"],
                )
                self.delete_no = gr.Button(
                    "Cancel",
                    visible=False,
                    elem_classes=["right-button"],
                )

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
        if file_id is None:
            deselect = gr.update(visible=False)
        else:
            deselect = gr.update(visible=True)
        return (
            deselect,
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    def to_confirm_delete(self, file_id):
        if file_id is None:
            gr.Warning("No file is selected")
            return (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            )

        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        )

    def delete_yes_event(self, file_id):
        with Session(engine) as session:
            source = session.execute(
                select(self._index._resources["Source"]).where(
                    self._index._resources["Source"].id == file_id
                )
            ).first()
            if source:
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
                else:
                    ds_ids.append(each[0].target_id)
                session.delete(each[0])
            session.commit()

        self._index._vs.delete(vs_ids)
        self._index._docstore.delete(ds_ids)

        gr.Info(f"File {file_id} has been deleted")

        return None, self.selected_panel_false

    def delete_no_event(self):
        return (
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    def on_register_events(self):
        """Register all events to the app"""
        self.delete_button.click(
            fn=self.to_confirm_delete,
            inputs=[self.selected_file_id],
            outputs=[self.delete_button, self.delete_yes, self.delete_no],
            show_progress="hidden",
        )

        onDeleted = (
            self.delete_yes.click(
                fn=self.delete_yes_event,
                inputs=[self.selected_file_id],
                outputs=None,
            )
            .then(
                fn=lambda: (None, self.selected_panel_false),
                inputs=None,
                outputs=[self.selected_file_id, self.selected_panel],
                show_progress="hidden",
            )
            .then(
                fn=self.list_file,
                inputs=[self._app.user_id],
                outputs=[self.file_list_state, self.file_list],
            )
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onDeleted = onDeleted.then(**event)

        self.delete_no.click(
            fn=self.delete_no_event,
            inputs=None,
            outputs=[self.delete_button, self.delete_yes, self.delete_no],
            show_progress="hidden",
        )
        self.deselect_button.click(
            fn=lambda: (None, self.selected_panel_false),
            inputs=None,
            outputs=[self.selected_file_id, self.selected_panel],
            show_progress="hidden",
        )
        self.selected_panel.change(
            fn=self.file_selected,
            inputs=[self.selected_file_id],
            outputs=[
                self.deselect_button,
                self.delete_button,
                self.delete_yes,
                self.delete_no,
            ],
            show_progress="hidden",
        )

        onUploaded = self.upload_button.click(
            fn=self.index_fn,
            inputs=[
                self.files,
                self.reindex,
                self._app.settings_state,
                self._app.user_id,
            ],
            outputs=[self.file_output],
            concurrency_limit=20,
        ).then(
            fn=self.list_file,
            inputs=[self._app.user_id],
            outputs=[self.file_list_state, self.file_list],
            concurrency_limit=20,
        )
        for event in self._app.get_event(f"onFileIndex{self._index.id}Changed"):
            onUploaded = onUploaded.then(**event)

        self.file_list.select(
            fn=self.interact_file_list,
            inputs=[self.file_list],
            outputs=[self.selected_file_id, self.selected_panel],
            show_progress="hidden",
        )

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_file,
            inputs=[self._app.user_id],
            outputs=[self.file_list_state, self.file_list],
        )

    def index_fn(self, files, reindex: bool, settings, user_id):
        """Upload and index the files

        Args:
            files: the list of files to be uploaded
            reindex: whether to reindex the files
            selected_files: the list of files already selected
            settings: the settings of the app
        """
        if not files:
            gr.Info("No uploaded file")
            return gr.update()

        errors = self.validate(files)
        if errors:
            gr.Warning(", ".join(errors))
            return gr.update()

        gr.Info(f"Start indexing {len(files)} files...")

        # get the pipeline
        indexing_pipeline = self._index.get_indexing_pipeline(settings, user_id)

        result = indexing_pipeline(files, reindex=reindex)
        if result is None:
            gr.Info("Finish indexing")
            return
        output_nodes, _ = result
        gr.Info(f"Finish indexing into {len(output_nodes)} chunks")

        # download the file
        text = "\n\n".join([each.text for each in output_nodes])
        handler, file_path = tempfile.mkstemp(suffix=".txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        os.close(handler)

        return gr.update(value=file_path, visible=True)

    def index_files_from_dir(self, folder_path, reindex, settings, user_id):
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

        return self.index_fn(files, reindex, settings, user_id)

    def list_file(self, user_id):
        if user_id is None:
            # not signed in
            return [], pd.DataFrame.from_records(
                [
                    {
                        "id": "-",
                        "name": "-",
                        "size": "-",
                        "text_length": "-",
                        "date_created": "-",
                    }
                ]
            )

        Source = self._index._resources["Source"]
        with Session(engine) as session:
            statement = select(Source)
            if self._index.config.get("private", False):
                statement = statement.where(Source.user == user_id)
            results = [
                {
                    "id": each[0].id,
                    "name": each[0].name,
                    "size": each[0].size,
                    "text_length": each[0].text_length,
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
                        "text_length": "-",
                        "date_created": "-",
                    }
                ]
            )

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
                ("Disabled", "disabled"),
                ("Search All", "all"),
                ("Select", "select"),
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
