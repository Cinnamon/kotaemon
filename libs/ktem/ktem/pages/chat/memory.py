import logging
import os

import gradio as gr
import pandas as pd
import requests
from ktem.app import BasePage

logger = logging.getLogger(__name__)


DEFAULT_KNET_ENDPOINT = "http://127.0.0.1:8081"
KNET_ENDPOINT = os.environ.get("KN_ENDPOINT", DEFAULT_KNET_ENDPOINT)
LONG_TERM_MEMORY_COLLECTION = "long_term_memory"


class MemoryPage(BasePage):
    """Manage RAG long-term memory from KNet"""

    def __init__(self, app):
        self._app = app
        self.memory_list = gr.State(value=[])

        self.on_building_ui()

    def list_memories(self, user_id):
        """Retrieve memory list from KNet endpoint"""
        memory_list = []
        try:
            params = {"user_id": user_id, "collection": LONG_TERM_MEMORY_COLLECTION}

            response = requests.get(
                KNET_ENDPOINT + "/retrieve_long_term_memory", params=params, timeout=5
            )
            if response.status_code == 200:
                output = response.json()
                memory_list = output["knowledges"]
                print(params, memory_list)
            else:
                raise IOError(f"{response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to retrieve KNet memory: {e}")

        if memory_list:
            memory_list = pd.DataFrame.from_records(
                memory_list,
                columns=["id", "text"],
            )
        else:
            memory_list = pd.DataFrame.from_records(
                [
                    {
                        "id": "-",
                        "text": "-",
                    }
                ],
                columns=["id", "text"],
            )
        return memory_list

    def delete_memory(self, memory_id):
        """Delete memory from KNet endpoint"""
        try:
            params = {"ids": [memory_id], "collection": LONG_TERM_MEMORY_COLLECTION}

            response = requests.delete(
                KNET_ENDPOINT + "/delete_long_term_memory", params=params, timeout=20
            )
            print(params, response.text)
            if response.status_code == 200:
                gr.Info("Memory deleted successfully")
            else:
                raise IOError(f"{response.status_code}: {response.text}")
        except Exception as e:
            raise gr.Error(f"Failed to delete KNet memory: {e}")

    def interact_memory_list(self, memory_list, ev: gr.SelectData):
        if (ev.value == "-" and ev.index[0] == 0) or not ev.selected:
            return "", "", gr.update(visible=False)

        return (
            memory_list["id"][ev.index[0]],
            memory_list["text"][ev.index[0]],
            gr.update(visible=True),
        )

    def on_building_ui(self):
        self.memories = gr.Dataframe(
            headers=[
                "id",
                "text",
            ],
            column_widths=["20%", "80%"],
            interactive=False,
        )

        with gr.Row(visible=False) as self.memory_detail_panel:
            self.selected_memory_id = gr.State(value="")
            self.selected_memory_text = gr.Textbox(
                "Memory",
                interactive=False,
                container=False,
                scale=2,
            )
            self.delete_button = gr.Button(
                "Delete",
                variant="stop",
                scale=1,
            )

        with gr.Row():
            self.refresh_button = gr.Button(
                "Refresh",
                variant="secondary",
            )
            self.close_button = gr.Button(
                "Close",
                variant="secondary",
            )

    def on_register_events(self):
        gr.on(
            triggers=[
                self.memories.select,
            ],
            fn=self.interact_memory_list,
            inputs=[
                self.memories,
            ],
            outputs=[
                self.selected_memory_id,
                self.selected_memory_text,
                self.memory_detail_panel,
            ],
        )

        gr.on(
            triggers=[
                self.delete_button.click,
            ],
            fn=self.delete_memory,
            inputs=[
                self.selected_memory_id,
            ],
        ).then(
            self.list_memories,
            inputs=[
                self._app.user_id,
            ],
            outputs=[
                self.memories,
            ],
        )

        self.refresh_button.click(
            self.list_memories, inputs=[self._app.user_id], outputs=[self.memories]
        )
