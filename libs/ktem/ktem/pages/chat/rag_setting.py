import logging
import os

import gradio as gr
import requests
from ktem.app import BasePage

logger = logging.getLogger(__name__)


DEFAULT_KNET_ENDPOINT = "http://127.0.0.1:8081"
KNET_ENDPOINT = os.environ.get("KN_ENDPOINT", DEFAULT_KNET_ENDPOINT)


class RAGSetting(BasePage):
    """Manage RAG settings from KNet"""

    def __init__(self, app):
        self._app = app
        self.setting_state = gr.State(value={})
        self.on_building_ui()
        self.on_register_events()

    def get_pipelines(self):
        """Retrieve pipeline list from KNet endpoint"""
        try:
            response = requests.get(KNET_ENDPOINT + "/query_type", timeout=5)
            if response.status_code == 200:
                output = response.json()
                return [item["name"] for item in output["pipelines"]]
            else:
                raise IOError(f"{response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to retrieve KNet pipelines: {e}")
            return []

    def on_building_ui(self):
        pipline_options = self.get_pipelines()
        self.pipeline_select = gr.Dropdown(
            label="Pipeline",
            choices=pipline_options,
            value=pipline_options[0] if pipline_options else None,
            container=False,
            interactive=True,
        )
        self.retrieval_expansion = gr.Checkbox(
            label="Enable retrieval expansion",
            value=False,
            container=False,
        )

    def store_setting_state(self, pipeline, retrieval_expansion):
        return {
            "pipeline": pipeline,
            "retrieval_expansion": retrieval_expansion,
        }

    def on_register_events(self):
        gr.on(
            triggers=[
                self.pipeline_select.change,
                self.retrieval_expansion.change,
            ],
            fn=self.store_setting_state,
            inputs=[
                self.pipeline_select,
                self.retrieval_expansion,
            ],
            outputs=self.setting_state,
        )
