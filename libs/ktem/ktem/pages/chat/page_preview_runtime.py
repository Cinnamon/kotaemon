import hashlib
import os
import shutil
import tempfile
from urllib.parse import quote

from pypdf import PdfReader

from ...assets import PDFJS_PREBUILT_DIR
from ...utils.render import BASE_PATH
from .page_preview_types import is_pdf_source


def get_file_signature(file_path: str) -> str:
    try:
        stat = os.stat(file_path)
        raw = f"{os.path.abspath(file_path)}|{stat.st_size}|{int(stat.st_mtime_ns)}"
    except Exception:
        raw = os.path.abspath(file_path)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_pdfjs_viewer_src(file_path: str, page: int, fit_mode: str = "pdf") -> str:
    viewer_html_path = PDFJS_PREBUILT_DIR / "web" / "viewer.html"
    if not viewer_html_path.is_file():
        return ""

    normalized_viewer_path = str(viewer_html_path).replace("\\", "/")
    normalized_pdf_path = file_path.replace("\\", "/")
    pdf_src = f"{BASE_PATH}/file={normalized_pdf_path}"
    encoded_pdf_src = quote(pdf_src, safe="")
    page_num = max(1, int(page or 1))
    query = (
        f"embed=1&disablehistory=true&sidebarviewonload=0"
        f"&ktempage={page_num}&ktemv=12&ktemfit={quote(fit_mode or 'pdf', safe='')}"
        f"&file={encoded_pdf_src}"
    )
    return f"{BASE_PATH}/file={normalized_viewer_path}?{query}#page={page_num}"


def notice_html(message: str) -> str:
    return f"<div class='pdf-preview-notice'>{message or ''}</div>"


def safe_int(value, fallback: int = 1) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def clamp_page(page: int, total_pages: int) -> int:
    if total_pages < 1:
        total_pages = 1
    return min(max(1, int(page or 1)), int(total_pages))


def safe_pdf_page_count(pdf_path: str, fallback: int = 1, logger=None) -> int:
    fallback = max(1, safe_int(fallback, 1))
    if not pdf_path or not os.path.isfile(pdf_path):
        return fallback
    try:
        return max(1, len(PdfReader(pdf_path, strict=False).pages))
    except Exception as exc:
        if logger is not None:
            logger.warning("Failed to read PDF total pages from %s: %s", pdf_path, exc)
        return fallback


def is_valid_pdf(pdf_path: str) -> bool:
    try:
        if not pdf_path or (not os.path.isfile(pdf_path)):
            return False
        if os.path.getsize(pdf_path) < 64:
            return False
        pages = len(PdfReader(pdf_path, strict=False).pages)
        return pages > 0
    except Exception:
        return False


def get_pdf_preview_dir() -> str:
    gradio_temp_dir = os.environ.get("GRADIO_TEMP_DIR", tempfile.gettempdir())
    preview_dir = os.path.join(gradio_temp_dir, "pdf_previews")
    os.makedirs(preview_dir, exist_ok=True)
    return preview_dir


def ensure_pdf_preview_copy(file_path: str, file_name: str) -> str:
    if not file_path or not os.path.isfile(file_path):
        return ""
    if not is_pdf_source(file_name, file_path):
        return file_path

    preview_dir = get_pdf_preview_dir()
    preview_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.pdf"
    preview_path = os.path.join(preview_dir, preview_name)

    if not os.path.isfile(preview_path):
        shutil.copyfile(file_path, preview_path)
    elif os.path.getsize(preview_path) != os.path.getsize(file_path):
        shutil.copyfile(file_path, preview_path)

    return preview_path