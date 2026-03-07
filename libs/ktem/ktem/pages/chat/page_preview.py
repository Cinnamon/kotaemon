import json
import os
from pathlib import Path
import shutil
import tempfile
from urllib.parse import quote

import gradio as gr
from sqlmodel import Session, select

from ...assets import PDFJS_PREBUILT_DIR
from kotaemon.loaders.pdf_loader import get_page_thumbnails

from ...db.models import engine
from ...utils.render import BASE_PATH

MINDMAP_PLACEHOLDER_HTML = (
    "<div class='page-result-placeholder'>"
    "Enter a question to generate a page-specific mindmap."
    "</div>"
)
ANSWER_PLACEHOLDER_TEXT = "Ask a question about the current page to generate an answer."


class ChatPagePreviewController:
    def __init__(self, app):
        self._app = app
        self._page_thumbnail_cache: dict[str, dict[str, str]] = {}
        self._page_preview_cache: dict[str, dict[str, str]] = {}

    def _get_pdfjs_viewer_src(self, file_path: str, page: int) -> str:
        viewer_html_path = PDFJS_PREBUILT_DIR / "web" / "viewer.html"
        if not viewer_html_path.is_file():
            return ""

        normalized_viewer_path = str(viewer_html_path).replace("\\", "/")
        normalized_pdf_path = file_path.replace("\\", "/")
        pdf_src = f"{BASE_PATH}/file={normalized_pdf_path}"
        encoded_pdf_src = quote(pdf_src, safe="")
        query = (
            f"embed=1&disablehistory=true&sidebarviewonload=0"
            f"&ktempage={max(1, int(page or 1))}&file={encoded_pdf_src}"
        )
        return f"{BASE_PATH}/file={normalized_viewer_path}?{query}"

    def _get_page_thumbnail(self, file_id: str, page: int) -> str:
        if not file_id:
            return ""

        page_key = str(page)
        if file_id in self._page_thumbnail_cache:
            cached = self._page_thumbnail_cache[file_id].get(page_key)
            if cached is not None:
                return cached

        first_index = self._app.index_manager.indices[0]
        index_table = first_index._resources["Index"]
        doc_store = first_index._resources["DocStore"]

        with Session(engine) as session:
            stmt = select(index_table.target_id).where(
                index_table.source_id == file_id,
                index_table.relation_type == "document",
            )
            doc_ids = [row[0] for row in session.execute(stmt).all()]

        page_map: dict[str, str] = {}
        if doc_ids:
            docs = doc_store.get(doc_ids)
            for doc in docs:
                if doc.metadata.get("type") != "thumbnail":
                    continue
                page_label = str(doc.metadata.get("page_label", ""))
                image_origin = doc.metadata.get("image_origin", "")
                if page_label and image_origin:
                    page_map[page_label] = image_origin

        self._page_thumbnail_cache[file_id] = page_map
        return page_map.get(page_key, "")

    def _get_page_preview_image(self, file_id: str, file_path: str, page: int) -> str:
        if not file_id or not file_path or not os.path.isfile(file_path):
            return ""

        page_key = str(page)
        if file_id in self._page_preview_cache:
            cached = self._page_preview_cache[file_id].get(page_key)
            if cached is not None:
                return cached

        page_map = self._page_preview_cache.setdefault(file_id, {})
        try:
            rendered_pages = get_page_thumbnails(
                Path(file_path), [max(0, page - 1)], dpi=120
            )
            if rendered_pages:
                page_map[page_key] = rendered_pages[0]
                return rendered_pages[0]
        except Exception as exc:
            print(f"Failed to render page preview: {exc}")

        page_map[page_key] = ""
        return ""

    def _get_pdf_preview_src_and_notice(
        self, file_id: str, file_path: str, page: int
    ) -> tuple[str, str]:
        if not file_id and not file_path:
            return (
                "",
                "<div class='pdf-preview-notice'>Select a PDF file to preview.</div>",
            )

        if not os.path.isfile(file_path):
            return (
                "",
                "<div class='pdf-preview-notice'>Selected file is unavailable.</div>",
            )

        page = max(1, int(page or 1))
        viewer_src = self._get_pdfjs_viewer_src(file_path, page)
        if viewer_src:
            return (
                viewer_src,
                "<div class='pdf-preview-notice'></div>",
            )

        preview_image = self._get_page_preview_image(file_id, file_path, page)
        if preview_image:
            return (
                preview_image,
                "<div class='pdf-preview-notice'></div>",
            )

        thumbnail = self._get_page_thumbnail(file_id, page)
        if thumbnail:
            return (
                thumbnail,
                "<div class='pdf-preview-notice'></div>",
            )

        preview_path = file_path.replace("\\", "/")
        src = f"{BASE_PATH}/file={preview_path}#page={page}"
        return (
            src,
            "<div class='pdf-preview-notice'></div>",
        )

    def _extract_first_selected_file_id(self, selected_file_ids):
        if not selected_file_ids:
            return ""

        selected = selected_file_ids[0]

        if isinstance(selected, str) and selected.startswith("["):
            try:
                selected_items = json.loads(selected)
                return selected_items[0] if selected_items else ""
            except Exception:
                return ""

        return selected

    def _ensure_pdf_preview_copy(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""

        gradio_temp_dir = os.environ.get("GRADIO_TEMP_DIR", tempfile.gettempdir())
        preview_dir = os.path.join(gradio_temp_dir, "pdf_previews")
        os.makedirs(preview_dir, exist_ok=True)

        ext = os.path.splitext(file_name)[1].lower() if file_name else ".pdf"
        if ext != ".pdf":
            ext = ".pdf"

        preview_name = f"{os.path.basename(file_path)}{ext}"
        preview_path = os.path.join(preview_dir, preview_name)

        if not os.path.isfile(preview_path):
            shutil.copyfile(file_path, preview_path)
        elif os.path.getsize(preview_path) != os.path.getsize(file_path):
            shutil.copyfile(file_path, preview_path)

        return preview_path

    def resolve_pdf_source(self, first_selector_choices, selected_file_ids):
        del first_selector_choices

        file_id = self._extract_first_selected_file_id(selected_file_ids)
        if not file_id:
            return "", "", ""

        first_index = self._app.index_manager.indices[0]
        source_table = first_index._resources["Source"]
        file_storage_path = first_index._resources["FileStoragePath"]

        with Session(engine) as session:
            statement = select(source_table).where(source_table.id == file_id)
            source_obj = session.exec(statement).first()

        if not source_obj:
            return "", "", ""

        file_name = getattr(source_obj, "name", "") or ""
        stored_path = getattr(source_obj, "path", "") or ""

        resolved_path = ""
        if stored_path:
            candidate_storage_path = os.path.join(str(file_storage_path), stored_path)
            if os.path.isfile(candidate_storage_path):
                resolved_path = self._ensure_pdf_preview_copy(
                    candidate_storage_path, file_name
                )
            elif os.path.isfile(stored_path):
                resolved_path = self._ensure_pdf_preview_copy(stored_path, file_name)

        return file_id, file_name, resolved_path

    def clear_page_outputs(self):
        return (
            "",
            MINDMAP_PLACEHOLDER_HTML,
            gr.update(visible=False),
            None,
            ANSWER_PLACEHOLDER_TEXT,
        )

    def on_selected_file_change(self, first_selector_choices, selected_file_ids):
        file_id, file_name, file_path = self.resolve_pdf_source(
            first_selector_choices, selected_file_ids
        )
        page_number = 1
        preview_src, preview_notice = self._get_pdf_preview_src_and_notice(
            file_id, file_path, page_number
        )
        return (
            file_id,
            file_name,
            file_path,
            page_number,
            preview_src,
            preview_notice,
            *self.clear_page_outputs(),
        )

    def on_page_change(self, current_page, delta, file_id, file_path):
        next_page = max(1, int(current_page or 1) + int(delta or 0))
        preview_src, preview_notice = self._get_pdf_preview_src_and_notice(
            file_id, file_path, next_page
        )
        return (
            next_page,
            preview_src,
            preview_notice,
            *self.clear_page_outputs(),
        )

    def on_prev_page(self, current_page, file_id, file_path):
        return self.on_page_change(current_page, -1, file_id, file_path)

    def on_next_page(self, current_page, file_id, file_path):
        return self.on_page_change(current_page, 1, file_id, file_path)

    def on_page_set(self, current_page, file_id, file_path):
        next_page = max(1, int(current_page or 1))
        preview_src, preview_notice = self._get_pdf_preview_src_and_notice(
            file_id, file_path, next_page
        )
        return (
            next_page,
            preview_src,
            preview_notice,
            *self.clear_page_outputs(),
        )

    def refresh_selected_file_preview(
        self, first_selector_choices, selected_file_ids, current_page
    ):
        file_id, file_name, file_path = self.resolve_pdf_source(
            first_selector_choices, selected_file_ids
        )
        page_number = max(1, int(current_page or 1))
        preview_src, preview_notice = self._get_pdf_preview_src_and_notice(
            file_id, file_path, page_number
        )
        return file_id, file_name, file_path, page_number, preview_src, preview_notice