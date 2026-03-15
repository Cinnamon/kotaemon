import os

from ...utils.render import BASE_PATH
from .page_preview_models import PreviewPayload, PreviewPayloadContext
from .page_preview_types import TEXT_LIKE_EXTENSIONS


class PdfPreviewHandler:
    def __init__(self, controller):
        self._controller = controller

    def supports(self, context: PreviewPayloadContext) -> bool:
        return self._controller._is_pdf_source(
            context.effective_name, context.effective_path
        )

    def build(self, context: PreviewPayloadContext) -> PreviewPayload:
        total_pages = self._controller._safe_pdf_page_count(
            context.effective_path, context.cached_total
        )
        page = self._controller._clamp_page(context.page, total_pages)
        viewer_src = self._controller._get_pdfjs_viewer_src(
            context.effective_path, page, fit_mode="pdf"
        )
        if context.file_id:
            self._controller._total_pages_cache[context.file_id] = total_pages
        if viewer_src:
            return PreviewPayload(
                page,
                total_pages,
                viewer_src,
                self._controller._notice_html(""),
            )

        preview_path = context.effective_path.replace("\\", "/")
        fallback_src = f"{BASE_PATH}/file={preview_path}#page={page}"
        return PreviewPayload(
            page,
            total_pages,
            fallback_src,
            self._controller._notice_html(""),
        )


class _OfficeFamilyPreviewHandler:
    supported_extensions: tuple[str, ...] = tuple()

    def __init__(self, controller):
        self._controller = controller

    def supports(self, context: PreviewPayloadContext) -> bool:
        return context.source_extension in self.supported_extensions

    def build(self, context: PreviewPayloadContext) -> PreviewPayload:
        # First check if we have a cached PDF from previous session
        office_pdf = self._controller._get_cached_office_pdf_preview(
            context.effective_path
        )
        
        # If we have a valid cached PDF, use it immediately
        if office_pdf and os.path.isfile(office_pdf):
            total_pages = self._controller._safe_pdf_page_count(
                office_pdf, context.cached_total
            )
            page = self._controller._clamp_page(context.page, total_pages)
            viewer_src = self._controller._get_pdfjs_viewer_src(
                office_pdf, page, fit_mode="office"
            )
            if context.file_id:
                self._controller._total_pages_cache[context.file_id] = total_pages
                self._controller._non_pdf_preview_cache.pop(context.file_id, None)
            if viewer_src:
                return PreviewPayload(
                    page,
                    total_pages,
                    viewer_src,
                    self._controller._notice_html(""),
                )

            office_pdf_path = office_pdf.replace("\\", "/")
            fallback_src = f"{BASE_PATH}/file={office_pdf_path}#page={page}"
            return PreviewPayload(
                page,
                total_pages,
                fallback_src,
                self._controller._notice_html(""),
            )
        
        # No cached PDF found, show placeholder and schedule conversion
        show_placeholder_once = bool(
            context.file_id
            and context.file_id not in self._controller._office_placeholder_shown
        )
        if show_placeholder_once:
            pages = self._controller._non_pdf_preview_cache.get(context.file_id, [])
            if not pages:
                _ = self._controller._get_non_pdf_preview_src(
                    context.file_id,
                    context.effective_name,
                    context.effective_path,
                    context.page,
                )
                pages = self._controller._non_pdf_preview_cache.get(
                    context.file_id, []
                )
            if pages:
                total_pages = max(1, len(pages))
                page = self._controller._clamp_page(context.page, total_pages)
                self._controller._office_placeholder_shown.add(context.file_id)
                self._controller._total_pages_cache[context.file_id] = total_pages
                return PreviewPayload(
                    page,
                    total_pages,
                    pages[page - 1],
                    self._controller._notice_html(
                        "Generating PDF preview in background..."
                    ),
                )

        self._controller._schedule_office_pdf_conversion(
            context.effective_path, context.effective_name
        )

        pages = self._controller._non_pdf_preview_cache.get(context.file_id, [])
        if not pages:
            _ = self._controller._get_non_pdf_preview_src(
                context.file_id,
                context.effective_name,
                context.effective_path,
                context.page,
            )
            pages = self._controller._non_pdf_preview_cache.get(context.file_id, [])
        total_pages = max(1, len(pages or []))
        page = self._controller._clamp_page(context.page, total_pages)
        placeholder_src = (
            pages[page - 1]
            if pages
            else self._controller._get_non_pdf_preview_src(
                context.file_id,
                context.effective_name,
                context.effective_path,
                context.page,
            )
        )
        status = self._controller._get_office_job_status(context.effective_path)
        notice = (
            "PDF conversion failed. Showing text preview."
            if status == "failed"
            else "Generating PDF preview in background..."
        )
        if context.file_id:
            self._controller._total_pages_cache[context.file_id] = total_pages
        return PreviewPayload(
            page,
            total_pages,
            placeholder_src,
            self._controller._notice_html(notice),
        )


class DocumentOfficePreviewHandler(_OfficeFamilyPreviewHandler):
    supported_extensions = (".docx", ".doc")


class PresentationOfficePreviewHandler(_OfficeFamilyPreviewHandler):
    supported_extensions = (".pptx", ".ppt")

    def build(self, context: PreviewPayloadContext) -> PreviewPayload:
        if context.source_extension == ".pptx":
            preview_src = self._controller._get_presentation_preview_src(
                context.file_id,
                context.effective_path,
                context.page,
            )
            pages = self._controller._non_pdf_preview_cache.get(context.file_id, [])
            if preview_src and pages:
                total_pages = max(1, len(pages))
                page = self._controller._clamp_page(context.page, total_pages)
                if context.file_id:
                    self._controller._total_pages_cache[context.file_id] = total_pages
                return PreviewPayload(
                    page,
                    total_pages,
                    pages[page - 1],
                    self._controller._notice_html(""),
                )
        return super().build(context)


class SpreadsheetOfficePreviewHandler(_OfficeFamilyPreviewHandler):
    supported_extensions = (".xlsx", ".xls")


class _NonPdfPreviewHandler:
    def __init__(self, controller):
        self._controller = controller

    def build(self, context: PreviewPayloadContext) -> PreviewPayload:
        non_pdf_src = self._controller._get_non_pdf_preview_src(
            context.file_id,
            context.effective_name,
            context.effective_path,
            context.page,
        )
        pages = self._controller._non_pdf_preview_cache.get(context.file_id, [])
        total_pages = max(1, len(pages or []))
        page = self._controller._clamp_page(context.page, total_pages)
        if pages:
            non_pdf_src = pages[page - 1]
        if context.file_id:
            self._controller._total_pages_cache[context.file_id] = total_pages
        if non_pdf_src:
            return PreviewPayload(
                page,
                total_pages,
                non_pdf_src,
                self._controller._notice_html(""),
            )

        return PreviewPayload(
            page,
            total_pages,
            "",
            self._controller._notice_html(
                "Preview is available for PDF files only. You can still ask questions about this file."
            ),
        )


class TextLikePreviewHandler(_NonPdfPreviewHandler):
    def supports(self, context: PreviewPayloadContext) -> bool:
        return context.source_extension in TEXT_LIKE_EXTENSIONS


class UnknownPreviewHandler(_NonPdfPreviewHandler):
    def supports(self, context: PreviewPayloadContext) -> bool:
        del context
        return True