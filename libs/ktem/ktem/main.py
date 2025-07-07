import gradio as gr
import os
from decouple import config
from ktem.app import BaseApp
from ktem.pages.chat import ChatPage
from ktem.pages.help import HelpPage
from ktem.pages.resources import ResourcesTab
from ktem.pages.settings import SettingsPage
from ktem.pages.setup import SetupPage
from theflow.settings import settings as flowsettings

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_SSO_ENABLED = getattr(flowsettings, "KH_SSO_ENABLED", False)
KH_ENABLE_FIRST_SETUP = getattr(flowsettings, "KH_ENABLE_FIRST_SETUP", False)
KH_APP_DATA_EXISTS = getattr(flowsettings, "KH_APP_DATA_EXISTS", True)

ASSETS_DIR = "assets/icons"
if not os.path.isdir(ASSETS_DIR):
    ASSETS_DIR = "libs/ktem/ktem/assets/icons"

# override first setup setting
if config("KH_FIRST_SETUP", default=False, cast=bool):
    KH_APP_DATA_EXISTS = False


def toggle_first_setup_visibility():
    global KH_APP_DATA_EXISTS
    is_first_setup = False
    KH_APP_DATA_EXISTS = True
    return gr.update(visible=is_first_setup), gr.update(visible=not is_first_setup)


