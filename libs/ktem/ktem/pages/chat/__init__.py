import asyncio
import json
import re
from copy import deepcopy
from typing import Optional

import gradio as gr
from ktem.app import BasePage
from ktem.components import reasonings
from ktem.db.models import Conversation, engine
from ktem.index.file.ui import File
from ktem.reasoning.prompt_optimization.suggest_conversation_name import (
    SuggestConvNamePipeline,
)
from ktem.reasoning.prompt_optimization.suggest_followup_chat import (
    SuggestFollowupQuesPipeline,
)
from plotly.io import from_json
from sqlmodel import Session, select
from theflow.settings import settings as flowsettings

from kotaemon.base import Document
from kotaemon.indices.ingests.extensions import extension_manager

from ...utils import SUPPORTED_LANGUAGE_MAP, get_file_names_regex
from .chat_panel import ChatPanel
from .common import STATE
from .control import ConversationControl
from .report import ReportIssue

# from kotaemon.indices.ingests.files import KH_DEFAULT_FILE_EXTRACTORS


DEFAULT_SETTING = "(default)"
INFO_PANEL_SCALES = {True: 8, False: 4}

chat_input_focus_js = """
function() {
    let chatInput = document.querySelector("#chat-input textarea");
    chatInput.focus();
}
"""

pdfview_js = """
function() {
    // Get all links and attach click event
    var links = document.getElementsByClassName("pdf-link");
    for (var i = 0; i < links.length; i++) {
        links[i].onclick = openModal;
    }

    // Get all citation links and attach click event
    var links = document.querySelectorAll("a.citation");
    for (var i = 0; i < links.length; i++) {
        links[i].onclick = scrollToCitation;
    }

    var mindmap_el = document.getElementById('mindmap');

    if (mindmap_el) {
        var output = svgPanZoom(mindmap_el);
        const svg = mindmap_el.cloneNode(true);

        function on_svg_export(event) {
            event.preventDefault(); // Prevent the default link behavior
            // convert to a valid XML source
            const as_text = new XMLSerializer().serializeToString(svg);
            // store in a Blob
            const blob = new Blob([as_text], { type: "image/svg+xml" });
            // create an URI pointing to that blob
            const url = URL.createObjectURL(blob);
            const win = open(url);
            // so the Garbage Collector can collect the blob
            win.onload = (evt) => URL.revokeObjectURL(url);
        }

        var link = document.getElementById("mindmap-toggle");
        if (link) {
            link.onclick = function(event) {
                event.preventDefault(); // Prevent the default link behavior
                var div = document.getElementById("mindmap-wrapper");
                if (div) {
                    var currentHeight = div.style.height;
                    if (currentHeight === '400px') {
                        var contentHeight = div.scrollHeight;
                        div.style.height = contentHeight + 'px';
                    } else {
                        div.style.height = '400px'
                    }
                }
            };
        }

        var link = document.getElementById("mindmap-export");
        if (link) {
            link.addEventListener('click', on_svg_export);
        }
    }

    return [links.length]
}
"""


