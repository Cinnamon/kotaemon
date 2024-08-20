import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.base_models import ScenarioType
from ktem.db.models import Scenario, engine

from .crud import ScenarioCRUD

SCENARIO_DISPLAY_COLUMNS = [
    "name",
    "scenario_type",
    "specification",
    "base_prompt",
    "retrieval_validator",
]


class ScenarioManagement(BasePage):
    def __init__(
        self,
        app,
    ):
        self._app = app
        self._scenario_crud = ScenarioCRUD(engine)
        self.on_building_ui()

    def on_building_ui(self):
        self.build_view_panel()
        self.build_add_panel()

    def build_add_panel(self):
        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.name = gr.Textbox(
                        label="Scenario Name",
                        info="Must be unique and non-empty.",
                    )
                    self.specification = gr.Textbox(
                        label="Specification",
                        info="Detailed specification of the scenario",
                        lines=5,
                    )
                    self.scenario_type = gr.Dropdown(
                        label="Scenario Type",
                        choices=ScenarioType.get_types(),
                        value=ScenarioType.incident_search.value,
                        info="Select the type of the scenario",
                    )

                    self.btn_new = gr.Button("Add", variant="primary")

                with gr.Column(scale=3):
                    self.base_prompt = gr.Textbox(
                        label="Base Prompt",
                        info="Base prompt to be used in the scenario",
                        lines=5,
                    )

                    self.retrieval_validator = gr.Textbox(
                        label="Retrieval Validator",
                        info="Logic for retrieval validation",
                        lines=5,
                    )

    def build_view_panel(self):
        with gr.Tab(label="View"):
            self.scenario_list = gr.DataFrame(
                headers=SCENARIO_DISPLAY_COLUMNS,
                interactive=False,
                wrap=False,
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_scenario_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_name = gr.Textbox(
                            label="Scenario Name",
                            info="Must be unique and non-empty.",
                            interactive=False,
                        )
                        self.edit_specification = gr.Textbox(
                            label="Specification",
                            info="Detailed specification of the scenario",
                            lines=5,
                            interactive=True,
                        )

                        self.edit_scenario_type = gr.Dropdown(
                            label="Scenario Type",
                            choices=ScenarioType.get_types(),
                            value=ScenarioType.incident_search.value,
                            info="Select the type of the scenario",
                            interactive=True,
                        )

                    with gr.Column():
                        self.edit_base_prompt = gr.Textbox(
                            label="Base Prompt",
                            info="Base prompt to be used in the scenario",
                            lines=5,
                            interactive=True,
                        )
                        self.edit_retrieval_validator = gr.Textbox(
                            label="Retrieval Validator",
                            info="Logic for retrieval validation",
                            lines=5,
                            interactive=True,
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

    def list_scenario(self) -> pd.DataFrame:
        scenarios: list[Scenario] = self._scenario_crud.list_all()
        if scenarios:
            scenario_df = pd.DataFrame.from_records(
                [dict(scenario) for scenario in scenarios]
            )[SCENARIO_DISPLAY_COLUMNS]
        else:
            scenario_df = pd.DataFrame(columns=SCENARIO_DISPLAY_COLUMNS)
        return scenario_df

    def create_scenario(
        self,
        name: str,
        scenario_type: str,
        specification: str,
        base_prompt: str,
        retrieval_validator: str,
    ) -> pd.DataFrame:
        try:
            self._scenario_crud.create(
                name, scenario_type, specification, base_prompt, retrieval_validator
            )
            gr.Info(f'Create scenario "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to create scenario {name}: {e}")

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_scenario,
            inputs=[],
            outputs=[self.scenario_list],
        )

    def select_scenario(self, scenario_list, select_data: gr.SelectData):
        if select_data.value == "-" and select_data.index[0] == 0:
            gr.Info("No valid scenario name is selected.")
            return ""

        if not select_data.selected:
            return ""

        return scenario_list["name"][select_data.index[0]]

    def on_selected_scenario_change(self, selected_scenario_name):
        edit_scenario_name = gr.update(value="")
        edit_specification = gr.update(value="")
        edit_scenario_type = gr.update(value="")
        edit_base_prompt = gr.update(value="")
        edit_retrieval_validator = gr.update(value="")

        if selected_scenario_name == "":
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

            scenario_obj: Scenario | None = self._scenario_crud.query_by_name(
                selected_scenario_name
            )
            if scenario_obj:
                edit_scenario_name = scenario_obj.name
                edit_specification = scenario_obj.specification
                edit_scenario_type = scenario_obj.scenario_type
                edit_base_prompt = scenario_obj.base_prompt
                edit_retrieval_validator = scenario_obj.retrieval_validator

        return (
            _selected_panel,
            _selected_panel_btn,
            btn_delete,
            btn_delete_yes,
            btn_delete_no,
            # scenario info
            edit_scenario_name,
            edit_specification,
            edit_scenario_type,
            edit_base_prompt,
            edit_retrieval_validator,
        )

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def delete_scenario(self, selected_scenario_name):
        result = self._scenario_crud.delete_by_name(selected_scenario_name)
        assert result, f"Failed to delete scenario {selected_scenario_name}"

        return ""

    def save_scenario(
        self,
        name: str,
        scenario_type: str,
        specification: str,
        base_prompt: str,
        retrieval_validator: str,
    ):
        try:
            self._scenario_crud.update_by_name(
                name=name,
                scenario_type=scenario_type,
                specification=specification,
                base_prompt=base_prompt,
                retrieval_validator=retrieval_validator,
            )
            gr.Info(f'Updated scenario "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to edit scenario {name}: {e}")

    def on_register_events(self):
        self.scenario_list.select(
            self.select_scenario,
            inputs=self.scenario_list,
            outputs=[self.selected_scenario_name],
            show_progress="hidden",
        )

        self.selected_scenario_name.change(
            self.on_selected_scenario_change,
            inputs=[self.selected_scenario_name],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                # delete section
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                # scenario info,
                self.edit_name,
                self.edit_specification,
                self.edit_scenario_type,
                self.edit_base_prompt,
                self.edit_retrieval_validator,
            ],
            show_progress="hidden",
        )

        self.btn_new.click(
            self.create_scenario,
            inputs=[
                self.name,
                self.scenario_type,
                self.specification,
                self.base_prompt,
                self.retrieval_validator,
            ],
            outputs=None,
        ).success(self.list_scenario, inputs=[], outputs=[self.scenario_list]).then(
            fn=lambda: (
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
            ),
            outputs=[
                self.name,
                self.specification,
                self.scenario_type,
                self.base_prompt,
                self.retrieval_validator,
            ],
        )

        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )

        self.btn_delete_yes.click(
            self.delete_scenario,
            inputs=[self.selected_scenario_name],
            outputs=[self.selected_scenario_name],
            show_progress="hidden",
        )

        self.btn_edit_save.click(
            self.save_scenario,
            inputs=[
                self.edit_name,
                self.edit_scenario_type,
                self.edit_specification,
                self.edit_base_prompt,
                self.edit_retrieval_validator,
            ],
            show_progress="hidden",
        ).then(
            self.list_scenario,
            inputs=[],
            outputs=[self.scenario_list],
        )
