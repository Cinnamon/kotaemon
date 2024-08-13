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
                name="MetaIndex",
                config={}
            )
            meta_index.on_start()
        self._meta_index = meta_index
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.tag_list = gr.DataFrame(
                headers=["ID", "Name", "Prompt"],
                interactive=False,
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

        # TODO: only extract necessary columns
        return pd.DataFrame.from_records(tags)

    def create_tag(self, name: str, prompt: str, config: str, type: str, valid_classes: str) -> pd.DataFrame:
        try:
            self._tag_crud.create(
                name,
                prompt,
                config,
                type,
                valid_classes
            )
            gr.Info(f'Create index "{name}" successfully')
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
            tag_id=tag_id
        )

        indexing_pipeline.run(
            tag_prompt=tag_prompt
        )

    def on_register_events(self):
        # Enable selection while user select classification
        self.type.change(
            lambda selected_type: gr.update(
                visible=(selected_type == TagType.classification.value)
            ),
            inputs=[self.type],
            outputs=[self.valid_classes],
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
