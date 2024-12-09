import logging

import gradio as gr
from ktem.app import BasePage
from ktem.reasoning.prompt_optimization.verify_answer import (
    verify_answer_groundedness_azure,
)
from ktem.reasoning.simple import AnswerWithContextPipeline
from ktem.utils.render import Render

from kotaemon.base import Document

logger = logging.getLogger(__name__)


class VerificationPage(BasePage):
    """Verify the groundedness of the answer"""

    def __init__(self, app):
        self._app = app

        self.on_building_ui()

    def on_building_ui(self):
        with gr.Accordion(
            "Verification Result",
            visible=False,
        ) as self.verification_ui:
            self.verification_result = gr.HTML()
            self.close_button = gr.Button(
                "Close",
                variant="secondary",
            )

    def on_register_events(self):
        self.close_button.click(
            fn=lambda: gr.update(visible=False),
            outputs=[self.verification_ui],
        )

    def highlight_spans(self, text, spans):
        spans = sorted(spans, key=lambda x: x["start"])
        highlighted_text = text[: spans[0]["start"]]
        for idx, span in enumerate(spans):
            to_highlight = text[span["start"] : span["end"]]
            highlighted_text += Render.highlight(to_highlight)
            if idx < len(spans) - 1:
                highlighted_text += text[span["end"] : spans[idx + 1]["start"]]
        highlighted_text += text[spans[-1]["end"] :]

        return highlighted_text

    def verify_answer(self, chat_history, retrieval_history):
        if len(chat_history) < 1:
            raise gr.Error("Empty chat.")

        query = chat_history[-1][0]
        answer = chat_history[-1][1]

        last_evidence = retrieval_history[-1]
        text_only_evidence, _ = AnswerWithContextPipeline.extract_evidence_images(
            last_evidence
        )

        gr.Info("Verifying the groundedness of the answer. Please wait...")
        result = verify_answer_groundedness_azure(query, answer, [text_only_evidence])

        verification_output = "<h4>Trust score: {:.2f}</h4>".format(
            1 - result["ungroundedPercentage"]
        )
        verification_output += "<h4>Claims that might be incorrect</h4>"
        spans = [
            {
                "start": claim["offset"]["codePoint"],
                "end": claim["offset"]["codePoint"] + claim["length"]["codePoint"],
            }
            for claim in result["ungroundedDetails"]
        ]
        highlighted_text = self.highlight_spans(answer, spans)
        highlighted_text = highlighted_text.replace("\n", "<br>")
        verification_output += f"<div>{highlighted_text}</div>"

        verification_output += "<h4>Rationale</h4>"
        print(verification_output)
        rationale = ""

        for claim in result["ungroundedDetails"]:
            rationale += Render.collapsible_with_header(
                Document(text=claim["reason"], metadata={"file_name": claim["text"]})
            )

        verification_output += f"<div><b>{rationale}</b></div>"

        return gr.update(visible=True), verification_output
