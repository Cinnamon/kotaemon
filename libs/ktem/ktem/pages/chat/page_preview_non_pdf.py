import os

from sqlmodel import Session, select

from ...db.models import engine
from .page_preview_document import (
    extract_docx_html,
    extract_docx_text,
    paginate_docx_html,
)
from .page_preview_presentation import extract_pptx_text
from .page_preview_spreadsheet import extract_xlsx_text
from .page_preview_text import build_html_pages, paginate_plain_text, read_text_file
from .page_preview_types import TEXT_LIKE_EXTENSIONS


class NonPdfPreviewService:
    def __init__(self, controller):
        self._controller = controller

    def get_preview_src(self, file_id: str, file_name: str, file_path: str, page: int) -> str:
        if not file_id:
            return ""

        cached = self._controller._non_pdf_preview_cache.get(file_id)
        if cached is not None:
            page_idx = max(1, int(page or 1)) - 1
            page_idx = min(page_idx, max(0, len(cached) - 1))
            return cached[page_idx] if cached else ""

        preview_chunks = self._get_index_preview_chunks(file_id)
        resolved_file_path = file_path or self._controller._resolve_file_path_by_file_id(file_id)
        preview_text = "\n\n".join(preview_chunks).strip()
        rich_html = self._build_rich_html(file_name, resolved_file_path)
        if (not preview_text) and file_name:
            preview_text = self.extract_text_from_file(resolved_file_path, file_name)
        if not preview_text:
            preview_text = "No text preview available for this file."
        if len(preview_text) > 9000:
            preview_text = preview_text[:9000] + " ..."

        page_contents = paginate_docx_html(rich_html) if rich_html else []
        if not page_contents:
            page_contents = paginate_plain_text(preview_text)

        html_pages = build_html_pages(page_contents)
        self._controller._non_pdf_preview_cache[file_id] = html_pages
        self._controller._total_pages_cache[file_id] = max(1, len(html_pages))
        page_idx = max(1, int(page or 1)) - 1
        page_idx = min(page_idx, max(0, len(html_pages) - 1))
        return html_pages[page_idx]

    def extract_text_from_file(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        ext = os.path.splitext(file_name or file_path)[1].lower()
        if ext in TEXT_LIKE_EXTENSIONS:
            return read_text_file(file_path)
        if ext == ".docx":
            return extract_docx_text(file_path)
        if ext == ".pptx":
            return extract_pptx_text(file_path)
        if ext == ".xlsx":
            return extract_xlsx_text(file_path)
        return ""

    def _build_rich_html(self, file_name: str, resolved_file_path: str) -> str:
        ext = os.path.splitext(file_name or "")[1].lower()
        if ext == ".docx" and resolved_file_path:
            return extract_docx_html(resolved_file_path)
        return ""

    def _get_index_preview_chunks(self, file_id: str) -> list[str]:
        first_index = self._controller._app.index_manager.indices[0]
        index_table = first_index._resources["Index"]
        doc_store = first_index._resources["DocStore"]

        with Session(engine) as session:
            stmt = select(index_table.target_id).where(
                index_table.source_id == file_id,
                index_table.relation_type == "document",
            )
            doc_ids = [row[0] for row in session.execute(stmt).all()]

        preview_chunks: list[str] = []
        total_chars = 0
        for doc_id in doc_ids:
            docs = doc_store.get([doc_id])
            if not docs:
                continue
            doc = docs[0]
            if doc.metadata.get("type") in {"thumbnail", "plot"}:
                continue
            text = getattr(doc, "text", "") or getattr(doc, "content", "") or ""
            if not text:
                continue
            text = " ".join(str(text).split())
            if not text:
                continue
            preview_chunks.append(text)
            total_chars += len(text)
            if total_chars >= 9000:
                break
        return preview_chunks