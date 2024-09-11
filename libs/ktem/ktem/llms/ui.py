from copy import deepcopy

import gradio as gr
import pandas as pd
import yaml
from ktem.app import BasePage
from ktem.utils.file import YAMLNoDateSafeLoader
from theflow.utils.modules import deserialize

from .manager import llms


def format_description(cls):
    params = cls.describe()["params"]
    params_lines = ["| Name | Type | Description |", "| --- | --- | --- |"]
    for key, value in params.items():
        if isinstance(value["auto_callback"], str):
            continue
        params_lines.append(f"| {key} | {value['type']} | {value['help']} |")
    return f"{cls.__doc__}\n\n" + "\n".join(params_lines)


class LLMManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.spec_desc_default = (
            "# Spec description\n\nSelect an LLM to view the spec description."
        )
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.llm_list = gr.DataFrame(
                headers=["name", "vendor", "default"],
                interactive=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_llm_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_default = gr.Checkbox(
                            label="Set default",
                            info=(
                                "Set this LLM as default. If no default is set, a "
                                "random LLM will be used."
                            ),
                        )
                        self.edit_spec = gr.Textbox(
                            label="Specification",
                            info="Specification of the LLM in YAML format",
                            lines=10,
                        )

                        with gr.Accordion(
                            label="Test connection", visible=False, open=False
                        ) as self._check_connection_panel:
                            with gr.Row():
                                with gr.Column(scale=4):
                                    self.connection_logs = gr.HTML("Logs")

                                with gr.Column(scale=1):
                                    self.btn_test_connection = gr.Button(
                                        "Test",
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
                        self.edit_spec_desc = gr.Markdown("# Spec description")

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="LLM name",
                        info=(
                            "Must be unique. The name will be used to identify the LLM."
                        ),
                    )
                    self.llm_choices = gr.Dropdown(
                        label="LLM vendors",
                        info=(
                            "Choose the vendor for the LLM. Each vendor has different "
                            "specification."
                        ),
                    )
                    self.spec = gr.Textbox(
                        label="Specification",
                        info="Specification of the LLM in YAML format",
                    )
                    self.default = gr.Checkbox(
                        label="Set default",
                        info=(
                            "Set this LLM as default. This default LLM will be used "
                            "by default across the application."
                        ),
                    )
                    self.btn_new = gr.Button("Add LLM", variant="primary")

                with gr.Column(scale=3):
                    self.spec_desc = gr.Markdown(self.spec_desc_default)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
        )
        self._app.app.load(
            lambda: gr.update(choices=list(llms.vendors().keys())),
            outputs=[self.llm_choices],
        )

    def on_llm_vendor_change(self, vendor):
        vendor = llms.vendors()[vendor]

        required: dict = {}
        desc = vendor.describe()
        for key, value in desc["params"].items():
            if value.get("required", False):
                required[key] = None

        return yaml.dump(required), format_description(vendor)

    def on_register_events(self):
        self.llm_choices.select(
            self.on_llm_vendor_change,
            inputs=[self.llm_choices],
            outputs=[self.spec, self.spec_desc],
        )
        self.btn_new.click(
            self.create_llm,
            inputs=[self.name, self.llm_choices, self.spec, self.default],
            outputs=[],
        ).success(self.list_llms, inputs=[], outputs=[self.llm_list]).success(
            lambda: ("", None, "", False, self.spec_desc_default),
            outputs=[
                self.name,
                self.llm_choices,
                self.spec,
                self.default,
                self.spec_desc,
            ],
        )
        self.llm_list.select(
            self.select_llm,
            inputs=self.llm_list,
            outputs=[self.selected_llm_name],
            show_progress="hidden",
        )
        self.selected_llm_name.change(
            self.on_selected_llm_change,
            inputs=[self.selected_llm_name],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                # delete section
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                # edit section
                self.edit_spec,
                self.edit_spec_desc,
                self.edit_default,
                # check connection panel
                self._check_connection_panel,
            ],
            show_progress="hidden",
        ).success(lambda: gr.update(value=""), outputs=[self.connection_logs])

        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_llm,
            inputs=[self.selected_llm_name],
            outputs=[self.selected_llm_name],
            show_progress="hidden",
        ).then(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
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
        self.btn_edit_save.click(
            self.save_llm,
            inputs=[
                self.selected_llm_name,
                self.edit_default,
                self.edit_spec,
            ],
            show_progress="hidden",
        ).then(
            self.list_llms,
            inputs=[],
            outputs=[self.llm_list],
        )
        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_llm_name],
        )

        self.btn_test_connection.click(
            self.check_connection,
            inputs=[self.selected_llm_name, self.edit_spec],
            outputs=[self.connection_logs],
        )

    def create_llm(self, name, choices, spec, default):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            spec["__type__"] = (
                llms.vendors()[choices].__module__
                + "."
                + llms.vendors()[choices].__qualname__
            )

            llms.add(name, spec=spec, default=default)
            gr.Info(f"LLM {name} created successfully")
        except Exception as e:
            raise gr.Error(f"Failed to create LLM {name}: {e}")

    def list_llms(self):
        """List the LLMs"""
        items = []
        for item in llms.info().values():
            record = {}
            record["name"] = item["name"]
            record["vendor"] = item["spec"].get("__type__", "-").split(".")[-1]
            record["default"] = item["default"]
            items.append(record)

        if items:
            llm_list = pd.DataFrame.from_records(items)
        else:
            llm_list = pd.DataFrame.from_records(
                [{"name": "-", "vendor": "-", "default": "-"}]
            )

        return llm_list

    def select_llm(self, llm_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No LLM is loaded. Please add LLM first")
            return ""

        if not ev.selected:
            return ""

        return llm_list["name"][ev.index[0]]

    def on_selected_llm_change(self, selected_llm_name):
        if selected_llm_name == "":
            _check_connection_panel = gr.update(visible=False)
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
            edit_spec = gr.update(value="")
            edit_spec_desc = gr.update(value="")
            edit_default = gr.update(value=False)
        else:
            _check_connection_panel = gr.update(visible=True)
            _selected_panel = gr.update(visible=True)
            _selected_panel_btn = gr.update(visible=True)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)

            info = deepcopy(llms.info()[selected_llm_name])
            vendor_str = info["spec"].pop("__type__", "-").split(".")[-1]
            vendor = llms.vendors()[vendor_str]

            edit_spec = yaml.dump(info["spec"])
            edit_spec_desc = format_description(vendor)
            edit_default = info["default"]

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            edit_spec,
            edit_spec_desc,
            edit_default,
            _check_connection_panel,
        )

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def check_connection(self, selected_llm_name: str, selected_spec):
        log_content: str = ""

        try:
            log_content += f"- Testing model: {selected_llm_name}<br>"
            yield log_content

            # Parse content & init model
            info = deepcopy(llms.info()[selected_llm_name])

            # Parse content & create dummy embedding
            spec = yaml.load(selected_spec, Loader=YAMLNoDateSafeLoader)
            info["spec"].update(spec)

            llm = deserialize(info["spec"], safe=False)

            if llm is None:
                raise Exception(f"Can not found model: {selected_llm_name}")

            log_content += "- Sending a message `Hi`<br>"
            yield log_content
            respond = llm("Hi")

            log_content += (
                f"<mark style='background: yellow; color: red'>- Connection success. "
                f"Got response:\n {respond}</mark><br>"
            )
            yield log_content

            gr.Info(f"LLM {selected_llm_name} connect successfully")
        except Exception as e:
            log_content += (
                f"<mark style='color: yellow; background: red'>- Connection failed. "
                f"Got error:\n {e}</mark>"
            )
            yield log_content

        return log_content

    def save_llm(self, selected_llm_name, default, spec):
        try:
            spec = yaml.load(spec, Loader=YAMLNoDateSafeLoader)
            spec["__type__"] = llms.info()[selected_llm_name]["spec"]["__type__"]
            llms.update(selected_llm_name, spec=spec, default=default)
            gr.Info(f"LLM {selected_llm_name} saved successfully")
        except Exception as e:
            raise gr.Error(f"Failed to save LLM {selected_llm_name}: {e}")

    def delete_llm(self, selected_llm_name):
        try:
            llms.delete(selected_llm_name)
        except Exception as e:
            gr.Error(f"Failed to delete LLM {selected_llm_name}: {e}")
            return selected_llm_name

        return ""
