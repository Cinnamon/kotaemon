from __future__ import annotations

import html
import logging
from collections.abc import Callable
from typing import Any

import tiktoken

from kotaemon.base import BaseComponent, Document, RetrievedDocument
from kotaemon.indices.knowledge.retrieval.trace import trace_event, trace_update
from kotaemon.indices.splitters import TokenSplitter

EVIDENCE_MODE_TEXT = 0
EVIDENCE_MODE_TABLE = 1
EVIDENCE_MODE_CHATBOT = 2
EVIDENCE_MODE_FIGURE = 3

logger = logging.getLogger(__name__)


def _first_present(*values):
    return next((value for value in values if value is not None and value != ""), None)


def _plain_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " / ".join(
            str(part) for part in value if part is not None and part != ""
        )
    return str(value)


def _source_text(document: RetrievedDocument) -> str:
    return document.text if isinstance(document.text, str) else str(document.text or "")


def _body_from_metadata(
    document: RetrievedDocument, metadata_key: str | None = None
) -> str:
    """Use alternate evidence only when citations can map it into source text."""
    source_text = _source_text(document)
    candidate = (document.metadata or {}).get(metadata_key) if metadata_key else None
    if isinstance(candidate, str) and candidate and candidate in source_text:
        return candidate
    return source_text


def _metadata_header(metadata: dict[str, Any], *, chatbot: bool = False) -> str:
    parts = []
    logical_path = metadata.get("virtual_path")
    if logical_path:
        parts.append(
            f"<b>Path:</b> {html.escape(_plain_value(logical_path), quote=True)}"
        )
    section_path = metadata.get("section_path") or metadata.get("section")
    if section_path:
        parts.append(
            f"<b>Section:</b> {html.escape(_plain_value(section_path), quote=True)}"
        )
    if not chatbot:
        page = _first_present(
            metadata.get("page_label"),
            metadata.get("page"),
            metadata.get("page_number"),
        )
        if page is not None:
            parts.append(f"<b>Page:</b> {html.escape(_plain_value(page), quote=True)}")
    return "\n" + "\n".join(parts) if parts else ""


def _format_evidence_unit(
    document: RetrievedDocument,
) -> tuple[int, str, str | None]:
    metadata = document.metadata or {}
    file_name = _first_present(
        metadata.get("file_name"), metadata.get("document_name"), "-"
    )
    safe_file_name = html.escape(_plain_value(file_name), quote=True)
    page = _first_present(
        metadata.get("page_label"), metadata.get("page"), metadata.get("page_number")
    )
    source = safe_file_name
    if page is not None:
        source += f" (Page {html.escape(_plain_value(page), quote=True)})"

    doc_type = metadata.get("type", "")
    if doc_type == "table":
        body = _body_from_metadata(document, "table_origin")
        unit = (
            f"<br><b>Table from {source}</b>"
            + _metadata_header(metadata)
            + "\n"
            + body
            + "\n<br>"
        )
        return EVIDENCE_MODE_TABLE, unit, None

    if doc_type == "chatbot":
        row = _first_present(metadata.get("page_label"), metadata.get("page"), "-")
        body = _body_from_metadata(document, "window")
        unit = (
            f"<br><b>Chatbot scenario from {safe_file_name} "
            f"(Row {html.escape(_plain_value(row), quote=True)})</b>"
            + _metadata_header(metadata, chatbot=True)
            + "\n"
            + body
            + "\n<br>"
        )
        return EVIDENCE_MODE_CHATBOT, unit, None

    if doc_type == "image":
        caption = _body_from_metadata(document, "window")
        safe_caption = html.escape(caption, quote=True)
        image_origin = metadata.get("image_origin", "")
        unit = (
            f"<br><b>Figure from {source}</b>"
            + _metadata_header(metadata)
            + "\n<img width='85%' src='<src>' "
            + f"alt='{safe_caption}'/>\n<br>"
        )
        return EVIDENCE_MODE_FIGURE, unit, image_origin

    body = _body_from_metadata(document, "window")
    unit = (
        f"<br><b>Content from {source}: </b>"
        + _metadata_header(metadata)
        + " "
        + body
        + " \n<br>"
    )
    return EVIDENCE_MODE_TEXT, unit, None


def format_evidence_unit(
    document: RetrievedDocument,
) -> tuple[int, str, str | None]:
    """Render one complete citation-ready evidence unit for budget packers."""
    return _format_evidence_unit(document)


