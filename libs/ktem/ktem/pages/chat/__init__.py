import asyncio
import csv
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Optional

import gradio as gr
from filelock import FileLock
from ktem.app import BasePage
from ktem.components import reasonings
from ktem.db.models import Conversation, engine
from ktem.index.file.ui import File
from ktem.reasoning.prompt_optimization.suggest_conversation_name import (
    SuggestConvNamePipeline,
)
from plotly.io import from_json
from sqlmodel import Session, select
from theflow.settings import settings as flowsettings

from kotaemon.base import Document
from kotaemon.indices.ingests.files import KH_DEFAULT_FILE_EXTRACTORS

from .chat_panel import ChatPanel
from .chat_suggestion import ChatSuggestion
from .common import STATE
from .control import ConversationControl
from .report import ReportIssue

DEFAULT_SETTING = "(default)"
INFO_PANEL_SCALES = {True: 8, False: 4}


pdfview_js = """
function() {
    // Get all links and attach click event
    var links = document.getElementsByClassName("pdf-link");
    for (var i = 0; i < links.length; i++) {
        links[i].onclick = openModal;
    }
}
"""


class ChatPage(BasePage):
    def __init__(self, app):
        self._app = app
        self._indices_input = []

        self.on_building_ui()
        self._reasoning_type = gr.State(value=None)
        self._llm_type = gr.State(value=None)
        self._conversation_renamed = gr.State(value=False)
        self.info_panel_expanded = gr.State(value=True)

    def on_building_ui(self):
        with gr.Row():
            self.state_chat = gr.State(STATE)
            self.state_retrieval_history = gr.State([])
            self.state_chat_history = gr.State([])
            self.state_plot_history = gr.State([])
            self.state_settings = gr.State({})
            self.state_info_panel = gr.State("")
            self.state_plot_panel = gr.State(None)

            with gr.Column(scale=1, elem_id="conv-settings-panel") as self.conv_column:
                self.chat_control = ConversationControl(self._app)

                if getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION", False):
                    self.chat_suggestion = ChatSuggestion(self._app)

                for index_id, index in enumerate(self._app.index_manager.indices):
                    index.selector = None
                    index_ui = index.get_selector_component_ui()
                    if not index_ui:
                        # the index doesn't have a selector UI component
                        continue

                    index_ui.unrender()  # need to rerender later within Accordion
                    with gr.Accordion(
                        label=f"{index.name} Collection", open=index_id < 1
                    ):
                        index_ui.render()
                        gr_index = index_ui.as_gradio_component()
                        if gr_index:
                            if isinstance(gr_index, list):
                                index.selector = tuple(
                                    range(
                                        len(self._indices_input),
                                        len(self._indices_input) + len(gr_index),
                                    )
                                )
                                index.default_selector = index_ui.default()
                                self._indices_input.extend(gr_index)
                            else:
                                index.selector = len(self._indices_input)
                                index.default_selector = index_ui.default()
                                self._indices_input.append(gr_index)
                        setattr(self, f"_index_{index.id}", index_ui)

                if len(self._app.index_manager.indices) > 0:
                    with gr.Accordion(label="Quick Upload") as _:
                        self.quick_file_upload = File(
                            file_types=list(KH_DEFAULT_FILE_EXTRACTORS.keys()),
                            file_count="multiple",
                            container=True,
                            show_label=False,
                        )
                        self.quick_file_upload_status = gr.Markdown()

                self.report_issue = ReportIssue(self._app)

            with gr.Column(scale=6, elem_id="chat-area"):
                self.chat_panel = ChatPanel(self._app)

                with gr.Row():
                    with gr.Accordion(label="Chat settings", open=False):
                        # a quick switch for reasoning type option
                        with gr.Row():
                            gr.HTML("Reasoning method")
                            gr.HTML("Model")

                        with gr.Row():
                            reasoning_type_values = [
                                (DEFAULT_SETTING, DEFAULT_SETTING)
                            ] + self._app.default_settings.reasoning.settings[
                                "use"
                            ].choices
                            self.reasoning_types = gr.Dropdown(
                                choices=reasoning_type_values,
                                value=DEFAULT_SETTING,
                                container=False,
                                show_label=False,
                            )
                            self.model_types = gr.Dropdown(
                                choices=self._app.default_settings.reasoning.options[
                                    "simple"
                                ]
                                .settings["llm"]
                                .choices,
                                value="",
                                container=False,
                                show_label=False,
                            )

            with gr.Column(
                scale=INFO_PANEL_SCALES[False], elem_id="chat-info-panel"
            ) as self.info_column:
                with gr.Accordion(label="Information panel", open=True):
                    self.modal = gr.HTML("<div id='pdf-modal'></div>")
                    self.plot_panel = gr.Plot(visible=False)
                    self.info_panel = gr.HTML(elem_id="html-info-panel")

    def _json_to_plot(self, json_dict: dict | None):
        if json_dict:
            plot = from_json(json_dict)
            plot = gr.update(visible=True, value=plot)
        else:
            plot = gr.update(visible=False)
        return plot

    def on_register_events(self):
        gr.on(
            triggers=[
                self.chat_panel.text_input.submit,
                self.chat_panel.submit_btn.click,
            ],
            fn=self.submit_msg,
            inputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self._app.user_id,
                self.chat_control.conversation_id,
                self.chat_control.conversation_rn,
            ],
            outputs=[
                self.chat_panel.text_input,
                self.chat_panel.chatbot,
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
            ],
            concurrency_limit=20,
            show_progress="hidden",
        ).success(
            fn=self.chat_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self._reasoning_type,
                self._llm_type,
                self.state_chat,
                self._app.user_id,
            ]
            + self._indices_input,
            outputs=[
                self.chat_panel.chatbot,
                self.info_panel,
                self.plot_panel,
                self.state_plot_panel,
                self.state_chat,
            ],
            concurrency_limit=20,
            show_progress="minimal",
        ).success(
            fn=self.backup_original_info,
            inputs=[
                self.chat_panel.chatbot,
                self._app.settings_state,
                self.info_panel,
                self.state_chat_history,
            ],
            outputs=[
                self.state_chat_history,
                self.state_settings,
                self.state_info_panel,
            ],
        ).then(
            fn=self.persist_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self._app.user_id,
                self.info_panel,
                self.state_plot_panel,
                self.state_retrieval_history,
                self.state_plot_history,
                self.chat_panel.chatbot,
                self.state_chat,
            ]
            + self._indices_input,
            outputs=[
                self.state_retrieval_history,
                self.state_plot_history,
            ],
            concurrency_limit=20,
        ).success(
            fn=self.check_and_suggest_name_conv,
            inputs=self.chat_panel.chatbot,
            outputs=[
                self.chat_control.conversation_rn,
                self._conversation_renamed,
            ],
        ).success(
            self.chat_control.rename_conv,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation_rn,
                self._conversation_renamed,
                self._app.user_id,
            ],
            outputs=[
                self.chat_control.conversation,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
            ],
            show_progress="hidden",
        ).then(
            fn=None, inputs=None, outputs=None, js=pdfview_js
        )

        self.chat_panel.regen_btn.click(
            fn=self.regen_fn,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self._reasoning_type,
                self._llm_type,
                self.state_chat,
                self._app.user_id,
            ]
            + self._indices_input,
            outputs=[
                self.chat_panel.chatbot,
                self.info_panel,
                self.plot_panel,
                self.state_plot_panel,
                self.state_chat,
            ],
            concurrency_limit=20,
            show_progress="minimal",
        ).then(
            fn=self.persist_data_source,
            inputs=[
                self.chat_control.conversation_id,
                self._app.user_id,
                self.info_panel,
                self.state_plot_panel,
                self.state_retrieval_history,
                self.state_plot_history,
                self.chat_panel.chatbot,
                self.state_chat,
            ]
            + self._indices_input,
            outputs=[
                self.state_retrieval_history,
                self.state_plot_history,
            ],
            concurrency_limit=20,
        ).success(
            fn=self.check_and_suggest_name_conv,
            inputs=self.chat_panel.chatbot,
            outputs=[
                self.chat_control.conversation_rn,
                self._conversation_renamed,
            ],
        ).success(
            self.chat_control.rename_conv,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation_rn,
                self._conversation_renamed,
                self._app.user_id,
            ],
            outputs=[
                self.chat_control.conversation,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
            ],
            show_progress="hidden",
        ).then(
            fn=None, inputs=None, outputs=None, js=pdfview_js
        )

        self.chat_control.btn_info_expand.click(
            fn=lambda is_expanded: (
                gr.update(scale=INFO_PANEL_SCALES[is_expanded]),
                not is_expanded,
            ),
            inputs=self.info_panel_expanded,
            outputs=[self.info_column, self.info_panel_expanded],
        )

        self.chat_panel.chatbot.like(
            fn=self.is_liked,
            inputs=[self.chat_control.conversation_id],
            outputs=None,
        ).success(
            self.save_log,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_panel.chatbot,
                self._app.settings_state,
                self.info_panel,
                self.state_chat_history,
                self.state_settings,
                self.state_info_panel,
                gr.State(getattr(flowsettings, "KH_APP_DATA_DIR", "logs")),
            ],
            outputs=None,
        )

        self.chat_control.btn_new.click(
            self.chat_control.new_conv,
            inputs=self._app.user_id,
            outputs=[self.chat_control.conversation_id, self.chat_control.conversation],
            show_progress="hidden",
        ).then(
            self.chat_control.select_conv,
            inputs=[self.chat_control.conversation, self._app.user_id],
            outputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
                self.chat_panel.chatbot,
                self.info_panel,
                self.state_plot_panel,
                self.state_retrieval_history,
                self.state_plot_history,
                self.chat_control.cb_is_public,
                self.state_chat,
            ]
            + self._indices_input,
            show_progress="hidden",
        ).then(
            fn=self._json_to_plot,
            inputs=self.state_plot_panel,
            outputs=self.plot_panel,
        )

        self.chat_control.btn_del.click(
            lambda id: self.toggle_delete(id),
            inputs=[self.chat_control.conversation_id],
            outputs=[self.chat_control._new_delete, self.chat_control._delete_confirm],
        )
        self.chat_control.btn_del_conf.click(
            self.chat_control.delete_conv,
            inputs=[self.chat_control.conversation_id, self._app.user_id],
            outputs=[self.chat_control.conversation_id, self.chat_control.conversation],
            show_progress="hidden",
        ).then(
            self.chat_control.select_conv,
            inputs=[self.chat_control.conversation, self._app.user_id],
            outputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
                self.chat_panel.chatbot,
                self.info_panel,
                self.state_plot_panel,
                self.state_retrieval_history,
                self.state_plot_history,
                self.chat_control.cb_is_public,
                self.state_chat,
            ]
            + self._indices_input,
            show_progress="hidden",
        ).then(
            fn=self._json_to_plot,
            inputs=self.state_plot_panel,
            outputs=self.plot_panel,
        ).then(
            lambda: self.toggle_delete(""),
            outputs=[self.chat_control._new_delete, self.chat_control._delete_confirm],
        )
        self.chat_control.btn_del_cnl.click(
            lambda: self.toggle_delete(""),
            outputs=[self.chat_control._new_delete, self.chat_control._delete_confirm],
        )
        self.chat_control.btn_conversation_rn.click(
            lambda: gr.update(visible=True),
            outputs=[
                self.chat_control.conversation_rn,
            ],
        )
        self.chat_control.conversation_rn.submit(
            self.chat_control.rename_conv,
            inputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation_rn,
                gr.State(value=True),
                self._app.user_id,
            ],
            outputs=[
                self.chat_control.conversation,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
            ],
            show_progress="hidden",
        )

        self.chat_control.conversation.select(
            self.chat_control.select_conv,
            inputs=[self.chat_control.conversation, self._app.user_id],
            outputs=[
                self.chat_control.conversation_id,
                self.chat_control.conversation,
                self.chat_control.conversation_rn,
                self.chat_panel.chatbot,
                self.info_panel,
                self.state_plot_panel,
                self.state_retrieval_history,
                self.state_plot_history,
                self.chat_control.cb_is_public,
                self.state_chat,
            ]
            + self._indices_input,
            show_progress="hidden",
        ).then(
            fn=self._json_to_plot,
            inputs=self.state_plot_panel,
            outputs=self.plot_panel,
        ).then(
            lambda: self.toggle_delete(""),
            outputs=[self.chat_control._new_delete, self.chat_control._delete_confirm],
        ).then(
            fn=None, inputs=None, outputs=None, js=pdfview_js
        )

        # evidence display on message selection
        self.chat_panel.chatbot.select(
            self.message_selected,
            inputs=[
                self.state_retrieval_history,
                self.state_plot_history,
            ],
            outputs=[
                self.info_panel,
                self.state_plot_panel,
            ],
        ).then(
            fn=self._json_to_plot,
            inputs=self.state_plot_panel,
            outputs=self.plot_panel,
        ).then(
            fn=None, inputs=None, outputs=None, js=pdfview_js
        )

        self.chat_control.cb_is_public.change(
            self.on_set_public_conversation,
            inputs=[self.chat_control.cb_is_public, self.chat_control.conversation],
            outputs=None,
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
                self.info_panel,
                self.state_chat,
            ]
            + self._indices_input,
            outputs=None,
        )
        self.reasoning_types.change(
            self.reasoning_changed,
            inputs=[self.reasoning_types],
            outputs=[self._reasoning_type],
        )
        self.model_types.change(
            lambda x: x,
            inputs=[self.model_types],
            outputs=[self._llm_type],
        )
        self.chat_control.conversation_id.change(
            lambda: gr.update(visible=False),
            outputs=self.plot_panel,
        )

        if getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION", False):
            self.chat_suggestion.example.select(
                self.chat_suggestion.select_example,
                outputs=[self.chat_panel.text_input],
                show_progress="hidden",
            )

    def submit_msg(self, chat_input, chat_history, user_id, conv_id, conv_name):
        """Submit a message to the chatbot"""
        if not chat_input:
            raise ValueError("Input is empty")

        if not conv_id:
            id_, update = self.chat_control.new_conv(user_id)
            with Session(engine) as session:
                statement = select(Conversation).where(Conversation.id == id_)
                name = session.exec(statement).one().name
                new_conv_id = id_
                conv_update = update
                new_conv_name = name
        else:
            new_conv_id = conv_id
            conv_update = gr.update()
            new_conv_name = conv_name

        return (
            "",
            chat_history + [(chat_input, None)],
            new_conv_id,
            conv_update,
            new_conv_name,
        )

    def toggle_delete(self, conv_id):
        if conv_id:
            return gr.update(visible=False), gr.update(visible=True)
        else:
            return gr.update(visible=True), gr.update(visible=False)

    def on_set_public_conversation(self, is_public, convo_id):
        if not convo_id:
            gr.Warning("No conversation selected")
            return

        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == convo_id)

            result = session.exec(statement).one()
            name = result.name

            if result.is_public != is_public:
                # Only trigger updating when user
                # select different value from the current
                result.is_public = is_public
                session.add(result)
                session.commit()

                gr.Info(
                    f"Conversation: {name} is {'public' if is_public else 'private'}."
                )

    def on_subscribe_public_events(self):
        if self._app.f_user_management:
            self._app.subscribe_event(
                name="onSignIn",
                definition={
                    "fn": self.chat_control.reload_conv,
                    "inputs": [self._app.user_id],
                    "outputs": [self.chat_control.conversation],
                    "show_progress": "hidden",
                },
            )

            self._app.subscribe_event(
                name="onSignOut",
                definition={
                    "fn": lambda: self.chat_control.select_conv("", None),
                    "outputs": [
                        self.chat_control.conversation_id,
                        self.chat_control.conversation,
                        self.chat_control.conversation_rn,
                        self.chat_panel.chatbot,
                        self.info_panel,
                        self.state_plot_panel,
                        self.state_retrieval_history,
                        self.state_plot_history,
                        self.chat_control.cb_is_public,
                    ]
                    + self._indices_input,
                    "show_progress": "hidden",
                },
            )

    def persist_data_source(
        self,
        convo_id,
        user_id,
        retrieval_msg,
        plot_data,
        retrival_history,
        plot_history,
        messages,
        state,
        *selecteds,
    ):
        """Update the data source"""
        if not convo_id:
            gr.Warning("No conversation selected")
            return

        # if not regen, then append the new message
        if not state["app"].get("regen", False):
            retrival_history = retrival_history + [retrieval_msg]
            plot_history = plot_history + [plot_data]
        else:
            if retrival_history:
                print("Updating retrieval history (regen=True)")
                retrival_history[-1] = retrieval_msg
                plot_history[-1] = plot_data

        # reset regen state
        state["app"]["regen"] = False

        selecteds_ = {}
        for index in self._app.index_manager.indices:
            if index.selector is None:
                continue
            if isinstance(index.selector, int):
                selecteds_[str(index.id)] = selecteds[index.selector]
            else:
                selecteds_[str(index.id)] = [selecteds[i] for i in index.selector]

        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == convo_id)
            result = session.exec(statement).one()

            data_source = result.data_source
            old_selecteds = data_source.get("selected", {})
            is_owner = result.user == user_id

            # Write down to db
            result.data_source = {
                "selected": selecteds_ if is_owner else old_selecteds,
                "messages": messages,
                "retrieval_messages": retrival_history,
                "plot_history": plot_history,
                "state": state,
                "likes": deepcopy(data_source.get("likes", [])),
            }
            session.add(result)
            session.commit()

        return retrival_history, plot_history

    def reasoning_changed(self, reasoning_type):
        if reasoning_type != DEFAULT_SETTING:
            # override app settings state (temporary)
            gr.Info("Reasoning type changed to `{}`".format(reasoning_type))
        return reasoning_type

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

    def message_selected(self, retrieval_history, plot_history, msg: gr.SelectData):
        index = msg.index[0]
        return retrieval_history[index], plot_history[index]

    def create_pipeline(
        self,
        settings: dict,
        session_reasoning_type: str,
        session_llm: str,
        state: dict,
        user_id: int,
        *selecteds,
    ):
        """Create the pipeline from settings

        Args:
            settings: the settings of the app
            state: the state of the app
            selected: the list of file ids that will be served as context. If None, then
                consider using all files

        Returns:
            - the pipeline objects
        """
        # override reasoning_mode by temporary chat page state
        print("Session reasoning type", session_reasoning_type)
        print("Session LLM", session_llm)
        reasoning_mode = (
            settings["reasoning.use"]
            if session_reasoning_type in (DEFAULT_SETTING, None)
            else session_reasoning_type
        )
        reasoning_cls = reasonings[reasoning_mode]
        print("Reasoning class", reasoning_cls)
        reasoning_id = reasoning_cls.get_info()["id"]

        settings = deepcopy(settings)
        llm_setting_key = f"reasoning.options.{reasoning_id}.llm"
        if llm_setting_key in settings and session_llm not in (DEFAULT_SETTING, None):
            settings[llm_setting_key] = session_llm

        # get retrievers
        retrievers = []
        for index in self._app.index_manager.indices:
            index_selected = []
            if isinstance(index.selector, int):
                index_selected = selecteds[index.selector]
            if isinstance(index.selector, tuple):
                for i in index.selector:
                    index_selected.append(selecteds[i])
            iretrievers = index.get_retriever_pipelines(
                settings, user_id, index_selected
            )
            retrievers += iretrievers

        # prepare states
        reasoning_state = {
            "app": deepcopy(state["app"]),
            "pipeline": deepcopy(state.get(reasoning_id, {})),
        }

        pipeline = reasoning_cls.get_pipeline(settings, reasoning_state, retrievers)

        return pipeline, reasoning_state

    def chat_fn(
        self,
        conversation_id,
        chat_history,
        settings,
        reasoning_type,
        llm_type,
        state,
        user_id,
        *selecteds,
    ):
        """Chat function"""
        chat_input = chat_history[-1][0]
        chat_history = chat_history[:-1]

        queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        # construct the pipeline
        pipeline, reasoning_state = self.create_pipeline(
            settings, reasoning_type, llm_type, state, user_id, *selecteds
        )
        print("Reasoning state", reasoning_state)
        pipeline.set_output_queue(queue)

        text, refs, plot, plot_gr = "", "", None, gr.update(visible=False)
        msg_placeholder = getattr(
            flowsettings, "KH_CHAT_MSG_PLACEHOLDER", "Thinking ..."
        )
        print(msg_placeholder)
        yield (
            chat_history + [(chat_input, text or msg_placeholder)],
            refs,
            plot_gr,
            plot,
            state,
        )

        for response in pipeline.stream(chat_input, conversation_id, chat_history):

            if not isinstance(response, Document):
                continue

            if response.channel is None:
                continue

            if response.channel == "chat":
                if response.content is None:
                    text = ""
                else:
                    text += response.content

            if response.channel == "info":
                if response.content is None:
                    refs = ""
                else:
                    refs += response.content

            if response.channel == "plot":
                plot = response.content
                plot_gr = self._json_to_plot(plot)

            state[pipeline.get_info()["id"]] = reasoning_state["pipeline"]
            yield (
                chat_history + [(chat_input, text or msg_placeholder)],
                refs,
                plot_gr,
                plot,
                state,
            )

        if not text:
            empty_msg = getattr(
                flowsettings, "KH_CHAT_EMPTY_MSG_PLACEHOLDER", "(Sorry, I don't know)"
            )
            print(f"Generate nothing: {empty_msg}")
            yield (
                chat_history + [(chat_input, text or empty_msg)],
                refs,
                plot_gr,
                plot,
                state,
            )

    def regen_fn(
        self,
        conversation_id,
        chat_history,
        settings,
        reasoning_type,
        llm_type,
        state,
        user_id,
        *selecteds,
    ):
        """Regen function"""
        if not chat_history:
            gr.Warning("Empty chat")
            yield chat_history, "", state
            return

        state["app"]["regen"] = True
        yield from self.chat_fn(
            conversation_id,
            chat_history,
            settings,
            reasoning_type,
            llm_type,
            state,
            user_id,
            *selecteds,
        )

    def check_and_suggest_name_conv(self, chat_history):
        suggest_pipeline = SuggestConvNamePipeline()
        new_name = gr.update()
        renamed = False

        # check if this is a newly created conversation
        if len(chat_history) == 1:
            suggested_name = suggest_pipeline(chat_history).text[:40]
            new_name = gr.update(value=suggested_name)
            renamed = True

        return new_name, renamed

    def backup_original_info(
        self, chat_history, settings, info_pannel, original_chat_history
    ):
        original_chat_history.append(chat_history[-1])
        return original_chat_history, settings, info_pannel

    def save_log(
        self,
        conversation_id,
        chat_history,
        settings,
        info_panel,
        original_chat_history,
        original_settings,
        original_info_panel,
        log_dir,
    ):
        if not Path(log_dir).exists():
            Path(log_dir).mkdir(parents=True)

        lock = FileLock(Path(log_dir) / ".lock")
        # get current date
        today = datetime.now()
        formatted_date = today.strftime("%d%m%Y_%H")

        with Session(engine) as session:
            statement = select(Conversation).where(Conversation.id == conversation_id)
            result = session.exec(statement).one()

            data_source = deepcopy(result.data_source)
            likes = data_source.get("likes", [])
            if not likes:
                return

        feedback = likes[-1][-1]
        message_index = likes[-1][0]

        current_message = chat_history[message_index[0]]
        original_message = original_chat_history[message_index[0]]
        is_original = all(
            [
                current_item == original_item
                for current_item, original_item in zip(
                    current_message, original_message
                )
            ]
        )

        dataframe = [
            [
                conversation_id,
                message_index,
                current_message[0],
                current_message[1],
                chat_history,
                settings,
                info_panel,
                feedback,
                is_original,
                original_message[1],
                original_chat_history,
                original_settings,
                original_info_panel,
            ]
        ]

        with lock:
            log_file = Path(log_dir) / f"{formatted_date}_log.csv"
            is_log_file_exist = log_file.is_file()
            with open(log_file, "a") as f:
                writer = csv.writer(f)
                # write headers
                if not is_log_file_exist:
                    writer.writerow(
                        [
                            "Conversation ID",
                            "Message ID",
                            "Question",
                            "Answer",
                            "Chat History",
                            "Settings",
                            "Evidences",
                            "Feedback",
                            "Original/ Rewritten",
                            "Original Answer",
                            "Original Chat History",
                            "Original Settings",
                            "Original Evidences",
                        ]
                    )

                writer.writerows(dataframe)
