"""Citation display helpers.

Renders citation evidence into HTML for the Gradio UI.
This logic lives in ktem (app layer) because it depends on
``ktem.utils.render.Render`` which is UI-specific and must
not be imported by the ``kotaemon`` framework layer.
"""

from __future__ import annotations

import logging

from kotaemon.base import Document
from kotaemon.indices.qa.citation_qa import (
    CONTEXT_RELEVANT_WARNING_SCORE,
    AnswerWithContextPipeline,
)

from ktem.utils.render import Render

logger = logging.getLogger(__name__)


def prepare_citations(
    pipeline: AnswerWithContextPipeline,
    answer: Document,
    docs: list[Document],
) -> tuple[list[Document], list[Document]]:
    """Prepare citation documents for UI display.

    Delegates evidence-matching to the framework-level
    ``pipeline.match_evidence_with_context``, then
    renders the results with ``Render``.
    """
    with_citation: list[Document] = []
    without_citation: list[Document] = []
    has_llm_score = any(
        "llm_trulens_score" in doc.metadata for doc in docs
    )

    spans = pipeline.match_evidence_with_context(answer, docs)
    id2docs = {doc.doc_id: doc for doc in docs}
    not_detected = set(id2docs.keys()) - set(spans.keys())

    for _id, ss in spans.items():
        if not ss:
            not_detected.add(_id)
            continue
        cur_doc = id2docs[_id]
        highlight_text = ""

        ss = sorted(ss, key=lambda x: x["start"])
        last_end = 0
        text = cur_doc.text[: ss[0]["start"]]

        for idx, span in enumerate(ss):
            span_start = max(last_end, span["start"])
            span_end = max(last_end, span["end"])

            to_highlight = cur_doc.text[span_start:span_end]
            last_end = span_end

            highlight_text += (
                (" " if highlight_text else "") + to_highlight
            )

            span_idx = span.get("idx", None)
            if span_idx is not None:
                to_highlight = f"\u3010{span_idx}\u3011" + to_highlight

            text += Render.highlight(
                to_highlight,
                elem_id=(
                    str(span_idx) if span_idx is not None else None
                ),
            )
            if idx < len(ss) - 1:
                text += cur_doc.text[
                    span["end"] : ss[idx + 1]["start"]
                ]

        text += cur_doc.text[ss[-1]["end"] :]
        with_citation.append(
            Document(
                channel="info",
                content=Render.collapsible_with_header_score(
                    cur_doc,
                    override_text=text,
                    highlight_text=highlight_text,
                    open_collapsible=True,
                ),
            )
        )

    logger.info("Got %d cited docs", len(with_citation))

    sorted_not_detected = sorted(
        not_detected,
        key=lambda id_: id2docs[id_].metadata.get(
            "llm_trulens_score", 0.0
        ),
        reverse=True,
    )

    for id_ in sorted_not_detected:
        doc = id2docs[id_]
        doc_score = doc.metadata.get("llm_trulens_score", 0.0)
        is_open = not has_llm_score or (
            doc_score > CONTEXT_RELEVANT_WARNING_SCORE
        )
        without_citation.append(
            Document(
                channel="info",
                content=Render.collapsible_with_header_score(
                    doc, open_collapsible=is_open
                ),
            )
        )
    return with_citation, without_citation
