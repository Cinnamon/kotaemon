from enum import Enum
from typing import Literal

import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.base_models import BaseTag, TagScope, TagType
from ktem.db.models import Tag, engine
from ktem.index import IndexManager
from sqlmodel import Session, select

from kotaemon.base import Document
from kotaemon.storages import BaseDocumentStore

from .crud import TagCRUD
from .index import TagIndex
from .pipelines import MetaIndexPipeline

TAG_DISPLAY_COLUMNS = ["name", "scope", "type", "prompt"]
TRIAL_INPUT_TYPES = ["Content", "File"]


class TrialInputType(str, Enum):
    content = "Content"
    file = "File"

    @classmethod
    def get_types(cls) -> list[str]:
        return [elem.value for elem in cls]


class TagManagement(BasePage):
    def __init__(
        self,
        app,
    ):
        self._app = app
        self._tag_crud = TagCRUD(engine)
        self._index_manager: IndexManager = app.index_manager
        self.on_building_ui()

    def on_building_ui(self):
        self.build_view_panel()
        self.build_add_panel()

    def build_edit_panel(self):
        with gr.Column(visible=False) as self._selected_panel:
            self.selected_tag_name = gr.Textbox(value="", visible=False)
            with gr.Row():
                with gr.Column():
                    self.edit_name = gr.Textbox(
                        label="Meta tag name",
                        info="Must be unique and non-empty.",
                        interactive=False,
                    )
                    self.edit_prompt = gr.Textbox(
                        label="Prompt",
                        info="Description of the tag",
                        lines=5,
                    )
                    self.edit_scope = gr.Radio(
                        label="Scope",
                        choices=TagScope.get_types(),
                        value=TagScope.chunk.value,
                        info="Select the scope of the tag (file / chunk level)",
                    )
                    self.edit_type = gr.Radio(
                        label="Tag type",
                        choices=TagType.get_types(),
                        value=TagType.text.value,
                        info="Select the type of the tag",
                    )
                    self.edit_valid_classes = gr.Textbox(
                        label="Valid classes",
                        info="Enter valid classes for "
                        "classification (comma-separated)",
                        visible=False,
                    )

                with gr.Column():
                    self.edit_config = gr.Textbox(
                        label="Meta tag config",
                        info="Configuration of the tag",
                        lines=5,
                    )

        with gr.Row(visible=False) as self._selected_panel_btn:
            with gr.Column():
                self.btn_edit_save = gr.Button("Save", min_width=10, variant="primary")
            with gr.Column():
                self.btn_delete = gr.Button("Delete", min_width=10, variant="stop")
                with gr.Row():
                    self.btn_delete_yes = gr.Button(
                        "Confirm Delete",
                        variant="stop",
                        visible=False,
                        min_width=10,
                    )
                    self.btn_delete_no = gr.Button(
                        "Cancel", visible=False, min_width=10
                    )
            with gr.Column():
                self.btn_close = gr.Button("Close", min_width=10)

    def build_trial_panel(self):
        with gr.Row():
            with gr.Column(scale=1):
                self.trial_input_type = gr.Radio(
                    choices=TRIAL_INPUT_TYPES,
                    label="Choose type of input",
                    value=TRIAL_INPUT_TYPES[0],
                )

            with gr.Column(scale=1):
                self.trial_select_index = gr.Dropdown(
                    label="Meta index", interactive=True, multiselect=False
                )

            with gr.Column(scale=2):
                self.trial_select_index_name = gr.Textbox(
                    label="Index name",
                    interactive=False,
                )

        # Raw content input when trial mode is Content
        self.trial_raw_content = gr.Textbox(
            label="Enter content here",
            placeholder="Type your content here",
            visible=True,
            lines=5,
        )

        # Meta Index & File Select when trial mode is File
        self.trial_select_file = gr.Dropdown(
            label="Existing file", interactive=True, visible=False, multiselect=False
        )

        self.trial_gen_btn = gr.Button("Generate")

        self.trial_output_content = gr.HTML(label="Generated content")

    def build_view_panel(self):
        with gr.Tab(label="View"):
            self.tag_list = gr.DataFrame(
                headers=TAG_DISPLAY_COLUMNS,
                interactive=False,
                wrap=False,
            )

            self.build_edit_panel()

            with gr.Accordion("Trial", visible=False) as self._trial_panel:
                self.build_trial_panel()

    def build_add_panel(self):
        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Meta tag name",
                        info="Must be unique and non-empty.",
                    )
                    self.prompt = gr.Textbox(
                        label="Prompt",
                        info="Description of the tag",
                        lines=5,
                    )
                    self.scope = gr.Radio(
                        label="Scope",
                        choices=TagScope.get_types(),
                        value=TagScope.chunk.value,
                        info="Select the scope of the tag (file / chunk level)",
                    )
                    self.type = gr.Radio(
                        label="Tag type",
                        choices=TagType.get_types(),
                        value=TagType.text.value,
                        info="Select the type of the tag",
                    )
                    self.valid_classes = gr.Textbox(
                        label="Valid classes",
                        info="Enter valid classes for classification (comma-separated)",
                        visible=False,
                    )
                    self.btn_new = gr.Button("Add", variant="primary")

                with gr.Column(scale=3):
                    self.config = gr.Textbox(
                        label="Meta tag config",
                        info="Configuration of the tag",
                        lines=5,
                    )

    def list_tag(self) -> pd.DataFrame:
        tags: list[Tag] = self._tag_crud.list_all()
        if tags:
            tag_df = pd.DataFrame.from_records([dict(tag) for tag in tags])[
                TAG_DISPLAY_COLUMNS
            ]
        else:
            tag_df = pd.DataFrame(columns=TAG_DISPLAY_COLUMNS)
        return tag_df

    def list_indices(self) -> list[int]:
        items = []
        for i, item in enumerate(self._index_manager.indices):
            if not isinstance(item, TagIndex):
                continue
            items += [i]

        return items

    def list_files(self, index_id: int) -> list[str]:
        tag_index: TagIndex = self._index_manager.indices[index_id]

        source = tag_index._resources["Source"]
        file_names: list[str] = []
        with Session(engine) as session:
            statement = select(source)

            results = session.exec(statement).all()
            for result in results:
                file_names += [result.name]

        return file_names

    def get_chunks_by_file_name(
        self, index_id: int, file_name: str, n_chunk: int = -1
    ) -> list[Document]:
        tag_index: TagIndex = self._index_manager.indices[index_id]

        index = tag_index._resources["Index"]
        source = tag_index._resources["Source"]
        ds: BaseDocumentStore = tag_index._docstore

        with Session(engine) as session:
            statement = select(source).where(source.name.in_([file_name]))

            # Retrieve all satisfied file_ids
            results = session.exec(statement).all()
            file_id = [result.id for result in results]
            assert len(file_id) == 1, Exception(
                f"Invalid number of file_id for name: {file_name}. "
                f"Expect 1, got: {len(file_id)}"
            )
            file_id = file_id[0]

            # Retrieve chunk ids
            statement = select(index).where(index.source_id.in_([file_id]))
            results = session.exec(statement).all()
            chunk_ids = [r.target_id for r in results]

            docs: list[Document] = ds.get(chunk_ids)

            if n_chunk > 0:
                docs = docs[:n_chunk]

            return docs

    def create_tag(
        self,
        name: str,
        prompt: str,
        config: str,
        type: str,
        scope: str,
        valid_classes: str,
    ) -> pd.DataFrame:
        try:
            self._tag_crud.create(name, prompt, config, type, scope, valid_classes)
            gr.Info(f'Create tag "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to create tag {name}: {e}")

    def on_load_indices(self):
        list_indices = self.list_indices()

        default_value = list_indices[0] if len(list_indices) > 0 else None
        return gr.update(choices=list_indices, value=default_value)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
        )

        self._app.app.load(
            self.on_load_indices,
            inputs=[],
            outputs=[self.trial_select_index],
        )

    def broadcast_tag_updated_to_index(self, name: str):
        print("Broadcasting tag", name)

    def select_tag(self, tag_list, select_data: gr.SelectData):
        if select_data.value == "-" and select_data.index[0] == 0:
            gr.Info("No valid tag name is selected.")
            return ""

        if not select_data.selected:
            return ""

        return tag_list["name"][select_data.index[0]]

    def on_selected_tag_change(self, selected_tag_name):
        edit_tag_name = gr.update(value="")
        edit_tag_prompt = gr.update(value="")
        edit_tag_scope = gr.update(value="")
        edit_tag_type = gr.update(value="")
        edit_tag_config = gr.update(value="")
        edit_tag_meta = gr.update(value="")

        if selected_tag_name == "":
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
        else:
            _selected_panel = gr.update(visible=True)
            _selected_panel_btn = gr.update(visible=True)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)

            tag_obj: BaseTag | None = self._tag_crud.query_by_name(selected_tag_name)
            if tag_obj:
                edit_tag_name = tag_obj.name
                edit_tag_prompt = tag_obj.prompt
                edit_tag_scope = tag_obj.scope
                edit_tag_type = tag_obj.type
                edit_tag_config = tag_obj.config
                edit_tag_meta = tag_obj.meta.get("valid_classes", "")

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            # tag info
            edit_tag_name,
            edit_tag_prompt,
            edit_tag_scope,
            edit_tag_type,
            edit_tag_config,
            edit_tag_meta,
        )

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def delete_tag(self, selected_tag_name):
        result = self._tag_crud.delete_by_name(selected_tag_name)
        assert result, f"Failed to delete tag {selected_tag_name}"

        return ""

    def save_tag(
        self,
        name: str,
        prompt: str,
        scope: str,
        type: str,
        config: str,
        valid_classes: str,
    ):
        try:
            self._tag_crud.update_by_name(
                name=name,
                prompt=prompt,
                config=config,
                type=type,
                scope=scope,
                valid_classes=valid_classes,
            )
            gr.Info(f'Updated tag "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to edit tag {name}: {e}")

    def on_gen_click(
        self,
        index_id: int,
        selected_type: Literal["Content", "Files"],
        tag_prompt: str,
        tag_scope: str,
        tag_config: str,
        file_name: str,
        content: str,
        settings: dict,
        user_id: str,
    ) -> str:
        if index_id is None:
            raise gr.Error("Please select an index")

        tag_index: TagIndex = self._index_manager.indices[index_id]
        tag_index_pipeline: MetaIndexPipeline = tag_index.get_indexing_pipeline(
            settings, user_id
        )
        if selected_type in ["Content"]:
            if content is None or content == "":
                raise gr.Error("Please type your content")
            contents_in = [content]
        elif selected_type in ["File"]:
            if file_name is None:
                raise gr.Error("Please select file")

            chunks: list[Document] = self.get_chunks_by_file_name(
                index_id, file_name, n_chunk=-1
            )
            contents_in: list[str] = [chunk.text for chunk in chunks]

            if len(chunks) < 1:
                raise gr.Warning(f"No chunks in file-{file_name}. Return")

            if tag_scope == TagScope.file:
                contents_in = ["\n".join([elem for elem in contents_in])]

        else:
            raise Exception("Not implemented error!")

        html_result = (
            "<div style='max-height: 400px; overflow-y: auto;'>"
            "<table border='1' style='width:100%; border-collapse: collapse;'>"
        )
        html_result += (
            "<tr>"
            "<th>#</th>"
            "<th>Tag Prompt</th>"
            "<th>Content</th>"
            "<th>Generated Content</th>"
            "</tr>"
        )

        for i, content_in in enumerate(contents_in):
            generated_content = tag_index_pipeline.generate_with_llm(
                tag_prompt, content_in
            )

            html_result += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><details><summary>Tag prompt</summary>{tag_prompt}</details></td>"
                f"<td><details><summary>Input content</summary>{content_in}</details></td>"
                f"<td><details><summary>Generated content</summary>{generated_content}</details></td>"
                f"</tr>"
            )

        html_result += "</table></div>"

        return html_result

    def on_register_events(self):
        # Enable selection while user select classification
        self.type.change(
            lambda selected_type: gr.update(
                visible=(selected_type == TagType.classification.value)
            ),
            inputs=[self.type],
            outputs=[self.valid_classes],
        )
        self.edit_type.change(
            lambda selected_type: gr.update(
                visible=(selected_type == TagType.classification.value)
            ),
            inputs=[self.edit_type],
            outputs=[self.edit_valid_classes],
        )
        self.tag_list.select(
            self.select_tag,
            inputs=self.tag_list,
            outputs=[self.selected_tag_name],
            show_progress="hidden",
        )
        self.selected_tag_name.change(
            self.on_selected_tag_change,
            inputs=[self.selected_tag_name],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                # delete section
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                # tag info,
                self.edit_name,
                self.edit_prompt,
                self.edit_scope,
                self.edit_type,
                self.edit_config,
                self.edit_valid_classes,
            ],
            show_progress="hidden",
        ).success(
            lambda: gr.update(visible=True), inputs=[], outputs=[self._trial_panel]
        )

        # Add events
        self.btn_new.click(
            self.create_tag,
            inputs=[
                self.name,
                self.prompt,
                self.config,
                self.type,
                self.scope,
                self.valid_classes,
            ],
            outputs=None,
        ).success(self.list_tag, inputs=[], outputs=[self.tag_list]).success(
            self.broadcast_tag_updated_to_index,
            inputs=[
                self.name,
            ],
        ).then(
            fn=lambda: (
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
            ),
            outputs=[
                self.name,
                self.prompt,
                self.config,
                self.type,
                self.scope,
                self.valid_classes,
            ],
        )

        # Edit events
        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_tag,
            inputs=[self.selected_tag_name],
            outputs=[self.selected_tag_name],
            show_progress="hidden",
        ).then(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=False),
                gr.update(visible=False),
            ),
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_tag_name],
        )

        self.btn_edit_save.click(
            self.save_tag,
            inputs=[
                self.selected_tag_name,
                self.edit_prompt,
                self.edit_scope,
                self.edit_type,
                self.edit_config,
                self.edit_valid_classes,
            ],
            show_progress="hidden",
        ).then(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
        )

        # Trial events
        self.trial_input_type.change(
            lambda selected_type: (
                gr.update(visible=(selected_type == TRIAL_INPUT_TYPES[0])),
                gr.update(visible=(selected_type == TRIAL_INPUT_TYPES[1])),
            ),
            inputs=[self.trial_input_type],
            outputs=[self.trial_raw_content, self.trial_select_file],
        )

        self.trial_select_index.change(
            lambda selected_index: gr.update(choices=self.list_files(selected_index)),
            inputs=[self.trial_select_index],
            outputs=[self.trial_select_file],
        ).success(
            fn=lambda index_id: gr.update(
                value=self._index_manager.indices[index_id].name
            ),
            inputs=[self.trial_select_index],
            outputs=[self.trial_select_index_name],
        )

        self.trial_gen_btn.click(
            fn=self.on_gen_click,
            inputs=[
                self.trial_select_index,
                self.trial_input_type,
                self.edit_prompt,
                self.edit_scope,
                self.edit_config,
                self.trial_select_file,
                self.trial_raw_content,
                self._app.settings_state,
                self._app.user_id,
            ],
            outputs=[self.trial_output_content],
        )
