import gradio as gr
import pandas as pd
from sqlmodel import Session, select

from kotaemon.base import Document
from kotaemon.storages import BaseDocumentStore
from ktem.app import BasePage
from ktem.db.base_models import ScenarioType
from ktem.db.models import Scenario, engine
from ktem.index import IndexManager

from .crud import ScenarioCRUD
from ..tags import TagIndex

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
        self._index_manager: IndexManager = app.index_manager
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

    def build_trial_panel(self):
        # File select
        with gr.Row():
            with gr.Column(scale=1):
                self.trial_select_index = gr.Dropdown(
                    label="Meta index", interactive=True, multiselect=False
                )

            with gr.Column(scale=2):
                self.trial_select_index_name = gr.Textbox(
                    label="Index name",
                    interactive=False,
                )

            with gr.Column(scale=1):
                self.trial_select_file = gr.Dropdown(
                    label="Existing file",
                    interactive=True,
                    multiselect=True
                )

        # Input Description
        with gr.Row():
            with gr.Column(scale=1):
                self.trial_description = gr.Textbox(
                    label="Description",
                    placeholder="Type your description here",
                    lines=5
                )

        # Button
        with gr.Row():
            self.trial_gen_btn = gr.Button("Generate")

        # Output content
        with gr.Row():
            self.trial_output_content = gr.HTML(label="Generated content")

    def build_view_panel(self):
        with gr.Tab(label="View"):
            self.build_filter_panel()

            self.scenario_list = gr.DataFrame(
                headers=SCENARIO_DISPLAY_COLUMNS,
                interactive=False,
                wrap=False,
            )

            self.build_edit_panel()

            with gr.Accordion("Trial", visible=True) as self._trial_panel:
                self.build_trial_panel()

    def build_filter_panel(self):
        with gr.Row():
            with gr.Column(scale=1):
                self.filter_class_name = gr.Textbox(
                    label="Filter by class name",
                    placeholder="Enter class name",
                    lines=1,
                    show_label=True,
                )

            with gr.Column(scale=1):
                self.filter_types = gr.Dropdown(
                    label="Filter by class",
                    choices=ScenarioType.get_types(),
                    multiselect=True
                )

            with gr.Column(scale=1):
                self.filter_btn = gr.Button("Filter")
                self.filter_reset = gr.Button("Reset")

    def build_edit_panel(self):
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

    def list_scenario(self, name_pattern: str = "", types: list[str] = []) -> pd.DataFrame:
        scenarios: list[Scenario] = self._scenario_crud.list_all()
        if scenarios:
            # Filter by class name
            if name_pattern is not None and name_pattern != "":
                scenarios = [
                    scenario for scenario in scenarios
                    if name_pattern in scenario.name
                ]

            # Filter by types
            if types is not None and len(types) > 0:
                scenarios = [
                    scenario for scenario in scenarios
                    if scenario.scenario_type in ScenarioType.get_types()
                ]

            scenario_df = pd.DataFrame.from_records(
                [dict(scenario) for scenario in scenarios]
            )[SCENARIO_DISPLAY_COLUMNS]

        else:
            scenario_df = pd.DataFrame(columns=SCENARIO_DISPLAY_COLUMNS)
        return scenario_df

    def get_chunks_by_file_name(
        self, index_id: int, file_names: list[str], n_chunk: int = -1
    ) -> list[Document]:
        tag_index: TagIndex = self._index_manager.indices[index_id]

        index = tag_index._resources["Index"]
        source = tag_index._resources["Source"]
        ds: BaseDocumentStore = tag_index._docstore

        with Session(engine) as session:
            statement = select(source).where(source.name.in_(file_names))

            # Retrieve all satisfied file_ids
            results = session.exec(statement).all()
            file_ids = [result.id for result in results]

            # Retrieve chunk ids
            statement = select(index).where(index.source_id.in_(file_ids))
            results = session.exec(statement).all()
            chunk_ids = [r.target_id for r in results]

            docs: list[Document] = ds.get(chunk_ids)

            if n_chunk > 0:
                docs = docs[:n_chunk]

            return docs

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

    def list_indices(self) -> list[int]:
        items = []
        for i, item in enumerate(self._index_manager.indices):
            if not isinstance(item, TagIndex):
                continue
            items += [i]

        return items

    def list_files(self, index_id: int) -> list[str]:
        if index_id is None:
            raise gr.Warning("Meta index is None")

        tag_index: TagIndex = self._index_manager.indices[index_id]

        source = tag_index._resources["Source"]
        file_names: list[str] = []
        with Session(engine) as session:
            statement = select(source)

            results = session.exec(statement).all()
            for result in results:
                file_names += [result.name]

        return file_names

    def on_load_indices(self):
        list_indices = self.list_indices()

        default_value = list_indices[0] if len(list_indices) > 0 else None
        return gr.update(choices=list_indices, value=default_value)

    def _on_app_created(self):
        """Called when the app is created"""
        self._app.app.load(
            self.list_scenario,
            inputs=[],
            outputs=[self.scenario_list],
        )

        self._app.app.load(
            self.on_load_indices,
            inputs=[],
            outputs=[self.trial_select_index],
        ).success(
            fn=lambda index_id: gr.update(
                value=self._index_manager.indices[index_id].name
            ),
            inputs=[self.trial_select_index],
            outputs=[self.trial_select_index_name],
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
            trial_panel = gr.update(visible=False)
            _selected_panel = gr.update(visible=False)
            _selected_panel_btn = gr.update(visible=False)
            btn_delete = gr.update(visible=True)
            btn_delete_yes = gr.update(visible=False)
            btn_delete_no = gr.update(visible=False)
        else:
            trial_panel = gr.update(visible=True)
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
            # trial panel
            trial_panel
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

    def on_gen_click(
        self,
        index_id: int,
        description: str,
        file_names: list[str],
        scenario_prompt: str,
        scenario_validator: str,
    ):
        if index_id is None:
            raise gr.Error("Please select an index")

        chunks: list[Document] = self.get_chunks_by_file_name(
            index_id,
            file_names,
            n_chunk=-1
        )

        if len(chunks) < 1:
            raise gr.Warning(f"No chunks in files-{','.join(file_names)}. Return")

        contents_in: list[str] = [chunk.text for chunk in chunks]

        html_result = (
            "<div style='max-height: 400px; overflow-y: auto;'>"
            "<table border='1' style='width:100%; border-collapse: collapse;'>"
        )
        html_result += (
            "<tr>"
            "<th>#</th>"
            "<th>Chunk</th>"
            "<th>Relevant Score</th>"
            "</tr>"
        )

        for i, content_in in enumerate(contents_in):
            html_result += (
                f"<tr>"
                f"<td>{i}</td>"
                f"<td><details><summary>Chunk</summary>{content_in}</details></td>"
                f"<td>0.9</td>"
                f"</tr>"
            )

        html_result += "</table></div>"

        return html_result

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
                self._trial_panel
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
        ).success(
            self.list_scenario,
            inputs=[
                self.filter_class_name,
                self.filter_types
            ],
            outputs=[self.scenario_list]
        ).then(
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
            outputs=[
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no],
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
            inputs=[
                self.filter_class_name,
                self.filter_types
            ],
            outputs=[self.scenario_list],
        )

        # Filter events
        self.filter_btn.click(
            fn=self.list_scenario,
            inputs=[
                self.filter_class_name,
                self.filter_types
            ],
            outputs=[
                self.scenario_list
            ]
        ).success(
            lambda: gr.update(value=""),
            inputs=[],
            outputs=[self.selected_scenario_name]
        )

        self.filter_reset.click(
            fn=self.list_scenario,
            inputs=[],
            outputs=[
                self.scenario_list
            ]
        ).success(
            lambda: (
                gr.update(value=""),
                gr.update(value=None)
            ),
            inputs=[],
            outputs=[
                self.filter_class_name,
                self.filter_types
            ]
        )

        # Trial events
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
                self.trial_description,
                self.trial_select_file,
                self.edit_base_prompt,
                self.edit_retrieval_validator
            ],
            outputs=[
                self.trial_output_content
            ]
        )


