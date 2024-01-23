from typing import Optional

import gradio as gr
from ktem.app import BasePage
from ktem.db.models import IssueReport, engine
from sqlmodel import Session


class ReportIssue(BasePage):
    def __init__(self, app):
        self._app = app
        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(label="Report", open=False):
            self.correctness = gr.Radio(
                choices=[
                    ("The answer is correct", "correct"),
                    ("The answer is incorrect", "incorrect"),
                ],
                label="Correctness:",
            )
            self.issues = gr.CheckboxGroup(
                choices=[
                    ("The answer is offensive", "offensive"),
                    ("The evidence is incorrect", "wrong-evidence"),
                ],
                label="Other issue:",
            )
            self.more_detail = gr.Textbox(
                placeholder="More detail (e.g. how wrong is it, what is the "
                "correct answer, etc...)",
                container=False,
                lines=3,
            )
            gr.Markdown(
                "This will send the current chat and the user settings to "
                "help with investigation"
            )
            self.report_btn = gr.Button("Report")

    def report(
        self,
        correctness: str,
        issues: list[str],
        more_detail: str,
        conv_id: str,
        chat_history: list,
        files: list,
        settings: dict,
        user_id: Optional[int],
    ):
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
                    "files": files,
                },
                settings=settings,
                user=user_id,
            )
            session.add(issue)
            session.commit()
        gr.Info("Thank you for your feedback")
