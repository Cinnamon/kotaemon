import gradio as gr
from ktem.app import BasePage
from ktem.db.models import User, engine
from ktem.embeddings.ui import EmbeddingManagement
from ktem.index.ui import IndexManagement
from ktem.llms.ui import LLMManagement
from sqlmodel import Session, select

from .user import UserManagement


class ResourcesTab(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Tab("Index Collections") as self.index_management_tab:
            self.index_management = IndexManagement(self._app)

        with gr.Tab("LLMs") as self.llm_management_tab:
            self.llm_management = LLMManagement(self._app)

        with gr.Tab("Embeddings") as self.emb_management_tab:
            self.emb_management = EmbeddingManagement(self._app)

        if self._app.f_user_management:
            with gr.Tab("Users", visible=False) as self.user_management_tab:
                self.user_management = UserManagement(self._app)

    def on_subscribe_public_events(self):
        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.toggle_user_management,
                    "inputs": [self._app.user_id],
                    "outputs": [self.user_management_tab],
                    "show_progress": "hidden",
                },
            )

            self._app.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": self.toggle_user_management,
                    "inputs": [self._app.user_id],
                    "outputs": [self.user_management_tab],
                    "show_progress": "hidden",
                },
            )

    def toggle_user_management(self, user_id):
        """Show/hide the user management, depending on the user's role"""
        with Session(engine) as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user and user.admin:
                return gr.update(visible=True)

            return gr.update(visible=False)
