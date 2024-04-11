import gradio as gr
import pandas as pd
import yaml
from ktem.app import BasePage


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
        self.manager = app.index_manager
        self.spec_desc_default = (
            "# Spec description\n\nSelect an index to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.index_list = gr.DataFrame(
                headers=["ID", "Name", "Index Type"],
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
                            label="Specification",
                            info="Specification of the Index in YAML format",
                            lines=10,
                        )

                        gr.Markdown(
                            "IMPORTANT: Changing or deleting the name or "
                            "specification of the index will require restarting "
                            "the system. Some settings will require rebuilding "
                            "the index."
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

                    with gr.Column():
                        self.edit_spec_desc = gr.Markdown("# Spec description")

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_indices,
            inputs=None,
            outputs=[self.index_list],
        )

    def on_register_events(self):
        self.index_list.select(
            self.select_index,
            inputs=self.index_list,
            outputs=[self.selected_index_id],
            show_progress="hidden",
        )

        self.selected_index_id.change(
            self.on_change_selected_index,
            inputs=[self.selected_index_id],
            outputs=[
                self._selected_panel,
                # edit section
                self.edit_spec,
                self.edit_spec_desc,
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
            inputs=None,
            outputs=[
                self.btn_edit_save,
                self.btn_delete,
                self.btn_close,
                self._delete_confirm,
            ],
            show_progress="hidden",
        )
        self.btn_delete_no.click(
            lambda: (
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(visible=False),
            ),
            inputs=None,
            outputs=[
                self.btn_edit_save,
                self.btn_delete,
                self.btn_close,
                self._delete_confirm,
            ],
            show_progress="hidden",
        )
        self.btn_close.click(
            lambda: -1,
            outputs=[self.selected_index_id],
        )

    def list_indices(self):
        """List the indices constructed by the user"""
        items = []
        for item in self.manager.indices:
            record = {}
            record["ID"] = item.id
            record["Name"] = item.name
            record["Index Type"] = item.__class__.__name__
            items.append(record)

        if items:
            indices_list = pd.DataFrame.from_records(items)
        else:
            indices_list = pd.DataFrame.from_records(
                [{"ID": "-", "Name": "-", "Index Type": "-"}]
            )

        return indices_list

    def select_index(self, index_list, ev: gr.SelectData) -> int:
        """Return the index id"""
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No index is constructed. Please create one first!")
            return -1

        if not ev.selected:
            return -1

        return int(index_list["ID"][ev.index[0]])

    def on_change_selected_index(self, selected_index_id: int):
        if selected_index_id == -1:
            _selected_panel = gr.update(visible=False)
            edit_spec = gr.update(value="")
            edit_spec_desc = gr.update(value="")
            edit_name = gr.update(value="")
        else:
            _selected_panel = gr.update(visible=True)
            index = self.manager.info()[selected_index_id]
            edit_spec = yaml.dump(index.config)
            edit_spec_desc = format_description(index.__class__)
            edit_name = index.name

        return (
            _selected_panel,
            edit_spec,
            edit_spec_desc,
            edit_name,
        )
