import gradio as gr
from decouple import config
from ktem.app import BaseApp
from ktem.pages.chat import ChatPage
from ktem.pages.help import HelpPage
from ktem.pages.resources import ResourcesTab
from ktem.pages.settings import SettingsPage
from ktem.pages.setup import SetupPage
from theflow.settings import settings as flowsettings

KH_DEMO_MODE = getattr(flowsettings, "KH_DEMO_MODE", False)
KH_ENABLE_FIRST_SETUP = getattr(flowsettings, "KH_ENABLE_FIRST_SETUP", False)
KH_APP_DATA_EXISTS = getattr(flowsettings, "KH_APP_DATA_EXISTS", True)

# override first setup setting
if config("KH_FIRST_SETUP", default=False, cast=bool):
    KH_APP_DATA_EXISTS = False


def toggle_first_setup_visibility():
    global KH_APP_DATA_EXISTS
    is_first_setup = KH_DEMO_MODE or not KH_APP_DATA_EXISTS
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
                        f"{index.name}",
                        elem_id="indices-tab",
                        elem_classes=[
                            "fill-main-area-height",
                            "scrollable",
                            "indices-tab",
                        ],
                        id="indices-tab",
                        visible=not self.f_user_management,
                    ) as self._tabs[f"{index.id}-tab"]:
                        page = index.get_index_page_ui()
                        setattr(self, f"_index_{index.id}", page)
            elif len(self.index_manager.indices) > 1:
                with gr.Tab(
                    "Files",
                    elem_id="indices-tab",
                    elem_classes=["fill-main-area-height", "scrollable", "indices-tab"],
                    id="indices-tab",
                    visible=not self.f_user_management,
                ) as self._tabs["indices-tab"]:
                    for index in self.index_manager.indices:
                        with gr.Tab(
                            index.name,
                            elem_id=f"{index.id}-tab",
                        ) as self._tabs[f"{index.id}-tab"]:
                            page = index.get_index_page_ui()
                            setattr(self, f"_index_{index.id}", page)

            with gr.Tab(
                "Resources",
                elem_id="resources-tab",
                id="resources-tab",
                visible=not self.f_user_management,
                elem_classes=["fill-main-area-height", "scrollable"],
            ) as self._tabs["resources-tab"]:
                self.resources_page = ResourcesTab(self)

            with gr.Tab(
                "Settings",
                elem_id="settings-tab",
                id="settings-tab",
                visible=not self.f_user_management,
                elem_classes=["fill-main-area-height", "scrollable"],
            ) as self._tabs["settings-tab"]:
                self.settings_page = SettingsPage(self)

            with gr.Tab(
                "Help",
                elem_id="help-tab",
                id="help-tab",
                visible=not self.f_user_management,
                elem_classes=["fill-main-area-height", "scrollable"],
            ) as self._tabs["help-tab"]:
                self.help_page = HelpPage(self)

        if KH_ENABLE_FIRST_SETUP:
            with gr.Column(visible=False) as self.setup_page_wrapper:
                self.setup_page = SetupPage(self)

    def on_subscribe_public_events(self):
        if self.f_user_management:
            from ktem.db.engine import engine
            from ktem.db.models import User
            from sqlmodel import Session, select

            def toggle_login_visibility(user_id):
                if not user_id:
                    return list(
                        (
                            gr.update(visible=True)
                            if k == "login-tab"
                            else gr.update(visible=False)
                        )
                        for k in self._tabs.keys()
                    ) + [gr.update(selected="login-tab")]

                with Session(engine) as session:
                    user = session.exec(select(User).where(User.id == user_id)).first()
                    if user is None:
                        return list(
                            (
                                gr.update(visible=True)
                                if k == "login-tab"
                                else gr.update(visible=False)
                            )
                            for k in self._tabs.keys()
                        )

                    is_admin = user.admin

                tabs_update = []
                for k in self._tabs.keys():
                    if k == "login-tab":
                        tabs_update.append(gr.update(visible=False))
                    elif k == "resources-tab":
                        tabs_update.append(gr.update(visible=is_admin))
                    else:
                        tabs_update.append(gr.update(visible=True))

                tabs_update.append(gr.update(selected="chat-tab"))

                return tabs_update

            self.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs],
                    "show_progress": "hidden",
                },
            )

            self.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": toggle_login_visibility,
                    "inputs": [self.user_id],
                    "outputs": list(self._tabs.values()) + [self.tabs],
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