def _call_tokenizer(tokenizer: Callable[[str], Any], text: str) -> int:
    result = tokenizer(text)
    if isinstance(result, int):
        return result
    try:
        return len(result)
    except TypeError:
        return len(list(result))


def _default_token_count(text: str) -> int:
    encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoder.encode(text, allowed_special=set(), disallowed_special="all"))


class PrepareEvidencePipeline(BaseComponent):
    """Format ranked documents as complete evidence units within a token budget.

    ``trim_func`` remains accepted for saved pipeline compatibility. Its
    ``chunk_size`` is used as the budget when available, and its tokenizer is used
    when it can be read safely. The splitter is never asked to cut formatted
    evidence. Inject ``token_counter`` for a different exact counting function.
    """

    max_context_length: int = 32000
    trim_func: TokenSplitter | None = None
    token_counter: Callable[[str], int] | None = None

    def _budget(self) -> int:
        if self.trim_func is not None:
            chunk_size = getattr(self.trim_func, "chunk_size", None)
            if isinstance(chunk_size, int) and chunk_size > 0:
                return chunk_size
            kwargs = getattr(self.trim_func, "_kwargs", {})
            chunk_size = kwargs.get("chunk_size") if isinstance(kwargs, dict) else None
            if isinstance(chunk_size, int) and chunk_size > 0:
                return chunk_size
        return self.max_context_length

    def _counter(self) -> Callable[[str], int]:
        if self.token_counter is not None:
            return self.token_counter

        if self.trim_func is not None:
            candidates = [getattr(self.trim_func, "tokenizer", None)]
            splitter_obj = getattr(self.trim_func, "_obj", None)
            candidates.append(getattr(splitter_obj, "_tokenizer", None))
            for candidate in candidates:
                if callable(candidate):
                    return lambda text, tokenizer=candidate: _call_tokenizer(
                        tokenizer, text
                    )

        return _default_token_count

    def run(self, docs: list[RetrievedDocument], trace: Any | None = None) -> Document:
        evidence = ""
        images = []
        included_modes: list[int] = []
        included_ids: list[str] = []
        included_table_bodies: set[str] = set()
        included_generic_bodies: set[str] = set()
        table_count = 0
        budget = self._budget()
        count_tokens = self._counter()
        used_tokens = 0

        for retrieved_item in docs:
            evidence_mode, unit, image_origin = format_evidence_unit(retrieved_item)
            metadata = retrieved_item.metadata or {}
            doc_type = metadata.get("type", "")

            if doc_type == "table":
                body = _body_from_metadata(retrieved_item, "table_origin")
                if body in included_table_bodies or table_count >= 5:
                    continue
            elif doc_type in {"", "text", "paragraph"}:
                body = _body_from_metadata(retrieved_item, "window")
                if body and body in included_generic_bodies:
                    continue

            candidate = evidence + unit
            candidate_tokens = count_tokens(candidate)
            if candidate_tokens > budget:
                continue

            evidence = candidate
            used_tokens = candidate_tokens
            included_modes.append(evidence_mode)
            if retrieved_item.doc_id is not None:
                included_ids.append(retrieved_item.doc_id)
            if doc_type == "table":
                included_table_bodies.add(body)
                table_count += 1
            elif doc_type in {"", "text", "paragraph"} and body:
                included_generic_bodies.add(body)
            if evidence_mode == EVIDENCE_MODE_FIGURE and image_origin:
                images.append(image_origin)

        if EVIDENCE_MODE_FIGURE in included_modes:
            evidence_mode = EVIDENCE_MODE_FIGURE
        elif EVIDENCE_MODE_TABLE in included_modes:
            evidence_mode = EVIDENCE_MODE_TABLE
        elif EVIDENCE_MODE_CHATBOT in included_modes:
            evidence_mode = EVIDENCE_MODE_CHATBOT
        else:
            evidence_mode = EVIDENCE_MODE_TEXT

        trace_update(
            trace,
            context_chunk_ids=included_ids,
            context_tokens=used_tokens,
            context_token_budget=budget,
        )
        trace_event(
            trace,
            "context",
            chunk_ids=included_ids,
            token_budget=budget,
            tokens_used=used_tokens,
        )
        return Document(content=(evidence_mode, evidence, images))