class App(BaseApp):
    """The main app of Kotaemon

    The main application contains app-level information:
        - setting state
        - user id

    App life-cycle:
        - Render
        - Declare public events
        - Subscribe public events
        - Register events
    """

    def ui(self):
        """Render the UI"""
        self._tabs = {}

        with gr.Row():
            with gr.Tabs() as self.tabs:
                if self.f_user_management:
                    from ktem.pages.login import LoginPage

                    with gr.Tab(
                        "Welcome", elem_id="login-tab", id="login-tab"
                    ) as self._tabs["login-tab"]:
                        self.login_page = LoginPage(self)

                with gr.Tab(
                    "Chat",
                    elem_id="chat-tab",
                    id="chat-tab",
                    visible=not self.f_user_management,
                ) as self._tabs["chat-tab"]:
                    self.chat_page = ChatPage(self)

                if len(self.index_manager.indices) == 1:
                    for index in self.index_manager.indices:
                        with gr.Tab(
                            "Files",
                            elem_id="indices-tab",
                            elem_classes=[
                                "fill-main-area-height",
                                "scrollable",
                                "indices-tab",
                            ],
                            id="indices-tab",
                            visible=not self.f_user_management and not KH_DEMO_MODE,
                        ) as self._tabs[f"{index.id}-tab"]:
                            page = index.get_index_page_ui()
                            setattr(self, f"_index_{index.id}", page)
                elif len(self.index_manager.indices) > 1:
                    with gr.Tab(
                        "Files",
                        elem_id="indices-tab",
                        elem_classes=["fill-main-area-height", "scrollable", "indices-tab"],
                        id="indices-tab",
                        visible=not self.f_user_management and not KH_DEMO_MODE,
                    ) as self._tabs["indices-tab"]:
                        for index in self.index_manager.indices:
                            with gr.Tab(
                                index.name,
                                elem_id=f"{index.id}-tab",
                            ) as self._tabs[f"{index.id}-tab"]:
                                page = index.get_index_page_ui()
                                setattr(self, f"_index_{index.id}", page)
                with gr.Tab(
                        "User",
                        elem_id="settings-tab",
                        id="settings-tab",
                        visible=False,  # pastikan tab user tidak muncul
                        elem_classes=["fill-main-area-height", "scrollable"],
                    ) as self._tabs["settings-tab"]:
                        self.settings_page = SettingsPage(self)

                with gr.Tab(
                    "Help",
                    elem_id="help-tab",
                    id="help-tab",
                    visible=False,
                    elem_classes=["fill-main-area-height", "scrollable"],
                ) as self._tabs["help-tab"]:
                    self.help_page = HelpPage(self)
                    
                if not KH_DEMO_MODE:
                    if not KH_SSO_ENABLED:
                        with gr.Tab(
                            "Resources",
                            elem_id="resources-tab",
                            id="resources-tab",
                            visible=False,
                            elem_classes=["fill-main-area-height", "scrollable"],
                        ) as self._tabs["resources-tab"]:
                            self.resources_page = ResourcesTab(self)
        if KH_ENABLE_FIRST_SETUP:
            with gr.Column(visible=False) as self.setup_page_wrapper:
                self.setup_page = SetupPage(self)
                # Hide help and user button while setup page is shown
                if hasattr(self, "help_button") and self.help_button is not None:
                    self.help_button.visible = False
                if hasattr(self, "user_button") and self.user_button is not None:
                    self.user_button.visible = False
        with gr.Column(
            elem_classes=["additional-tab-button-col"]
        ):
            # State untuk tab aktif
            active_tab = gr.State(value="other")
            # Tombol untuk mengubah tab ke 'help-tab'
            self.help_button = gr.Button(
                "",
                elem_id="help-tab-button-icon",
                icon=f"{ASSETS_DIR}/docu-info-circle.svg",
                visible=False,
                size="lg",
                variant="secondary",
                elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon"]
            )
            # Tombol untuk mengubah tab ke 'settings-tab'
            self.user_button = gr.Button(
                "User",
                elem_id="user-tab-button-icon",
                icon=f"{ASSETS_DIR}/docu-user-circle.svg",
                visible=False,
                size="lg",
                variant="secondary",
                elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon", "force-hide"]
            )

            def set_tab(tab_id):
                return gr.update(selected=tab_id), tab_id

            # Saat user_button di-click, pindahkan tab ke 'settings-tab' dan update state
            self.user_button.click(
                fn=lambda: set_tab("settings-tab"),
                outputs=[self.tabs, active_tab]
            )
            # Saat help_button di-click, pindahkan tab ke 'help-tab' dan update state
            self.help_button.click(
                fn=lambda: set_tab("help-tab"),
                outputs=[self.tabs, active_tab]
            )

            # Ganti icon sesuai tab aktif
            def update_icons(tab_id, reset):
                # Jika dipanggil dari self.tabs.select, set active_tab ke 'other' agar tombol reset
                if reset == "from_select":
                    return (
                        gr.update(icon=f"{ASSETS_DIR}/docu-info-circle.svg"),
                        gr.update(icon=f"{ASSETS_DIR}/docu-user-circle.svg", elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon"]),
                        "other"
                    )
                # Ubah warna text dan icon sesuai tab aktif
                help_active = tab_id == "help-tab"
                user_active = tab_id == "settings-tab"
                return (
                    gr.update(
                        icon=f"{ASSETS_DIR}/docu-info-circle-active.svg" if help_active else f"{ASSETS_DIR}/docu-info-circle.svg"
                    ),
                    gr.update(
                        icon=f"{ASSETS_DIR}/docu-user-circle-active.svg" if user_active else f"{ASSETS_DIR}/docu-user-circle.svg",
                        elem_classes=[
                            "additional-tab-button", "no-background", "no-shadow-button-icon", ("additional-tab-button-active" if user_active else "")
                        ]
                    ),
                    tab_id
                )
            active_tab.change(
                fn=lambda tab_id: update_icons(tab_id, None)[:2],
                inputs=active_tab,
                outputs=[self.help_button, self.user_button],
                show_progress="hidden"
            )

            # Update tombol setiap kali tab berubah (tanpa reset_state)
            self.tabs.select(
                fn=lambda tab_id: update_icons(tab_id, "from_select"),
                inputs=[active_tab],
                outputs=[self.help_button, self.user_button, active_tab],
                show_progress="hidden"
            )

    def on_subscribe_public_events(self):
        if self.f_user_management:
            from ktem.db.engine import engine
            from ktem.db.models import User
            from sqlmodel import Session, select

            def toggle_login_visibility(user_id):
                # Update tab visibility
                if not user_id:
                    # Hide help/user button if on login page
                    return (
                        [
                            gr.update(visible=True) if k == "login-tab" else gr.update(visible=False)
                            for k in self._tabs.keys()
                        ]
                        + [gr.update(selected="login-tab")]
                        + [gr.update(visible=False), gr.update(visible=False, icon=f"{ASSETS_DIR}/docu-user-circle.svg", elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon", "force-hide"])]
                    )

                with Session(engine) as session:
                    user = session.exec(select(User).where(User.id == user_id)).first()
                    if user is None:
                        return (
                            [
                                gr.update(visible=True) if k == "login-tab" else gr.update(visible=False)
                                for k in self._tabs.keys()
                            ]
                            + [gr.update(selected="login-tab")]
                            + [gr.update(visible=False), gr.update(visible=False, icon=f"{ASSETS_DIR}/docu-user-circle.svg", elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon", "force-hide"])]
                        )

                    is_admin = user.admin

                tabs_update = []
                for k in self._tabs.keys():
                    if k == "login-tab":
                        tabs_update.append(gr.update(visible=False))
                    elif k == "resources-tab":
                        tabs_update.append(gr.update(visible=False))
                    else:
                        tabs_update.append(gr.update(visible=True))

                tabs_update.append(gr.update(selected="chat-tab"))
                # Show help/user button after login
                tabs_update.append(gr.update(visible=True))
                tabs_update.append(gr.update(visible=True, elem_classes=["additional-tab-button", "no-background", "no-shadow-button-icon"]))
                return tabs_update

            self.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs, self.help_button, self.user_button],
                    "show_progress": "hidden",
                },
            )

            self.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs, self.help_button, self.user_button],
                    "show_progress": "hidden",
                },
            )

        if KH_ENABLE_FIRST_SETUP:
            self.subscribe_event(
                name="onFirstSetupComplete",
                definition={
                    "fn": toggle_first_setup_visibility,
                    "inputs": [],
                    "outputs": [self.setup_page_wrapper, self.tabs],
                    "show_progress": "hidden",
                },
            )

    def _on_app_created(self):
        """Called when the app is created"""

        if KH_ENABLE_FIRST_SETUP:
            self.app.load(
                toggle_first_setup_visibility,
                inputs=[],
                outputs=[self.setup_page_wrapper, self.tabs],
            )
