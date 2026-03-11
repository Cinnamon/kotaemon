from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewPayloadRequest:
    file_id: str
    file_name: str
    file_path: str
    requested_page: int
    known_total_pages: int = 1


@dataclass(frozen=True)
class PreviewPayload:
    page: int
    total_pages: int
    preview_src: str
    preview_notice: str


@dataclass(frozen=True)
class PreviewPayloadContext:
    file_id: str
    effective_name: str
    effective_path: str
    source_extension: str
    page: int
    cached_total: int