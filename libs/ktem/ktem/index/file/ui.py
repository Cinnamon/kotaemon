import os
import tempfile

import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.engine import engine
from sqlalchemy import select
from sqlalchemy.orm import Session


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


class FileIndexPage(BasePage):
    def __init__(self, app, index):
        super().__init__(app)
        self._index = index
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
        self.selected_panel_false = "Selected file: (please select above)"
        self.selected_panel_true = "Selected file: {name}"
        # TODO: on_building_ui is not correctly named if it's always called in
        # the constructor
        self.public_events = [f"onFileIndex{index.id}Changed"]
        self.on_building_ui()

    def on_building_ui(self):
        """Build the UI of the app"""
        with gr.Accordion(label="File upload", open=False):
            gr.Markdown(
                f"Supported file types: {', '.join(self._supported_file_types)}",
            )
            self.files = gr.File(
                file_types=self._supported_file_types,
                file_count="multiple",
                container=False,
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

        gr.Markdown("## File list")
        self.file_list_state = gr.State(value=None)
        self.file_list = gr.DataFrame(
            headers=["id", "name", "size", "text_length", "date_created"],
            interactive=False,
        )

        with gr.Row():
            self.selected_file_id = gr.State(value=None)
            self.selected_panel = gr.Markdown(self.selected_panel_false)
            self.deselect_button = gr.Button("Deselect", visible=False)

        with gr.Row():
            with gr.Column():
                self.view_button = gr.Button("View Text (WIP)")
            with gr.Column():
                self.delete_button = gr.Button("Delete")
                with gr.Row():
                    self.delete_yes = gr.Button(
                        "Confirm Delete", variant="primary", visible=False
                    )
                    self.delete_no = gr.Button("Cancel", visible=False)

    def on_subscribe_public_events(self):
        """Subscribe to the declared public event of the app"""

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
                select(self._index._db_tables["Source"]).where(
                    self._index._db_tables["Source"].id == file_id
                )
            ).first()
            if source:
                session.delete(source[0])

            vs_ids, ds_ids = [], []
            index = session.execute(
                select(self._index._db_tables["Index"]).where(
                    self._index._db_tables["Index"].source_id == file_id
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
                inputs=None,
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
            ],
            outputs=[self.file_output],
        ).then(
            fn=self.list_file,
            inputs=None,
            outputs=[self.file_list_state, self.file_list],
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
            inputs=None,
            outputs=[self.file_list_state, self.file_list],
        )

    def index_fn(self, files, reindex: bool, settings):
        """Upload and index the files

        Args:
            files: the list of files to be uploaded
            reindex: whether to reindex the files
            selected_files: the list of files already selected
            settings: the settings of the app
        """
        gr.Info(f"Start indexing {len(files)} files...")

        # get the pipeline
        indexing_pipeline = self._index.get_indexing_pipeline(settings)

        result = indexing_pipeline(files, reindex=reindex)
        if result is None:
            gr.Info("Finish indexing")
            return
        output_nodes, _ = result
        gr.Info(f"Finish indexing into {len(output_nodes)} chunks")

        # download the file
        text = "\n\n".join([each.text for each in output_nodes])
        handler, file_path = tempfile.mkstemp(suffix=".txt")
        with open(file_path, "w") as f:
            f.write(text)
        os.close(handler)

        return gr.update(value=file_path, visible=True)

    def index_files_from_dir(self, folder_path, reindex, settings):
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

        return self.index_fn(files, reindex, settings)

    def list_file(self):
        Source = self._index._db_tables["Source"]
        with Session(engine) as session:
            statement = select(Source)
            results = [
                {
                    "id": each[0].id,
                    "name": each[0].name,
                    "size": each[0].size,
                    "text_length": each[0].text_length,
                    "date_created": each[0].date_created,
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


class FileSelector(BasePage):
    """File selector UI in the Chat page"""

    def __init__(self, app, index):
        super().__init__(app)
        self._index = index
        self.on_building_ui()

    def on_building_ui(self):
        self.selector = gr.Dropdown(
            label="Files",
            choices=[],
            multiselect=True,
            container=False,
            interactive=True,
        )

    def as_gradio_component(self):
        return self.selector

    def load_files(self, selected_files):
        options = []
        available_ids = []
        with Session(engine) as session:
            statement = select(self._index._db_tables["Source"])
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
            inputs=self.selector,
            outputs=[self.selector],
        )

    def on_subscribe_public_events(self):
        self._app.subscribe_event(
            name=f"onFileIndex{self._index.id}Changed",
            definition={
                "fn": self.load_files,
                "inputs": [self.selector],
                "outputs": [self.selector],
                "show_progress": "hidden",
            },
        )