class ChatPage(BasePage):
    def __init__(self, app):
        self._app = app
        self._indices_input = []

        self.on_building_ui()

        self._preview_links = gr.State(value=None)
        self._reasoning_type = gr.State(value=None)
        self._conversation_renamed = gr.State(value=False)
        self._use_suggestion = gr.State(
            value=getattr(flowsettings, "KH_FEATURE_CHAT_SUGGESTION", False)
        )
        self._info_panel_expanded = gr.State(value=True)

    def on_building_ui(self):
        with gr.Row():
            self.state_chat = gr.State(STATE)
            self.state_retrieval_history = gr.State([])
            self.state_plot_history = gr.State([])
            self.state_plot_panel = gr.State(None)
            self.first_selector_choices = gr.State(None)

            with gr.Column(scale=1, elem_id="conv-settings-panel") as self.conv_column:
                self.chat_control = ConversationControl(self._app)

                for index_id, index in enumerate(self._app.index_manager.indices):
                    index.selector = None
                    index_ui = index.get_selector_component_ui()
                    if not index_ui:
                        # the index doesn't have a selector UI component
                        continue

                    index_ui.unrender()  # need to rerender later within Accordion
                    with gr.Accordion(label=index.name, open=index_id < 1):
                        index_ui.render()
                        gr_index = index_ui.as_gradio_component()

                        # get the file selector choices for the first index
                        if index_id == 0:
                            self.first_selector_choices = index_ui.selector_choices

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
                            # file_types=list(KH_DEFAULT_FILE_EXTRACTORS.keys()),
                            file_types=extension_manager.get_supported_extensions(),
                            file_count="multiple",
                            container=True,
                            show_label=False,
                            elem_id="quick-file",
                        )
                        self.quick_urls = gr.Textbox(
                            placeholder="Or paste URLs here",
                            lines=1,
                            container=False,
                            show_label=False,
                            elem_id="quick-url",
                        )
                        self.quick_file_upload_status = gr.Markdown()

                self.report_issue = ReportIssue(self._app)

            with gr.Column(scale=6, elem_id="chat-area"):
                self.chat_panel = ChatPanel(self._app)

                with gr.Row():
                    with gr.Accordion(
                        label="Chat settings",
                        elem_id="chat-settings-expand",
                        open=False,
                    ):
                        with gr.Row(elem_id="quick-setting-labels"):
                            gr.HTML("Reasoning method")
                            gr.HTML("Model")
                            gr.HTML("Language")
                            gr.HTML("Suggestion")

                        with gr.Row():
                            reasoning_type_values = [
                                (DEFAULT_SETTING, DEFAULT_SETTING)
                            ] + self._app.default_settings.reasoning.settings[
                                "use"
                            ].choices
                            self.reasoning_type = gr.Dropdown(
                                choices=reasoning_type_values,
                                value=DEFAULT_SETTING,
                                container=False,
                                show_label=False,
                            )
                            self.model_type = gr.Dropdown(
                                choices=self._app.default_settings.reasoning.options[
                                    "simple"
                                ]
                                .settings["llm"]
                                .choices,
                                value="",
                                container=False,
                                show_label=False,
                            )
                            self.language = gr.Dropdown(
                                choices=[
                                    (DEFAULT_SETTING, DEFAULT_SETTING),
                                ]
                                + self._app.default_settings.reasoning.settings[
                                    "lang"
                                ].choices,
                                value=DEFAULT_SETTING,
                                container=False,
                                show_label=False,
                            )
                            self.use_chat_suggestion = gr.Checkbox(
                                label="Chat suggestion",
                                container=False,
                                elem_id="use-suggestion-checkbox",
                            )

                            self.citation = gr.Dropdown(
                                choices=[
                                    (DEFAULT_SETTING, DEFAULT_SETTING),
                                ]
                                + self._app.default_settings.reasoning.options["simple"]
                                .settings["highlight_citation"]
                                .choices,
                                value=DEFAULT_SETTING,
                                container=False,
                                show_label=False,
                                interactive=True,
                                elem_id="citation-dropdown",
                            )

                            self.use_mindmap = gr.State(value=DEFAULT_SETTING)
                            self.use_mindmap_check = gr.Checkbox(
                                label="Mindmap (default)",
                                container=False,
                                elem_id="use-mindmap-checkbox",
                            )

            with gr.Column(
                scale=INFO_PANEL_SCALES[False], elem_id="chat-info-panel"
            ) as self.info_column:
                with gr.Accordion(
                    label="Information panel", open=True, elem_id="info-expand"
                ):
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
        self.followup_questions = self.chat_control.chat_suggestion.examples
        self.followup_questions_ui = self.chat_control.chat_suggestion.accordion

        chat_event = (
            gr.on(
                triggers=[
                    self.chat_panel.text_input.submit,
                ],
                fn=self.submit_msg,
                inputs=[
                    self.chat_panel.text_input,
                    self.chat_panel.chatbot,
                    self._app.user_id,
                    self.chat_control.conversation_id,
                    self.chat_control.conversation_rn,
                    self.first_selector_choices,
                ],
                outputs=[
                    self.chat_panel.text_input,
                    self.chat_panel.chatbot,
                    self.chat_control.conversation_id,
                    self.chat_control.conversation,
                    self.chat_control.conversation_rn,
                    # file selector from the first index
                    self._indices_input[0],
                    self._indices_input[1],
                ],
                concurrency_limit=20,
                show_progress="hidden",
            )
            .success(
                fn=self.chat_fn,
                inputs=[
                    self.chat_control.conversation_id,
                    self.chat_panel.chatbot,
                    self._app.settings_state,
                    self._reasoning_type,
                    self.model_type,
                    self.use_mindmap,
                    self.citation,
                    self.language,
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
            )
            .then(
                fn=lambda: True,
                inputs=None,
                outputs=[self._preview_links],
                js=pdfview_js,
            )
            .success(
                fn=self.check_and_suggest_name_conv,
                inputs=self.chat_panel.chatbot,
                outputs=[
                    self.chat_control.conversation_rn,
                    self._conversation_renamed,
                ],
            )
            .success(
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
            )
        )

        # chat suggestion toggle
        chat_event = chat_event.success(
            fn=self.suggest_chat_conv,
            inputs=[
                self._app.settings_state,
                self.chat_panel.chatbot,
                self._use_suggestion,
            ],
            outputs=[
                self.followup_questions_ui,
                self.followup_questions,
            ],
            show_progress="hidden",
        )
        # .success(
        #     self.chat_control.persist_chat_suggestions,
        #     inputs=[
        #         self.chat_control.conversation_id,
        #         self.followup_questions,
        #         self._use_suggestion,
        #         self._app.user_id,
        #     ],
        #     show_progress="hidden",
        # )

        # final data persist
        chat_event = chat_event.then(
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
        )

        self.chat_control.btn_info_expand.click(
            fn=lambda is_expanded: (
                gr.update(scale=INFO_PANEL_SCALES[is_expanded]),
                not is_expanded,
            ),
            inputs=self._info_panel_expanded,
            outputs=[self.info_column, self._info_panel_expanded],
        )
        self.chat_control.btn_chat_expand.click(
            fn=None, inputs=None, js="function() {toggleChatColumn();}"
        )

        self.chat_panel.chatbot.like(
            fn=self.is_liked,
            inputs=[self.chat_control.conversation_id],
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
                self.followup_questions,
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
            fn=None,
            inputs=None,
            js=chat_input_focus_js,
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
                self.followup_questions,
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
                self.followup_questions,
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
            fn=lambda: True,
            inputs=None,
            outputs=[self._preview_links],
            js=pdfview_js,
        ).then(
            fn=None, inputs=None, outputs=None, js=chat_input_focus_js
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
            fn=lambda: True,
            inputs=None,
            outputs=[self._preview_links],
            js=pdfview_js,
        ).then(
            fn=None, inputs=None, outputs=None, js=chat_input_focus_js
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
        self.reasoning_type.change(
            self.reasoning_changed,
            inputs=[self.reasoning_type],
            outputs=[self._reasoning_type],
        )
        self.use_mindmap_check.change(
            lambda x: (x, gr.update(label="Mindmap " + ("(on)" if x else "(off)"))),
            inputs=[self.use_mindmap_check],
            outputs=[self.use_mindmap, self.use_mindmap_check],
            show_progress="hidden",
        )
        self.use_chat_suggestion.change(
            lambda x: (x, gr.update(visible=x)),
            inputs=[self.use_chat_suggestion],
            outputs=[self._use_suggestion, self.followup_questions_ui],
            show_progress="hidden",
        )
        self.chat_control.conversation_id.change(
            lambda: gr.update(visible=False),
            outputs=self.plot_panel,
        )

        self.followup_questions.select(
            self.chat_control.chat_suggestion.select_example,
            outputs=[self.chat_panel.text_input],
            show_progress="hidden",
        ).then(
            fn=None,
            inputs=None,
            outputs=None,
            js=chat_input_focus_js,
        )

    def submit_msg(
        self,
        chat_input,
        chat_history,
        user_id,
        conv_id,
        conv_name,
        first_selector_choices,
    ):
        """Submit a message to the chatbot"""
        if not chat_input:
            raise ValueError("Input is empty")

        chat_input_text = chat_input.get("text", "")

        # get all file names with pattern @"filename" in input_str
        file_names, chat_input_text = get_file_names_regex(chat_input_text)
        first_selector_choices_map = {
            item[0]: item[1] for item in first_selector_choices
        }
        file_ids = []

        if file_names:
            for file_name in file_names:
                file_id = first_selector_choices_map.get(file_name)
                if file_id:
                    file_ids.append(file_id)

        if file_ids:
            selector_output = ["select", file_ids]
        else:
            selector_output = [gr.update(), gr.update()]

        # check if regen mode is active
        if chat_input_text:
            chat_history = chat_history + [(chat_input_text, None)]
        else:
            if not chat_history:
                raise gr.Error("Empty chat")

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

        return [
            {},
            chat_history,
            new_conv_id,
            conv_update,
            new_conv_name,
        ] + selector_output

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
        try:
            retrieval_content, plot_content = (
                retrieval_history[index],
                plot_history[index],
            )
        except IndexError:
            retrieval_content, plot_content = gr.update(), None

        return retrieval_content, plot_content

    def create_pipeline(
        self,
        settings: dict,
        session_reasoning_type: str,
        session_llm: str,
        session_use_mindmap: bool | str,
        session_use_citation: str,
        session_language: str,
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
        print(
            "Session reasoning type",
            session_reasoning_type,
            "use mindmap",
            session_use_mindmap,
            "use citation",
            session_use_citation,
            "language",
            session_language,
        )
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
        if llm_setting_key in settings and session_llm not in (
            DEFAULT_SETTING,
            None,
            "",
        ):
            settings[llm_setting_key] = session_llm

        if session_use_mindmap not in (DEFAULT_SETTING, None):
            settings["reasoning.options.simple.create_mindmap"] = session_use_mindmap

        if session_use_citation not in (DEFAULT_SETTING, None):
            settings[
                "reasoning.options.simple.highlight_citation"
            ] = session_use_citation

        if session_language not in (DEFAULT_SETTING, None):
            settings["reasoning.lang"] = session_language

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
        use_mind_map,
        use_citation,
        language,
        state,
        user_id,
        *selecteds,
    ):
        """Chat function"""
        chat_input, chat_output = chat_history[-1]
        chat_history = chat_history[:-1]

        # if chat_input is empty, assume regen mode
        if chat_output:
            state["app"]["regen"] = True

        queue: asyncio.Queue[Optional[dict]] = asyncio.Queue()

        # construct the pipeline
        pipeline, reasoning_state = self.create_pipeline(
            settings,
            reasoning_type,
            llm_type,
            use_mind_map,
            use_citation,
            language,
            state,
            user_id,
            *selecteds,
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

    def check_and_suggest_name_conv(self, chat_history):
        suggest_pipeline = SuggestConvNamePipeline()
        new_name = gr.update()
        renamed = False

        # check if this is a newly created conversation
        if len(chat_history) == 1:
            suggested_name = suggest_pipeline(chat_history).text
            suggested_name = suggested_name.replace('"', "").replace("'", "")[:40]
            new_name = gr.update(value=suggested_name)
            renamed = True

        return new_name, renamed

    def suggest_chat_conv(self, settings, chat_history, use_suggestion):
        if use_suggestion:
            suggest_pipeline = SuggestFollowupQuesPipeline()
            suggest_pipeline.lang = SUPPORTED_LANGUAGE_MAP.get(
                settings["reasoning.lang"], "English"
            )
            suggested_questions = []

            if len(chat_history) >= 1:
                suggested_resp = suggest_pipeline(chat_history).text
                if ques_res := re.search(
                    r"\[(.*?)\]", re.sub("\n", "", suggested_resp)
                ):
                    ques_res_str = ques_res.group()
                    try:
                        suggested_questions = json.loads(ques_res_str)
                        suggested_questions = [[x] for x in suggested_questions]
                    except Exception:
                        pass

            return gr.update(visible=True), suggested_questions

        return gr.update(visible=False), gr.update()
