from copy import deepcopy

import gradio as gr
import pandas as pd
import yaml
from ktem.app import BasePage
from ktem.utils.file import YAMLNoDateSafeLoader

from .manager import IndexManager

DISPLAY_INDEX_COLUMNS = ["id", "name", "index type"]


# UGLY way to restart gradio server by updating atime
def update_current_module_atime():
    import os
    import time

    # Define the file path
    file_path = __file__
    print("Updating atime for", file_path)

    # Get the current time
    current_time = time.time()
    # Set the modified time (and access time) to the current time
    os.utime(file_path, (current_time, current_time))


def format_description(cls):
    user_settings = cls.get_admin_settings()
    params_lines = ["| Name | Default | Description |", "| --- | --- | --- |"]
    for key, value in user_settings.items():
        params_lines.append(
            f"| {key} | {value.get('value', '')} | {value.get('info', '')} |"
        )
    return f"{cls.__doc__}\n\n" + "\n".join(params_lines)


class IndexManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.manager: IndexManager = app.index_manager
        self.spec_desc_default = (
            "# Spec description\n\nSelect an index to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.index_list = gr.DataFrame(
                headers=DISPLAY_INDEX_COLUMNS,
                interactive=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_index_id = gr.Number(value=-1, visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_name = gr.Textbox(
                            label="Index name",
                        )
                        self.edit_spec = gr.Textbox(
                            label="Index config",
                            info="Admin configuration of the Index in YAML format",
                            lines=10,
                        )
                        self.spec_dropdown_field = gr.State(value=None)
                        self.spec_dropdown = gr.Dropdown(
                            visible=False,
                            multiselect=True,
                            allow_custom_value=False,
                            interactive=True,
                            value=[],
                        )

                        gr.Markdown(
                            "IMPORTANT: Changing or deleting the index will require "
                            "restarting the system. Some config settings will require "
                            "rebuilding the index for the index to work properly."
                        )
                        with gr.Row():
                            self.btn_edit_save = gr.Button(
                                "Save", min_width=10, variant="primary"
                            )
                            self.btn_delete = gr.Button(
                                "Delete", min_width=10, variant="stop"
                            )
                            with gr.Row(visible=False) as self._delete_confirm:
                                self.btn_delete_yes = gr.Button(
                                    "Confirm Delete",
                                    variant="stop",
                                    min_width=10,
                                )
                                self.btn_delete_no = gr.Button("Cancel", min_width=10)
                            self.btn_close = gr.Button("Close", min_width=10)

                        with gr.Row():
                            self.btn_rebuild = gr.Button("Rebuild Index", min_width=10)

                        with gr.Row():
                            self.rebuild_index_log = gr.TextArea(
                                label="Indexing progress",
                                visible=False,
                                lines=8,
                                max_lines=20,
                            )

                    with gr.Column():
                        self.edit_spec_desc = gr.Markdown("# Spec description")

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Index name",
                        info="Must be unique and non-empty.",
                    )
                    self.index_type = gr.Dropdown(label="Index type")
                    self.spec = gr.Textbox(
                        label="Specification",
                        info="Specification of the index in YAML format.",
                    )
                    gr.Markdown(
                        "<mark>Note</mark>: "
                        "After creating index, please restart the app"
                    )
                    self.btn_new = gr.Button("Add", variant="primary")

                with gr.Column(scale=3):
                    self.spec_desc = gr.Markdown(self.spec_desc_default)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_indices,
            inputs=[],
            outputs=[self.index_list],
        )
        self._app.app.load(
            lambda: gr.update(
                choices=[
                    (key.split(".")[-1], key) for key in self.manager.index_types.keys()
                ]
            ),
            outputs=[self.index_type],
        )

    def on_register_events(self):
        self.index_type.select(
            self.on_index_type_change,
            inputs=[self.index_type],
            outputs=[self.spec, self.spec_desc],
        )
        self.btn_new.click(
            self.create_index,
            inputs=[self.name, self.index_type, self.spec],
            outputs=None,
        ).success(self.list_indices, inputs=[], outputs=[self.index_list]).success(
            lambda: ("", None, "", self.spec_desc_default),
            outputs=[
                self.name,
                self.index_type,
                self.spec,
                self.spec_desc,
            ],
        ).success(
            update_current_module_atime
        )
        self.index_list.select(
            self.select_index,
            inputs=self.index_list,
            outputs=[self.selected_index_id],
            show_progress="hidden",
        )

        self.selected_index_id.change(
            self.on_selected_index_change,
            inputs=[self.selected_index_id],
            outputs=[
                self._selected_panel,
                # edit section
                self.edit_spec,
                self.edit_spec_desc,
                self.spec_dropdown,
                self.spec_dropdown_field,
                self.edit_name,
            ],
            show_progress="hidden",
        )
        self.btn_delete.click(
            lambda: (
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
            ),
            inputs=[],
            outputs=[
                self.btn_edit_save,
                self.btn_delete,
                self.btn_close,
                self._delete_confirm,
            ],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_index,
            inputs=[self.selected_index_id],
            outputs=[self.selected_index_id],
            show_progress="hidden",
        ).then(self.list_indices, inputs=[], outputs=[self.index_list],).success(
            update_current_module_atime
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=False),
            ),
            inputs=[],
            outputs=[
                self.btn_edit_save,
                self.btn_delete,
                self.btn_close,
                self._delete_confirm,
            ],
            show_progress="hidden",
        )
        self.btn_edit_save.click(
            self.update_index,
            inputs=[
                self.selected_index_id,
                self.edit_name,
                self.edit_spec,
                self.spec_dropdown,
                self.spec_dropdown_field,
            ],
            show_progress="hidden",
        ).then(
            self.list_indices,
            inputs=[],
            outputs=[self.index_list],
        )
        self.btn_close.click(
            lambda: -1,
            outputs=[self.selected_index_id],
        )
        self.btn_rebuild.click(
            lambda: gr.update(visible=True),
            outputs=[self.rebuild_index_log],
        ).then(
            self.rebuild_index,
            inputs=[
                self.selected_index_id,
                self._app.settings_state,
                self._app.user_id,
            ],
            outputs=[self.rebuild_index_log],
        )

    def on_index_type_change(self, index_type: str):
        """Update the spec description and pre-fill the default values

        Args:
            index_type: the name of the index type, this is usually the class name

        Returns:
            A tuple of the default spec and the description
        """
        index_type_cls = self.manager.index_types[index_type]
        required: dict = {
            key: value.get("value", None)
            for key, value in index_type_cls.get_admin_settings().items()
        }

        return yaml.dump(required, sort_keys=False), format_description(index_type_cls)

    def create_index(self, name: str, index_type: str, config: str):
        """Create the index

        Args:
            name: the name of the index
            index_type: the type of the index
            config: the expected config of the index
        """
        try:
            self.manager.build_index(
                name=name,
                config=yaml.load(config, Loader=YAMLNoDateSafeLoader),
                index_type=index_type,
            )
            gr.Info(f'Create index "{name}" successfully. Please restart the app!')
        except Exception as e:
            raise gr.Error(f"Failed to create Embedding model {name}: {e}")

    def list_indices(self):
        """List the indices constructed by the user"""
        items = []
        for item in self.manager.indices:
            record = {}
            for key, value in zip(
                DISPLAY_INDEX_COLUMNS, (item.id, item.name, item.__class__.__name__)
            ):
                record[key] = value
            items.append(record)

        if items:
            indices_list = pd.DataFrame.from_records(items)
        else:
            indices_list = pd.DataFrame.from_records(
                [{key: "-" for key in DISPLAY_INDEX_COLUMNS}]
            )

        return indices_list

    def select_index(self, index_list, ev: gr.SelectData) -> int:
        """Return the index id"""
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No index is constructed. Please create one first!")
            return -1

        if not ev.selected:
            return -1

        return int(index_list["id"][ev.index[0]])

    def on_selected_index_change(self, selected_index_id: int):
        """Show the relevant index as user selects it on the UI

        Args:
            selected_index_id: the id of the selected index
        """
        dropdown_values = []

        if selected_index_id == -1:
            _selected_panel = gr.update(visible=False)
            edit_spec = gr.update(value="")
            edit_spec_desc = gr.update(value="")
            edit_name = gr.update(value="")
            spec_dropdown = gr.update(visible=False)
            spec_dropdown_id = None
        else:
            _selected_panel = gr.update(visible=True)
            index = self.manager.info()[selected_index_id]
            edit_name = index.name

            # additional dropdown for spec description
            dropdown_settings = index.get_admin_settings_gradio()
            spec_dropdown_id = dropdown_settings.pop("id", None)

            # remove the dropdown field id from the config
            if spec_dropdown_id is not None:
                dropdown_values = index.config.get(spec_dropdown_id, None)

            # create a modified config without the dropdown field to display
            modified_index_config = deepcopy(index.config)
            modified_index_config.pop(spec_dropdown_id)

            edit_spec = yaml.dump(modified_index_config)
            edit_spec_desc = format_description(index.__class__)

            if dropdown_settings:
                dropdown_settings["visible"] = True
                dropdown_settings["value"] = dropdown_values
                spec_dropdown = gr.update(**dropdown_settings)
            else:
                spec_dropdown = gr.update(visible=False)

        return (
            _selected_panel,
            edit_spec,
            edit_spec_desc,
            spec_dropdown,
            spec_dropdown_id,
            edit_name,
        )

    def update_index(
        self,
        selected_index_id: int,
        name: str,
        config: str,
        tags: list[str],
        tag_id: str | None,
    ):
        try:
            spec = yaml.load(config, Loader=YAMLNoDateSafeLoader)
            if tag_id is not None:
                spec[tag_id] = tags
            self.manager.update_index(selected_index_id, name, spec)
            gr.Info(f'Update index "{name}" successfully. Please restart the app!')
        except Exception as e:
            raise gr.Error(f'Failed to save index "{name}": {e}')

    def delete_index(self, selected_index_id):
        try:
            self.manager.delete_index(selected_index_id)
            gr.Info("Delete index successfully. Please restart the app!")
        except Exception as e:
            gr.Warning(f"Fail to delete index: {e}")
            return selected_index_id

        return -1

    def rebuild_index(self, selected_index_id: int, settings, user_id):
        index = self.manager.info()[selected_index_id]
        indexing_pipeline = index.get_indexing_pipeline(settings, user_id)
        _iter = indexing_pipeline.rebuild_index()
        debugs = []

        try:
            while True:
                response = next(_iter)
                if response is None:
                    continue
                if response.channel == "debug":
                    debugs.append(response.text)
                yield "\n".join(debugs)
        except StopIteration:
            pass
