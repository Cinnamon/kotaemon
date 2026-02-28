import json
import logging

import gradio as gr
import pandas as pd
from ktem.app import BasePage

from kotaemon.agents.tools.mcp import discover_tools_info, format_tool_list

from .manager import mcp_manager

logger = logging.getLogger(__name__)

TOOLS_DEFAULT = "# Available Tools\n\nSelect or add an MCP server to view its tools."

MCP_SERVERS_KEY = "mcpServers"

EXAMPLE_CONFIG = """{
  "mcpServers": {
  }
}"""


class MCPManagement(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab(label="View"):
            self.mcp_list = gr.DataFrame(
                headers=["name", "config"],
                interactive=False,
                column_widths=[30, 70],
            )

            with gr.Column(visible=False) as self._selected_panel:
                self.selected_mcp_name = gr.Textbox(value="", visible=False)
                with gr.Row():
                    with gr.Column():
                        self.edit_config = gr.Code(
                            label="Configuration (JSON)",
                            language="json",
                            lines=10,
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
                        self.edit_tools_display = gr.Markdown(TOOLS_DEFAULT)

        with gr.Tab(label="Add"):
            with gr.Row():
                with gr.Column(scale=2):
                    self.config = gr.Code(
                        label="Configuration (JSON)",
                        language="json",
                        lines=10,
                        value=EXAMPLE_CONFIG,
                    )
                    gr.HTML(
                        "<br/>"
                    )  # Fix: Prevent the overflow of the gr.Code affect click button
                    with gr.Row():
                        self.btn_new = gr.Button("Add MCP Servers", variant="primary")

                with gr.Column(scale=3):
                    self.add_tools_display = gr.Markdown(TOOLS_DEFAULT)

    def _on_app_created(self):
        """Called when the app is created."""
        self._app.app.load(
            self.list_servers,
            inputs=[],
            outputs=[self.mcp_list],
        )

    def on_register_events(self):
        # Add new server — save first, then fetch tools async
        self.btn_new.click(
            self.create_server,
            inputs=[self.config],
            outputs=[self.add_tools_display],
        ).success(self.list_servers, inputs=[], outputs=[self.mcp_list]).then(
            self.fetch_tools_for_add,
            inputs=[self.config],
            outputs=[self.add_tools_display],
        ).then(
            lambda: EXAMPLE_CONFIG,
            outputs=[self.config],
        )

        # Select a server from list
        self.mcp_list.select(
            self.select_server,
            inputs=self.mcp_list,
            outputs=[self.selected_mcp_name],
            show_progress="hidden",
        )
        self.selected_mcp_name.change(
            self.on_selected_server_change,
            inputs=[self.selected_mcp_name],
            outputs=[
                self._selected_panel,
                self._selected_panel_btn,
                self.btn_delete,
                self.btn_delete_yes,
                self.btn_delete_no,
                self.edit_config,
                self.edit_tools_display,
            ],
            show_progress="hidden",
        ).then(
            self.fetch_tools_for_view,
            inputs=[self.selected_mcp_name],
            outputs=[self.edit_tools_display],
        )

        # Delete flow
        self.btn_delete.click(
            self.on_btn_delete_click,
            inputs=[],
            outputs=[self.btn_delete, self.btn_delete_yes, self.btn_delete_no],
            show_progress="hidden",
        )
        self.btn_delete_yes.click(
            self.delete_server,
            inputs=[self.selected_mcp_name],
            outputs=[self.selected_mcp_name],
            show_progress="hidden",
        ).then(self.list_servers, inputs=[], outputs=[self.mcp_list])
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

        # Save edits — save first, then refresh tools
        self.btn_edit_save.click(
            self.save_server,
            inputs=[self.selected_mcp_name, self.edit_config],
            outputs=[self.edit_tools_display],
            show_progress="hidden",
        ).then(self.list_servers, inputs=[], outputs=[self.mcp_list]).then(
            self.fetch_tools_for_view,
            inputs=[self.selected_mcp_name],
            outputs=[self.edit_tools_display],
        )

        # Close panel
        self.btn_close.click(lambda: "", outputs=[self.selected_mcp_name])

    # --- Handlers ---

    def _fetch_tools_markdown(self, config: dict) -> str:
        """Fetch tools from MCP server and return as formatted HTML."""
        try:
            tool_infos = discover_tools_info(config)
            enabled_tools = config.get("enabled_tools", None)
            return format_tool_list(tool_infos, enabled_tools)
        except Exception as e:
            return f"❌ Failed to fetch tools: {e}"

    def create_server(self, config_str):
        """Create server(s), show loading placeholder."""
        try:
            configs = json.loads(config_str)
        except json.JSONDecodeError as e:
            raise gr.Error(f"Invalid JSON: {e}")

        if not isinstance(configs, dict) or MCP_SERVERS_KEY not in configs:
            raise gr.Error(
                f"Config must be a dictionary with '{MCP_SERVERS_KEY}' root key."
            )

        mcp_servers = configs[MCP_SERVERS_KEY]
        if not isinstance(mcp_servers, dict):
            raise gr.Error(
                f"'{MCP_SERVERS_KEY}' must be a mapping of server names to configs."
            )

        # Validate that no names are empty before processing
        for name in mcp_servers:
            name = name.strip()
            if not name:
                raise gr.Error("Server names cannot be empty.")

        success_count = 0
        failed_count = 0
        msgs = []
        for name, config in mcp_servers.items():
            name = name.strip()
            if name in mcp_manager.info():
                gr.Warning(f"MCP server '{name}' already exists. Skipping.")
                failed_count += 1
                continue

            try:
                mcp_manager.add(name, config)
                success_count += 1
                msgs.append(f"# Tools for '{name}'\n\n⏳ Fetching tools...")
            except Exception as e:
                gr.Warning(f"Failed to create MCP server '{name}': {e}")
                failed_count += 1

        if success_count > 0:
            gr.Info(f"{success_count} MCP server(s) created successfully")

        if not msgs:
            return TOOLS_DEFAULT

        return "\n\n".join(msgs)

    def fetch_tools_for_add(self, config_str):
        """Fetch tools after server was added (chained call)."""
        if not config_str:
            return TOOLS_DEFAULT
        try:
            configs = json.loads(config_str)
        except json.JSONDecodeError:
            return "❌ Invalid JSON config"

        if not isinstance(configs, dict) or MCP_SERVERS_KEY not in configs:
            return f"❌ Config must be a dictionary with '{MCP_SERVERS_KEY}' root key"

        mcp_servers = configs[MCP_SERVERS_KEY]
        if not isinstance(mcp_servers, dict):
            return f"❌ '{MCP_SERVERS_KEY}' must be a dictionary"

        msgs = []
        for name, config in mcp_servers.items():
            msgs.append(
                f"# Tools for '{name.strip()}'\n\n{self._fetch_tools_markdown(config)}"
            )
        return "\n\n".join(msgs)

    def fetch_tools_for_view(self, selected_name):
        """Fetch tools for the View panel (chained call)."""
        if not selected_name:
            return TOOLS_DEFAULT
        entry = mcp_manager.info().get(selected_name)
        if not entry:
            return TOOLS_DEFAULT
        config = entry.get("config", {})
        return f"# Tools for '{selected_name}'\n\n{self._fetch_tools_markdown(config)}"

    def list_servers(self):
        items = []
        for entry in mcp_manager.info().values():
            items.append(
                {
                    "name": entry["name"],
                    "config": json.dumps(entry.get("config", {})),
                }
            )

        if items:
            return pd.DataFrame.from_records(items)
        return pd.DataFrame.from_records([{"name": "-", "config": "-"}])

    def select_server(self, mcp_list, ev: gr.SelectData):
        if ev.value == "-" and ev.index[0] == 0:
            gr.Info("No MCP server configured. Please add one first.")
            return ""
        if not ev.selected:
            return ""
        return mcp_list["name"][ev.index[0]]

    def on_selected_server_change(self, selected_name):
        if selected_name == "":
            return (
                gr.update(visible=False),  # panel
                gr.update(visible=False),  # buttons
                gr.update(visible=True),  # delete
                gr.update(visible=False),  # delete_yes
                gr.update(visible=False),  # delete_no
                gr.update(value="{}"),  # config
                gr.update(value=TOOLS_DEFAULT),  # tools display
            )

        entry = mcp_manager.info()[selected_name]
        config = entry.get("config", {})
        config_str = json.dumps(config, indent=2)

        return (
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value=config_str),
            gr.update(value=f"# Tools for '{selected_name}'\n\n⏳ Fetching tools..."),
        )

    def on_btn_delete_click(self):
        return (
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(visible=True),
        )

    def delete_server(self, selected_name):
        try:
            mcp_manager.delete(selected_name)
            gr.Info(f"MCP server '{selected_name}' deleted successfully")
        except Exception as e:
            gr.Error(f"Failed to delete MCP server '{selected_name}': {e}")
            return selected_name
        return ""

    def save_server(self, selected_name, config_str):
        try:
            config = json.loads(config_str)
        except json.JSONDecodeError as e:
            raise gr.Error(f"Invalid JSON: {e}")

        try:
            mcp_manager.update(selected_name, config)
            gr.Info(f"MCP server '{selected_name}' saved successfully")
        except Exception as e:
            raise gr.Error(f"Failed to save MCP server '{selected_name}': {e}")

        # Show loading placeholder; tools fetched in chained .then()
        return f"# Tools for '{selected_name}'\n\n⏳ Refreshing tools..."
