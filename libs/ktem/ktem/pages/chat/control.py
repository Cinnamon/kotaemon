import logging

import gradio as gr
from ktem.app import BasePage
from ktem.db.models import Conversation, engine
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


class ConversationControl(BasePage):
    """Manage conversation"""

    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Conversation control", open=True):
            self.conversation_id = gr.State(value="")
            self.conversation = gr.Dropdown(
                label="Chat sessions",
                choices=[],
                container=False,
                filterable=False,
                interactive=True,
            )

            with gr.Row():
                self.conversation_new_btn = gr.Button(value="New", min_width=10)
                self.conversation_del_btn = gr.Button(value="Delete", min_width=10)

            with gr.Row():
                self.conversation_rn = gr.Text(
                    placeholder="Conversation name",
                    container=False,
                    scale=5,
                    min_width=10,
                    interactive=True,
                )
                self.conversation_rn_btn = gr.Button(
                    value="Rename", scale=1, min_width=10
                )

        # current_state = gr.Text()
        # show_current_state = gr.Button(value="Current")
        # show_current_state.click(
        #     lambda a, b: "\n".join([a, b]),
        #     inputs=[cid, self.conversation],
        #     outputs=[current_state],
        # )

    def on_subscribe_public_events(self):
        self._app.subscribe_event(
            name="onSignIn",
            definition={
                "fn": self.reload_conv,
                "inputs": [self._app.user_id],
                "outputs": [self.conversation],
                "show_progress": "hidden",
            },
        )

        self._app.subscribe_event(
            name="onSignOut",
            definition={
                "fn": self.reload_conv,
                "inputs": [self._app.user_id],
                "outputs": [self.conversation],
                "show_progress": "hidden",
            },
        )

        self._app.subscribe_event(
            name="onCreateUser",
            definition={
                "fn": self.reload_conv,
                "inputs": [self._app.user_id],
                "outputs": [self.conversation],
                "show_progress": "hidden",
            },
        )

    def on_register_events(self):
        self.conversation_new_btn.click(
            self.new_conv,
            inputs=self._app.user_id,
            outputs=[self.conversation_id, self.conversation],
            show_progress="hidden",
        )
        self.conversation_del_btn.click(
            self.delete_conv,
            inputs=[self.conversation_id, self._app.user_id],
            outputs=[self.conversation_id, self.conversation],
            show_progress="hidden",
        )
        self.conversation_rn_btn.click(
            self.rename_conv,
            inputs=[self.conversation_id, self.conversation_rn, self._app.user_id],
            outputs=[self.conversation, self.conversation],
            show_progress="hidden",
        )

    def load_chat_history(self, user_id):
        """Reload chat history"""
        options = []
        with Session(engine) as session:
            statement = (
                select(Conversation)
                .where(Conversation.user == user_id)
                .order_by(Conversation.date_created.desc())  # type: ignore
            )
            results = session.exec(statement).all()
            for result in results:
                options.append((result.name, result.id))

        return options

    def reload_conv(self, user_id):
        conv_list = self.load_chat_history(user_id)
        if conv_list:
            return gr.update(value=conv_list[0][1], choices=conv_list)
        else:
            return gr.update(value=None, choices=[])

    def new_conv(self, user_id):
        """Create new chat"""
        if user_id is None:
            gr.Warning("Please sign in first (Settings → User Settings)")
            return None, gr.update()
        with Session(engine) as session:
            new_conv = Conversation(user=user_id)
            session.add(new_conv)
            session.commit()

            id_ = new_conv.id

        history = self.load_chat_history(user_id)

        return id_, gr.update(value=id_, choices=history)

    def delete_conv(self, conversation_id, user_id):
        """Create new chat"""
        if user_id is None:
            gr.Warning("Please sign in first (Settings → User Settings)")
            return None, gr.update()
        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == conversation_id)
            result = session.exec(statement).one()

            session.delete(result)
            session.commit()

        history = self.load_chat_history(user_id)
        if history:
            id_ = history[0][1]
            return id_, gr.update(value=id_, choices=history)
        else:
            return None, gr.update(value=None, choices=[])

    def select_conv(self, conversation_id):
        """Select the conversation"""
        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == conversation_id)
            try:
                result = session.exec(statement).one()
                id_ = result.id
                name = result.name
                selected = result.data_source.get("selected", {})
                chats = result.data_source.get("messages", [])
            except Exception as e:
                logger.warning(e)
                id_ = ""
                name = ""
                selected = {}
                chats = []

        indices = []
        for index in self._app.index_manager.indices:
            # assume that the index has selector
            if index.selector == -1:
                continue
            indices.append(selected.get(str(index.id), []))

        return id_, id_, name, chats, *indices

    def rename_conv(self, conversation_id, new_name, user_id):
        """Rename the conversation"""
        if user_id is None:
            gr.Warning("Please sign in first (Settings → User Settings)")
            return gr.update(), ""
        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == conversation_id)
            result = session.exec(statement).one()
            result.name = new_name
            session.add(result)
            session.commit()

        history = self.load_chat_history(user_id)
        return gr.update(choices=history), conversation_id

    def _on_app_created(self):
        """Reload the conversation once the app is created"""
        self._app.app.load(
            self.reload_conv,
            inputs=[self._app.user_id],
            outputs=[self.conversation],
        )
