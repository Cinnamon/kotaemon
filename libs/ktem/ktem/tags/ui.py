import json
from copy import deepcopy

import gradio as gr
import pandas as pd

from ktem.app import BasePage
from ktem.db.models import engine
from ktem.db.base_models import TagType

from .crud import TagCRUD
from .index import MetaIndex
from .pipelines import MetaIndexPipeline


class TagManagement(BasePage):
    def __init__(
        self,
        app,
        meta_index: MetaIndex | None = None,
        tag_crud: TagCRUD | None = None
    ):
        self._app = app
        self.spec_desc_default = (
            "# Spec description\n\nSelect an index to view the spec description."
        )
        if tag_crud is None:
            tag_crud = TagCRUD(engine)
        self._tag_crud = tag_crud

        if meta_index is None:
            meta_index = MetaIndex(
                self._app,
                id="1",
                name="Tag",
                config={}
            )
            meta_index.on_start()

        self._meta_index = meta_index
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.tag_list = gr.DataFrame(
                headers=["name", "prompt", "type", "meta"],
                interactive=False,
            )

            _visible = False
            with gr.Column(visible=_visible) as self._selected_panel:
                self.selected_tag_name = gr.Textbox(value="", visible=_visible)
                with gr.Row():
                    with gr.Column():
                        self.edit_name = gr.Textbox(
                            label="Meta tag name",
                            info="Must be unique and non-empty.",
                            interactive=False
                        )
                        self.edit_prompt = gr.Textbox(
                            label="Prompt",
                            info="Description of the tag"
                        )
                        self.edit_type = gr.Radio(
                            label="Tag Type",
                            choices=TagType.get_types(),
                            value=TagType.text.value,
                            info="Select the type of the tag",
                        )
                        self.edit_valid_classes = gr.Textbox(
                            label="Valid Classes",
                            info="Enter valid classes for classification (comma-separated)",
                            visible=False
                        )

                        with gr.Row(visible=_visible) as self._selected_panel_btn:
                            with gr.Column():
                                self.btn_edit_save = gr.Button(
                                    "Save", min_width=10, variant="primary"
                                )
                            with gr.Column():
                                self.btn_delete = gr.Button(
                                    "Delete", min_width=10, variant="stop"
                                )
                                with gr.Row():
                                    self.btn_delete_yes = gr.Button(
                                        "Confirm Delete",
                                        variant="stop",
                                        visible=_visible,
                                        min_width=10,
                                    )
                                    self.btn_delete_no = gr.Button(
                                        "Cancel", visible=_visible, min_width=10
                                    )
                            with gr.Column():
                                self.btn_close = gr.Button("Close", min_width=10)

                    with gr.Column():
                        self.edit_config = gr.Textbox(
                            label="Meta tag config",
                            info="Configuration of the tag",
                        )

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Meta tag name",
                        info="Must be unique and non-empty.",
                    )

                    self.prompt = gr.Textbox(
                        label="Prompt",
                        info="Description of the tag"
                    )

                    self.type = gr.Radio(
                        label="Tag Type",
                        choices=TagType.get_types(),
                        value=TagType.text.value,
                        info="Select the type of the tag",
                    )

                    self.valid_classes = gr.Textbox(
                        label="Valid Classes",
                        info="Enter valid classes for classification (comma-separated)",
                        visible=False,
                    )

                    self.btn_new = gr.Button("Add", variant="primary")

                with gr.Column(scale=3):
                    self.config = gr.Textbox(
                        label="Meta tag config",
                        info="Configuration of the tag",
                    )

    def list_tag(self) -> pd.DataFrame:
        tags: list[dict] = self._tag_crud.list_all()
        filtered_tags: list[dict] = []

        if len(tags) > 0:
            for tag in tags:
                filtered_tags += [{
                    "name": tag['name'],
                    "prompt": tag['prompt'],
                    "type": tag['type'],
                    "meta": json.dumps(tag['meta'])
                }]
        else:
            filtered_tags = [
                {
                    "name": "-",
                    "prompt": "-",
                    "type": "-",
                    "meta": "-"
                }
            ]

        # TODO: only extract necessary columns
        return pd.DataFrame.from_records(filtered_tags)

    def select_tag(self, tag_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No embedding model is loaded. Please add first")
            return ""

        if not ev.selected:
            return ""

        return tag_list["name"][ev.index[0]]

    def create_tag(
        self,
        name: str,
        prompt: str,
        config: str,
        type: str,
        valid_classes: str
    ) -> pd.DataFrame:
        try:
            self._tag_crud.create(
                name,
                prompt,
                config,
                type,
                valid_classes
            )
            gr.Info(f'Create tag "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to create tag {name}: {e}")

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
        )

    def broadcast_tag(self, name: str, user_id: str):
        tag = self._tag_crud.query_by_name(name)

        if tag is None:
            return

        tag_id = tag['id']
        tag_prompt = tag['prompt']

        indexing_pipeline: MetaIndexPipeline = self._meta_index.get_indexing_pipeline(
            user_id=user_id,
        )

        indexing_pipeline.run(
            tag_prompts=[tag_prompt],
            tag_ids=[tag_id],
        )

    def on_selected_tag_change(self, selected_tag_name):
        edit_tag_name = gr.update(value="")
        edit_tag_prompt = gr.update(value="")
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

            # Query information by name
            tag_info: dict | None = self._tag_crud.query_by_name(selected_tag_name)
            if tag_info:
                edit_tag_name = tag_info['name']
                edit_tag_prompt = tag_info['prompt']
                edit_tag_type = tag_info['type']
                edit_tag_config = tag_info['config']
                edit_tag_meta = tag_info['meta'].get("valid_classes", "")

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            edit_tag_name,
            edit_tag_prompt,
            edit_tag_type,
            edit_tag_config,
            edit_tag_meta
        )

    def save_tag(
        self,
        name: str,
        prompt: str,
        type: str,
        config: str,
        valid_classes: str
    ):
        try:
            self._tag_crud.update_by_name(
                name=name,
                prompt=prompt,
                config=config,
                type=type,
                valid_classes=valid_classes
            )
            gr.Info(f'Updated tag "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to edit tag {name}: {e}")

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
            outputs=[self.edit_valid_classes]
        )

        self.btn_new.click(
            self.create_tag,
            inputs=[
                self.name,
                self.prompt,
                self.config,
                self.type,
                self.valid_classes
            ],
            outputs=None
        ).success(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list]
        ).success(
            self.broadcast_tag,
            inputs=[
                self.name,
                self._app.user_id
            ],
            outputs=[]
        )

        self.tag_list.select(
            self.select_tag,
            inputs=[self.tag_list],
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
                # edit section
                self.edit_name,
                self.edit_prompt,
                self.edit_type,
                self.edit_config,
                self.edit_valid_classes
            ],
            show_progress="hidden",
        )

        self.btn_edit_save.click(
            self.save_tag,
            inputs=[
                self.selected_tag_name,
                self.edit_prompt,
                self.edit_type,
                self.edit_config,
                self.edit_valid_classes
            ],
            show_progress="hidden",
        ).then(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
        )

        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_tag_name],
        )

