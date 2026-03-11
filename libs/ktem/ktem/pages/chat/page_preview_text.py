import os
from html import escape
from urllib.parse import quote


PREVIEW_HTML_STYLE = (
    "html,body{max-width:100%;overflow-x:auto;}"
    "body{margin:0;padding:12px;font-family:Arial,sans-serif;background:#fff;color:#111;}"
    "pre{white-space:pre-wrap;word-break:break-word;line-height:1.45;font-size:13px;"
    "padding:12px;border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;}"
    ".docx-preview{border:1px solid #e5e7eb;border-radius:8px;background:#fafafa;padding:12px;"
    "max-width:100%;overflow-x:auto;font-size:clamp(13px,1.15vw,16px);line-height:1.55;}"
    ".docx-preview *{max-width:100%;box-sizing:border-box;}"
    ".docx-preview p{margin:0 0 8px 0;line-height:1.55;overflow-wrap:anywhere;word-break:break-word;}"
    ".docx-preview h1,.docx-preview h2,.docx-preview h3{margin:8px 0 8px 0;line-height:1.35;}"
    ".docx-preview a{color:#2563eb;text-decoration:underline;overflow-wrap:anywhere;word-break:break-all;}"
    ".docx-preview span,.docx-preview strong,.docx-preview em,.docx-preview u{overflow-wrap:anywhere;word-break:break-word;}"
    ".docx-preview ul,.docx-preview ol{margin:0 0 8px 0;padding-left:1.35em;list-style-position:outside;}"
    ".docx-preview li{margin:0 0 4px 0;overflow-wrap:anywhere;word-break:break-word;}"
    ".docx-page-break{display:block;height:0;overflow:hidden;}"
)


def paginate_plain_text(text: str, max_chars_per_page: int = 2200) -> list[str]:
    cleaned = (text or "").strip()
    if not cleaned:
        return ["<pre>No text preview available for this file.</pre>"]
    chunks: list[str] = []
    cursor = 0
    while cursor < len(cleaned):
        chunk = cleaned[cursor : cursor + max_chars_per_page]
        cursor += max_chars_per_page
        chunks.append(f"<pre>{escape(chunk)}</pre>")
    return chunks or ["<pre>No text preview available for this file.</pre>"]


def read_text_file(file_path: str, max_chars: int = 9000) -> str:
    if not file_path or not os.path.isfile(file_path):
        return ""
    for enc in ("utf-8", "utf-16", "latin-1", "gbk"):
        try:
            with open(file_path, "r", encoding=enc, errors="ignore") as file_obj:
                content = file_obj.read(max_chars * 2)
            return content[:max_chars]
        except Exception:
            continue
    return ""


def build_html_pages(page_contents: list[str]) -> list[str]:
    html_pages: list[str] = []
    for content_html in page_contents:
        html_doc = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<style>{PREVIEW_HTML_STYLE}</style></head><body>"
            f"{content_html}"
            "</body></html>"
        )
        html_pages.append("data:text/html;charset=utf-8," + quote(html_doc, safe=""))
    return html_pages