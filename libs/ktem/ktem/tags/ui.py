import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.base_models import BaseTag, TagScope, TagType
from ktem.db.models import Tag, engine

from .crud import TagCRUD

TAG_DISPLAY_COLUMNS = ["name", "scope", "type", "prompt", "id"]


class TagManagement(BasePage):
    def __init__(
        self,
        app,
    ):
        self._app = app
        self._tag_crud = TagCRUD(engine)
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.tag_list = gr.DataFrame(
                headers=TAG_DISPLAY_COLUMNS,
                column_widths=["25%", "10%", "15%", "45%", "5%"],
                interactive=False,
                wrap=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_tag_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_name = gr.Textbox(
                            label="Meta tag name",
                            info="Must be unique and non-empty.",
                            interactive=True,
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
                        with gr.Row(visible=False) as self._selected_panel_btn:
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
                                        visible=False,
                                        min_width=10,
                                    )
                                    self.btn_delete_no = gr.Button(
                                        "Cancel", visible=False, min_width=10
                                    )
                            with gr.Column():
                                self.btn_close = gr.Button("Close", min_width=10)

                    with gr.Column():
                        self.edit_config = gr.Textbox(
                            label="Meta tag config",
                            info="Configuration of the tag",
                            lines=5,
                        )

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Meta tag name",
                        info="Must be unique and non-empty.",
                        interactive=True,
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

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_tag,
            inputs=[],
            outputs=[self.tag_list],
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
        try:
            self._tag_crud.delete_by_name(selected_tag_name)
            gr.Info(f'Deleted tag "{selected_tag_name}" successfully')
            selected_tag_name = ""
        except Exception as e:
            raise gr.Error(f"Failed to delete tag {selected_tag_name}: {e}")

        return selected_tag_name

    def save_tag(
        self,
        name: str,
        new_name: str,
        prompt: str,
        scope: str,
        type: str,
        config: str,
        valid_classes: str,
    ):
        try:
            self._tag_crud.update_by_name(
                name=name,
                new_name=new_name,
                prompt=prompt,
                config=config,
                type=type,
                scope=scope,
                valid_classes=valid_classes,
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
        )

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
                self.edit_name,
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
