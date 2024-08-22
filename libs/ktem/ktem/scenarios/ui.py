import html
from typing import Generator

import gradio as gr
import pandas as pd
from ktem.app import BasePage
from ktem.db.base_models import ScenarioType
from ktem.db.models import Scenario, engine
from ktem.index import IndexManager
from ktem.index.file import FileIndex
from ktem.utils.render import Render

from kotaemon.base import Document

from ..tags import TagIndex
from ..tags.crud import ChunkTagIndexCRUD
from .crud import ScenarioCRUD, ScenarioValidator
from .pipelines import LLMScenarioPipeline

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
        self._indices: list[TagIndex | FileIndex] = self._index_manager.indices
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
                    self.base_prompt = gr.Textbox(
                        label="Base Prompt",
                        info="Base prompt to be used in the scenario",
                        lines=5,
                    )
                    self.scenario_type = gr.Dropdown(
                        label="Scenario Type",
                        choices=ScenarioType.get_types(),
                        value=ScenarioType.incident_search.value,
                        allow_custom_value=True,
                        info="Select the type of the scenario",
                    )

                    self.btn_new = gr.Button("Add", variant="primary")

                with gr.Column(scale=3):
                    self.specification = gr.Textbox(
                        label="Specification",
                        info="Detailed specification of the scenario",
                        lines=5,
                    )
                    self.retrieval_validator = gr.Textbox(
                        label="Retrieval Validator",
                        info="Logic for retrieval validation",
                        lines=5,
                    )

    def build_trial_panel(self):
        with gr.Column():
            with gr.Row():
                self.trial_input = gr.Textbox(label="Input parameter")
            with gr.Row() as self._trial_file_selection:
                self.trial_select_index = gr.Dropdown(
                    label="Index name",
                    interactive=True,
                    scale=1,
                )
                # Meta Index & File Select when trial mode is File
                self.trial_select_file = gr.Dropdown(
                    label="File name",
                    interactive=True,
                    multiselect=False,
                    scale=4,
                )

            with gr.Row():
                self.trial_gen_btn = gr.Button("Search")

        self.trial_output_content = gr.HTML(label="Generated content")

    def build_view_panel(self):
        with gr.Tab(label="View"):
            with gr.Accordion(
                "Filter",
                open=False,
            ):
                self.build_filter_panel()

            self.scenario_list = gr.DataFrame(
                headers=SCENARIO_DISPLAY_COLUMNS,
                interactive=False,
                wrap=False,
            )

            self.build_edit_panel()

    def build_filter_panel(self):
        with gr.Row():
            with gr.Column():
                self.filter_class_name = gr.Textbox(
                    label="Filter by scenario name",
                    placeholder="Enter class name",
                    lines=1,
                    show_label=True,
                )
                self.filter_reset = gr.Button("Reset", variant="secondary")

            with gr.Column():
                self.filter_types = gr.Dropdown(
                    label="Filter by class",
                    choices=ScenarioType.get_types(),
                    multiselect=True,
                    allow_custom_value=True,
                )

    def build_edit_panel(self):
        with gr.Column(visible=False) as self._selected_panel:
            self.selected_scenario_name = gr.Textbox(value="", visible=False)
            with gr.Row():
                with gr.Column():
                    self.edit_name = gr.Textbox(
                        label="Scenario Name",
                        info="Must be unique and non-empty.",
                        interactive=True,
                    )
                    self.edit_base_prompt = gr.Textbox(
                        label="Base Prompt",
                        info="Base prompt to be used in the scenario",
                        lines=5,
                        interactive=True,
                    )
                    self.edit_scenario_type = gr.Dropdown(
                        label="Scenario Type",
                        choices=ScenarioType.get_types(),
                        value=ScenarioType.incident_search.value,
                        info="Select the type of the scenario",
                        allow_custom_value=True,
                        interactive=True,
                    )

                with gr.Column():
                    self.edit_specification = gr.Textbox(
                        label="Specification",
                        info="Detailed specification of the scenario",
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

            with gr.Accordion("Scenario Preview", open=False) as self._trial_panel:
                self.build_trial_panel()

    def list_scenario(
        self, filter_name: str | None = None, filter_types: list[str] = []
    ) -> pd.DataFrame:
        scenarios: list[Scenario] = self._scenario_crud.list_all()
        if scenarios:
            filter_name = filter_name.strip().lower() if filter_name else None
            # Filter by class name
            if filter_name is not None and filter_name != "":
                scenarios = [
                    scenario
                    for scenario in scenarios
                    if filter_name in scenario.name.lower()
                ]

            # Filter by types
            if filter_types is not None and len(filter_types) > 0:
                scenarios = [
                    scenario
                    for scenario in scenarios
                    if scenario.scenario_type in filter_types
                ]

        if scenarios:
            scenario_df = pd.DataFrame.from_records(
                [dict(scenario) for scenario in scenarios]
            )[SCENARIO_DISPLAY_COLUMNS]
        else:
            scenario_df = pd.DataFrame.from_records(
                [{k: "-" for k in SCENARIO_DISPLAY_COLUMNS}]
            )
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

    def list_tag_indices(self) -> list[int]:
        items = []
        for idx, item in enumerate(self._indices):
            if not isinstance(item, TagIndex):
                continue
            items += [idx]

        return items

    def on_load_indices(self):
        list_indices = self.list_tag_indices()
        choices = [(self._indices[idx].name, idx) for idx in list_indices]

        default_value = list_indices[0] if len(list_indices) > 0 else None
        return gr.update(choices=choices, value=default_value)

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
            trial_panel,
        )

    def on_btn_delete_click(self):
        btn_delete = gr.update(visible=False)
        btn_delete_yes = gr.update(visible=True)
        btn_delete_no = gr.update(visible=True)

        return btn_delete, btn_delete_yes, btn_delete_no

    def delete_scenario(self, selected_scenario_name):
        result = self._scenario_crud.delete_by_name(selected_scenario_name)
        assert result, f"Failed to delete scenario {selected_scenario_name}"
        gr.Info(f'Deleted scenario "{selected_scenario_name}" successfully')

        return ""

    def save_scenario(
        self,
        name: str,
        new_name: str,
        scenario_type: str,
        specification: str,
        base_prompt: str,
        retrieval_validator: str,
    ):
        try:
            self._scenario_crud.update_by_name(
                name=name,
                new_name=new_name,
                scenario_type=scenario_type,
                specification=specification,
                base_prompt=base_prompt,
                retrieval_validator=retrieval_validator,
            )
            gr.Info(f'Updated scenario "{name}" successfully')
        except Exception as e:
            raise gr.Error(f"Failed to edit scenario {name}: {e}")

    def on_generate_click(
        self,
        index_id: int,
        scenario_name: str,
        scenario_prompt: str,
        file_name: str,
        input_param: str,
    ) -> Generator[str, None, None]:
        # get chunks from the selected index
        tag_index = self._indices[index_id]
        chunks: list[Document] = tag_index.get_chunks_by_file_name(
            file_name,
            n_chunk=50,
        )
        chunk_ids = [chunk.doc_id for chunk in chunks]
        chunk_tag_index_crud = ChunkTagIndexCRUD(engine)

        # get tagging information from the database
        doc_id_to_tags = chunk_tag_index_crud.query_by_chunk_ids(chunk_ids)

        # extract tags from the scenario prompt
        validator = ScenarioValidator(engine)
        tag_objs = validator.validate_tags(scenario_prompt)
        tag_names = [tag.name for tag in tag_objs]
        print("Using tags:", tag_names)

        query_pipeline = LLMScenarioPipeline()
        query_prompt = scenario_prompt
        tag_schema_str = "\n".join(
            [f"| {tag.name} | {tag.type} | {tag.meta} |" for tag in tag_objs]
        )
        search_query_dict = query_pipeline.run(query_prompt, tag_schema_str)

        if search_query_dict:
            search_tag_name, search_tag_value = list(search_query_dict.items())[0]
        else:
            search_tag_name, search_tag_value = None, None

        html_result = (
            "<div style='max-height: 600px; overflow-y: auto;'>"
            "<table border='1' style='width:100%; border-collapse: collapse;'>"
        )
        html_result += "<tr>" "<th>#</th>" "<th>Content</th>" "<th>Tags</th>" "</tr>"

        for idx, doc in enumerate(chunks):
            doc_id = doc.doc_id

            content = ""
            tag_content = ""

            # get title and chunk type
            title = html.escape(
                f"{doc.text[:100]}..." if len(doc.text) > 100 else doc.text
            )
            doc_type = doc.metadata.get("type", "text")

            # create display for tagging information
            cur_tag = doc_id_to_tags.get(doc_id, {})
            if cur_tag:
                tag_info: dict[str, str] = {}
                for _, tag in cur_tag.items():
                    is_tag_name_valid = (
                        search_tag_name
                        and tag["name"] == search_tag_name
                        and tag["content"] == search_tag_value
                    ) or (not search_tag_name and tag["name"] in tag_names)
                    if is_tag_name_valid:
                        tag_info[tag["name"]] = tag["content"][:100]

                # if tagging information exist, append to start of content
                if tag_info:
                    tag_content = "\n".join(
                        [
                            f"<div><mark><b>[{key}]</b>: {value}</mark></div>"
                            for key, value in tag_info.items()
                        ]
                    )
                else:
                    continue

            if doc_type == "text":
                content += html.escape(doc.text)
            elif doc_type == "table":
                content += Render.table(doc.text)
            elif doc_type == "image":
                content += Render.image(
                    url=doc.metadata.get("image_origin", ""), text=doc.text
                )

            header_prefix = ""
            if doc.metadata.get("page_label"):
                header_prefix += f"[Page {doc.metadata['page_label']}]"

            chunk_content = Render.collapsible(
                header=f"{header_prefix} {title}",
                content=content,
            )

            html_result += (
                "<tr>"
                f"<td>{idx + 1}</td>"
                f"<td>{chunk_content}</td>"
                "<td><details open='true'><summary><b>Tags</b>"
                f"</summary><mark>{tag_content}</mark></details></td>"
                "</tr>"
            )

            final_html_result = html_result + "</table></div>"
            yield final_html_result

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
                self._trial_panel,
            ],
            show_progress="hidden",
        ).success(
            lambda: gr.update(open=False),
            inputs=[],
            outputs=[self._trial_panel],
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
            inputs=[self.filter_class_name, self.filter_types],
            outputs=[self.scenario_list],
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
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )

        self.btn_delete_yes.click(
            self.delete_scenario,
            inputs=[self.selected_scenario_name],
            outputs=[self.selected_scenario_name],
            show_progress="hidden",
        ).success(self.list_scenario, inputs=[], outputs=[self.scenario_list])

        self.btn_edit_save.click(
            self.save_scenario,
            inputs=[
                self.selected_scenario_name,
                self.edit_name,
                self.edit_scenario_type,
                self.edit_specification,
                self.edit_base_prompt,
                self.edit_retrieval_validator,
            ],
            show_progress="hidden",
        ).then(
            self.list_scenario,
            inputs=[self.filter_class_name, self.filter_types],
            outputs=[self.scenario_list],
        )

        self.btn_close.click(
            lambda: "",
            outputs=[self.selected_scenario_name],
        )

        # Filter events
        gr.on(
            triggers=[
                self.filter_class_name.submit,
                self.filter_types.change,
            ],
            fn=self.list_scenario,
            inputs=[self.filter_class_name, self.filter_types],
            outputs=[self.scenario_list],
        ).success(
            lambda: gr.update(value=""),
            inputs=[],
            outputs=[self.selected_scenario_name],
        )

        self.filter_reset.click(
            fn=self.list_scenario, inputs=[], outputs=[self.scenario_list]
        ).success(
            lambda: (gr.update(value=""), gr.update(value=None)),
            inputs=[],
            outputs=[self.filter_class_name, self.filter_types],
        ).success(
            lambda: gr.update(value=""),
            inputs=[],
            outputs=[self.selected_scenario_name],
        )

        self.trial_select_index.change(
            lambda selected_index: gr.update(
                choices=self._indices[selected_index].list_files()
            ),
            inputs=[self.trial_select_index],
            outputs=[self.trial_select_file],
        )

        self.trial_gen_btn.click(
            fn=self.on_generate_click,
            inputs=[
                self.trial_select_index,
                self.edit_name,
                self.edit_base_prompt,
                self.trial_select_file,
                self.trial_input,
            ],
            outputs=[self.trial_output_content],
        )
