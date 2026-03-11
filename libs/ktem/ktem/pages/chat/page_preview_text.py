import os
from html import escape
from urllib.parse import quote


PREVIEW_HTML_STYLE = (
    "html,body{width:100%;height:100%;max-width:none;overflow:hidden;}"
    "body{margin:0;padding:12px;font-family:Arial,sans-serif;background:#fff;color:#111;box-sizing:border-box;}"
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
    ".pptx-preview-body{padding:0;background:linear-gradient(180deg,#eef2ff 0%,#f8fafc 100%);overflow:hidden;}"
    ".pptx-preview-root{width:100%;height:100%;min-height:100%;box-sizing:border-box;}"
    ".pptx-preview-shell{width:100%;height:100%;overflow:auto;padding:14px;box-sizing:border-box;scrollbar-gutter:stable both-edges;overscroll-behavior:contain;display:grid;place-items:center;}"
    ".pptx-preview-canvas-wrap{width:max-content;min-width:100%;min-height:100%;box-sizing:border-box;display:grid;place-items:center;}"
    ".pptx-preview-canvas-scale{width:max-content;height:max-content;transform-origin:top left;}"
    ".pptx-preview-stage{position:relative;border-radius:18px;overflow:hidden;box-shadow:0 14px 40px rgba(15,23,42,0.14);border:1px solid rgba(148,163,184,0.28);background:#fff;}"
    ".pptx-preview-slide-number{position:absolute;top:10px;right:12px;z-index:999;font-size:12px;line-height:1;padding:6px 8px;border-radius:999px;background:rgba(255,255,255,0.86);border:1px solid rgba(148,163,184,0.35);color:#334155;}"
    ".pptx-preview-element{position:absolute;box-sizing:border-box;overflow:hidden;}"
    ".pptx-preview-text{white-space:normal;word-break:break-word;overflow-wrap:anywhere;color:#0f172a;display:flex;flex-direction:column;justify-content:flex-start;align-items:stretch;background-clip:padding-box;}"
    ".pptx-preview-text,.pptx-preview-text *,.pptx-preview-table td{-webkit-user-select:text;user-select:text;}"
    ".pptx-preview-text p{margin:0 0 0.35rem 0;line-height:1.24;}"
    ".pptx-preview-text p:last-child{margin-bottom:0;}"
    ".pptx-preview-picture{display:flex;align-items:stretch;justify-content:stretch;background:transparent;}"
    ".pptx-preview-picture img{display:block;width:100%;height:100%;object-fit:fill;}"
    ".pptx-preview-table-wrap{background:rgba(255,255,255,0.95);overflow:hidden;}"
    ".pptx-preview-table{width:100%;height:100%;border-collapse:collapse;table-layout:fixed;font-size:12px;background:transparent;}"
    ".pptx-preview-table td{border:1px solid rgba(148,163,184,0.4);padding:6px 8px;vertical-align:top;word-break:break-word;overflow-wrap:anywhere;color:#0f172a;}"
    ".pptx-preview-link{color:#2563eb;text-decoration:underline;}"
    ".pptx-preview-empty{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:24px;text-align:center;color:#475569;background:rgba(255,255,255,0.72);}"
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


def build_html_pages(
    page_contents: list[str],
    body_class: str = "",
    extra_head: str = "",
    inline_script: str = "",
) -> list[str]:
    html_pages: list[str] = []
    for content_html in page_contents:
        body_attr = f" class='{body_class}'" if body_class else ""
        script_html = f"<script>{inline_script}</script>" if inline_script else ""
        html_doc = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<style>{PREVIEW_HTML_STYLE}</style>{extra_head}</head><body{body_attr}>"
            f"{content_html}"
            f"{script_html}"
            "</body></html>"
        )
        html_pages.append("data:text/html;charset=utf-8," + quote(html_doc, safe=""))
    return html_pages