import os

from .page_preview_handlers import (
    DocumentOfficePreviewHandler,
    PresentationOfficePreviewHandler,
    PdfPreviewHandler,
    SpreadsheetOfficePreviewHandler,
    TextLikePreviewHandler,
    UnknownPreviewHandler,
)
from .page_preview_models import PreviewPayload, PreviewPayloadContext, PreviewPayloadRequest
from .page_preview_types import detect_source_extension


class PreviewPayloadService:
    def __init__(self, controller):
        self._controller = controller
        self._handlers = [
            PdfPreviewHandler(controller),
            DocumentOfficePreviewHandler(controller),
            PresentationOfficePreviewHandler(controller),
            SpreadsheetOfficePreviewHandler(controller),
            TextLikePreviewHandler(controller),
            UnknownPreviewHandler(controller),
        ]

    def build_payload(self, request: PreviewPayloadRequest) -> PreviewPayload:
        page = max(1, self._controller._safe_int(request.requested_page, 1))
        cached_total = max(1, self._controller._safe_int(request.known_total_pages, 1))
        if request.file_id:
            cached_total = max(
                cached_total,
                self._controller._safe_int(
                    self._controller._total_pages_cache.get(request.file_id, 1), 1
                ),
            )

        if not request.file_id and not request.file_path:
            return PreviewPayload(
                1,
                1,
                "",
                self._controller._notice_html("Select a PDF file to preview."),
            )

        effective_name = request.file_name or self._controller._resolve_file_name_by_file_id(
            request.file_id
        )
        effective_path = request.file_path or self._controller._resolve_file_path_by_file_id(
            request.file_id
        )
        if not effective_path or not os.path.isfile(effective_path):
            return PreviewPayload(
                1,
                1,
                "",
                self._controller._notice_html("Selected file is unavailable."),
            )

        context = PreviewPayloadContext(
            file_id=request.file_id,
            effective_name=effective_name,
            effective_path=effective_path,
            source_extension=detect_source_extension(effective_name, effective_path),
            page=page,
            cached_total=cached_total,
        )

        for handler in self._handlers:
            if handler.supports(context):
                return handler.build(context)

        raise RuntimeError("No preview handler matched the current file.")