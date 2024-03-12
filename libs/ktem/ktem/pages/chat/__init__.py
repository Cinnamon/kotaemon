import asyncio
from copy import deepcopy
from typing import Optional

import gradio as gr
from ktem.app import BasePage
from ktem.components import reasonings
from ktem.db.models import Conversation, engine
from sqlmodel import Session, select

from .chat_panel import ChatPanel
from .control import ConversationControl
from .report import ReportIssue


class ChatPage(BasePage):
    def __init__(self, app):
        self._app = app
        self._indices_input = []
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Row():
            with gr.Column(scale=1):
                self.chat_control = ConversationControl(self._app)

                for index in self._app.index_manager.indices:
                    index.selector = -1
                    index_ui = index.get_selector_component_ui()
                    if not index_ui:
                        continue

                    index_ui.unrender()
                    with gr.Accordion(label=f"{index.name} Index", open=False):
                        index_ui.render()
                        gr_index = index_ui.as_gradio_component()
                        if gr_index:
                            index.selector = len(self._indices_input)
                            self._indices_input.append(gr_index)
                        setattr(self, f"_index_{index.id}", index_ui)

                self.report_issue = ReportIssue(self._app)
            with gr.Column(scale=6):
                self.chat_panel = ChatPanel(self._app)
            with gr.Column(scale=3):
                with gr.Accordion(label="Information panel", open=True):
                    self.info_panel = gr.HTML(elem_id="chat-info-panel")

    def on_register_events(self):
        gr.on(
            triggers=[
                self.chat_panel.text_input.submit,
                self.chat_panel.submit_btn.click,
            ],
            fn=self.chat_panel.submit_msg,
            inputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            outputs=[self.chat_panel.text_input, self.chat_panel.chatbot],
            show_progress="hidden",
        ).then(
            fn=self.chat_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self._app.dynamic_state,
            ]
            + self._indices_input,
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.info_panel,
            ],
            show_progress="minimal",
        ).then(
            fn=self.update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.dynamic_state,
            ]
            + self._indices_input,
            outputs=None,
        )

        self.chat_panel.regen_btn.click(
            fn=self.regen_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self._app.dynamic_state,
            ]
            + self._indices_input,
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.info_panel,
            ],
            show_progress="minimal",
        ).then(
            fn=self.update_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.dynamic_state,
            ]
            + self._indices_input,
            outputs=None,
        )

        self.chat_panel.chatbot.like(
            fn=self.is_liked,
            inputs=[self.chat_control.conversation_id],
            outputs=None,
        )

        self.chat_control.conversation.change(
            self.chat_control.select_conv,
            inputs=[self.chat_control.conversation],
            outputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
                self.chat_panel.chatbot,
                self._app.dynamic_state,
            ]
            + self._indices_input,
            show_progress="hidden",
        )

        self.report_issue.report_btn.click(
            self.report_issue.report,
            inputs=[
                self.report_issue.correctness,
                self.report_issue.issues,
                self.report_issue.more_detail,
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self._app.user_id,
            ]
            + self._indices_input,
            outputs=None,
        )

    def update_data_source(self, convo_id, messages, state, *selecteds):
        """Update the data source"""
        if not convo_id:
            gr.Warning("No conversation selected")
            return

        selecteds_ = {}
        for index in self._app.index_manager.indices:
            if index.selector != -1:
                selecteds_[str(index.id)] = selecteds[index.selector]

        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == convo_id)
            result = session.exec(statement).one()

            data_source = result.data_source
            result.data_source = {
                "selected": selecteds_,
                "messages": messages,
                "state": state,
                "likes": deepcopy(data_source.get("likes", [])),
            }
            session.add(result)
            session.commit()

    def is_liked(self, convo_id, liked: gr.LikeData):
        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == convo_id)
            result = session.exec(statement).one()

            data_source = deepcopy(result.data_source)
            likes = data_source.get("likes", [])
            likes.append([liked.index, liked.value, liked.liked])
            data_source["likes"] = likes

            result.data_source = data_source
            session.add(result)
            session.commit()

    def create_pipeline(self, settings: dict, state: dict, *selecteds):
        """Create the pipeline from settings

        Args:
            settings: the settings of the app
            is_regen: whether the regen button is clicked
            selected: the list of file ids that will be served as context. If None, then
                consider using all files

        Returns:
            the pipeline objects
        """
        # get retrievers
        retrievers = []
        for index in self._app.index_manager.indices:
            index_selected = []
            if index.selector != -1:
                index_selected = selecteds[index.selector]
            iretrievers = index.get_retriever_pipelines(settings, index_selected)
            retrievers += iretrievers

        reasoning_mode = settings["reasoning.use"]
        reasoning_cls = reasonings[reasoning_mode]
        pipeline = reasoning_cls.get_pipeline(settings, state, retrievers)

        return pipeline

    async def chat_fn(self, conversation_id, chat_history, settings, state, *selecteds):
        """Chat function"""
        chat_input = chat_history[-1][0]
        chat_history = chat_history[:-1]

        queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        # construct the pipeline
        state["is_regen"] = False
        pipeline = self.create_pipeline(settings, state, *selecteds)
        pipeline.set_output_queue(queue)

        asyncio.create_task(pipeline(chat_input, conversation_id, chat_history))
        text, refs = "", ""
        settings["reasoning.options.simple.already_rewrite"] = False

        len_ref = -1  # for logging purpose

        while True:
            try:
                response = queue.get_nowait()
            except Exception:
                yield "", chat_history + [(chat_input, text or "Thinking ...")], refs
                continue

            if response is None:
                queue.task_done()
                print("Chat completed")
                break

            if "output" in response:
                text += response["output"]
            if "evidence" in response:
                if response["evidence"] is None:
                    refs = ""
                else:
                    refs += response["evidence"]

            if len(refs) > len_ref:
                print(f"Len refs: {len(refs)}")
                len_ref = len(refs)

        yield "", chat_history + [(chat_input, text)], refs

    async def regen_fn(
        self, conversation_id, chat_history, settings, state, *selecteds
    ):
        """Chat function"""
        if len(chat_history) == 0:
            gr.Warning("Can't regenerate in an empty conversation")
            yield "", chat_history, ""
            return

        chat_input = chat_history[-1][0]
        if state.get("is_regen", False):
            chat_history = chat_history[:-1]

        queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        # construct the pipeline
        state["is_regen"] = True
        pipeline = self.create_pipeline(settings, state, *selecteds)
        pipeline.set_output_queue(queue)

        asyncio.create_task(pipeline(chat_input, conversation_id, chat_history))
        text, refs = "", ""
        settings["reasoning.options.simple.already_rewrite"] = True

        len_ref = -1  # for logging purpose

        while True:
            try:
                response = queue.get_nowait()
            except Exception:
                yield "", chat_history + [(chat_input, text or "Thinking ...")], refs
                continue

            if response is None:
                queue.task_done()
                print("Chat completed")
                break

            if "output" in response:
                text += response["output"]
            if "evidence" in response:
                if response["evidence"] is None:
                    refs = ""
                else:
                    refs += response["evidence"]
            if "chat_input" in response:
                chat_input = response["chat_input"]

            if len(refs) > len_ref:
                print(f"Len refs: {len(refs)}")
                len_ref = len(refs)

        yield "", chat_history + [(chat_input, text)], refs
