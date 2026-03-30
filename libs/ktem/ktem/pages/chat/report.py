from typing import Optional

import gradio as gr
from ktem.app import BasePage
from ktem.db.models import IssueReport, engine
from sqlmodel import Session

from ...utils.lang import get_ui_text
from ..settings import get_current_language


class ReportIssue(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        _lang = get_current_language()
        with gr.Accordion(
            label=get_ui_text("feedback.feedback", _lang),
            open=False,
            elem_id="report-accordion",
        ):
            self.correctness = gr.Radio(
                choices=[
                    (get_ui_text("feedback.answer_correct", _lang), "correct"),
                    (get_ui_text("feedback.answer_incorrect", _lang), "incorrect"),
                ],
                label=get_ui_text("feedback.correctness", _lang),
            )
            self.issues = gr.CheckboxGroup(
                choices=[
                    (get_ui_text("feedback.answer_offensive", _lang), "offensive"),
                    (get_ui_text("feedback.evidence_incorrect", _lang), "wrong-evidence"),
                ],
                label=get_ui_text("feedback.other_issue", _lang),
            )
            self.more_detail = gr.Textbox(
                placeholder=get_ui_text("feedback.more_detail", _lang),
                container=False,
                lines=3,
            )
            gr.Markdown(
                "This will send the current chat and the user settings to "
                "help with investigation"
            )
            self.report_btn = gr.Button(get_ui_text("feedback.report", _lang))

    def report(
        self,
        correctness: str,
        issues: list[str],
        more_detail: str,
        conv_id: str,
        chat_history: list,
        settings: dict,
        user_id: Optional[int],
        info_panel: str,
        chat_state: dict,
        *selecteds,
    ):
        selecteds_ = {}
        for index in self._app.index_manager.indices:
            if index.selector is not None:
                if isinstance(index.selector, int):
                    selecteds_[str(index.id)] = selecteds[index.selector]
                elif isinstance(index.selector, tuple):
                    selecteds_[str(index.id)] = [selecteds[_] for _ in index.selector]
                else:
                    print(f"Unknown selector type: {index.selector}")

        with Session(engine) as session:
            issue = IssueReport(
                issues={
                    "correctness": correctness,
                    "issues": issues,
                    "more_detail": more_detail,
                },
                chat={
                    "conv_id": conv_id,
                    "chat_history": chat_history,
                    "info_panel": info_panel,
                    "chat_state": chat_state,
                    "selecteds": selecteds_,
                },
                settings=settings,
                user=user_id,
            )
            session.add(issue)
            session.commit()
        _lang = get_current_language()
        gr.Info(get_ui_text("feedback.thank_you_feedback", _lang))
