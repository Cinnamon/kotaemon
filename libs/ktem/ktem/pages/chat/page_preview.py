import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import hashlib
import time
from html import escape
import re
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import quote

import gradio as gr
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from pypdf import PdfReader
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
logger = logging.getLogger(__name__)


class ChatPagePreviewController:
    def __init__(self, app):
        self._app = app
        self._page_thumbnail_cache: dict[str, dict[str, str]] = {}
        self._page_preview_cache: dict[str, dict[str, str]] = {}
        self._total_pages_cache: dict[str, int] = {}
        self._non_pdf_preview_cache: dict[str, list[str]] = {}
        self._file_name_cache: dict[str, str] = {}
        self._office_pdf_cache: dict[str, str] = {}
        self._office_pdf_job_status: dict[str, str] = {}
        self._office_pdf_job_ts: dict[str, float] = {}
        self._office_pdf_job_lock = threading.Lock()
        self._last_preview_file_id: str = ""
        self._force_first_page_file_id: str = ""
        self._office_placeholder_shown: set[str] = set()

    @staticmethod
    def _find_soffice_binary() -> str:
        env_path = os.environ.get("SOFFICE_PATH", "").strip()
        if env_path and os.path.isfile(env_path):
            return env_path

        for cmd in ("soffice", "soffice.com", "soffice.exe"):
            found = shutil.which(cmd)
            if found and os.path.isfile(found):
                return found

        candidates = [
            r"C:\Program Files\LibreOffice\program\soffice.com",
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.com",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return ""

    @staticmethod
    def _is_pdf_source(file_name: str, file_path: str) -> bool:
        file_name = (file_name or "").lower()
        file_path = (file_path or "").lower()
        return file_name.endswith(".pdf") or file_path.endswith(".pdf")

    @staticmethod
    def _detect_office_extension(file_name: str, file_path: str) -> str:
        ext = os.path.splitext((file_name or file_path or ""))[1].lower()
        if ext in {".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"}:
            return ext

        if file_path and os.path.isfile(file_path):
            try:
                if zipfile.is_zipfile(file_path):
                    with zipfile.ZipFile(file_path) as zf:
                        names = set(zf.namelist())
                    if "word/document.xml" in names:
                        return ".docx"
                    if "ppt/presentation.xml" in names:
                        return ".pptx"
                    if "xl/workbook.xml" in names:
                        return ".xlsx"
            except Exception:
                pass

            try:
                with open(file_path, "rb") as f:
                    header = f.read(8)
                if header.startswith(b"\xD0\xCF\x11\xE0"):
                    # Legacy binary Office container (doc/ppt/xls).
                    return ".doc"
            except Exception:
                pass

        return ""

    def _is_office_source(self, file_name: str, file_path: str) -> bool:
        return bool(self._detect_office_extension(file_name, file_path))

    @staticmethod
    def _get_file_signature(file_path: str) -> str:
        try:
            stat = os.stat(file_path)
            raw = f"{os.path.abspath(file_path)}|{stat.st_size}|{int(stat.st_mtime_ns)}"
        except Exception:
            raw = os.path.abspath(file_path)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _get_pdfjs_viewer_src(self, file_path: str, page: int, fit_mode: str = "pdf") -> str:
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
        # Keep both custom page param and standard hash page for robust PDF.js navigation.
        return f"{BASE_PATH}/file={normalized_viewer_path}?{query}#page={page_num}"

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

    def _get_non_pdf_preview_src(
        self, file_id: str, file_name: str, file_path: str, page: int
    ) -> str:
        if not file_id:
            return ""

        cached = self._non_pdf_preview_cache.get(file_id)
        if cached is not None:
            page_idx = max(1, int(page or 1)) - 1
            page_idx = min(page_idx, max(0, len(cached) - 1))
            return cached[page_idx] if cached else ""

        first_index = self._app.index_manager.indices[0]
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

        ext = os.path.splitext(file_name or "")[1].lower()
        rich_html = ""
        resolved_file_path = file_path or self._resolve_file_path_by_file_id(file_id)

        # For DOCX, always prefer rich HTML extraction for temporary preview,
        # so fonts/sizes/paragraph structure are preserved.
        if ext == ".docx" and resolved_file_path:
            rich_html = self._extract_docx_html(resolved_file_path)

        preview_text = "\n\n".join(preview_chunks).strip()
        if (not preview_text) and file_name:
            preview_text = self._extract_text_from_file(resolved_file_path, file_name)
        if not preview_text:
            preview_text = "No text preview available for this file."
        if len(preview_text) > 9000:
            preview_text = preview_text[:9000] + " ..."

        page_contents: list[str] = []
        if rich_html:
            page_contents = self._paginate_docx_html(rich_html)
        if not page_contents:
            page_contents = self._paginate_plain_text(preview_text)
        html_pages: list[str] = []
        total_pages = max(1, len(page_contents))
        for idx, content_html in enumerate(page_contents, start=1):
            html_doc = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<style>"
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
            "</style></head><body>"
            f"{content_html}"
            "</body></html>"
            )
            html_pages.append("data:text/html;charset=utf-8," + quote(html_doc, safe=""))

        self._non_pdf_preview_cache[file_id] = html_pages
        self._total_pages_cache[file_id] = max(1, len(html_pages))
        page_idx = max(1, int(page or 1)) - 1
        page_idx = min(page_idx, max(0, len(html_pages) - 1))
        return html_pages[page_idx]

    def _resolve_file_path_by_file_id(self, file_id: str) -> str:
        if not file_id:
            return ""
        for index in self._app.index_manager.indices:
            resources = getattr(index, "_resources", {}) or {}
            source_table = resources.get("Source")
            file_storage_path = resources.get("FileStoragePath")
            if source_table is None:
                continue

            with Session(engine) as session:
                statement = select(source_table).where(source_table.id == file_id)
                source_obj = session.exec(statement).first()
            if not source_obj:
                continue

            self._file_name_cache[file_id] = getattr(source_obj, "name", "") or ""
            stored_path = getattr(source_obj, "path", "") or ""
            if not stored_path:
                continue

            if file_storage_path:
                candidate_storage_path = os.path.join(
                    str(file_storage_path), stored_path
                )
                if os.path.isfile(candidate_storage_path):
                    return candidate_storage_path
            if os.path.isfile(stored_path):
                return stored_path
        return ""

    def _resolve_file_name_by_file_id(self, file_id: str) -> str:
        if not file_id:
            return ""
        if file_id in self._file_name_cache:
            return self._file_name_cache[file_id]
        _ = self._resolve_file_path_by_file_id(file_id)
        return self._file_name_cache.get(file_id, "")

    @staticmethod
    def _paginate_plain_text(text: str, max_chars_per_page: int = 2200) -> list[str]:
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

    @staticmethod
    def _paginate_docx_html(rich_html: str) -> list[str]:
        if not rich_html:
            return []
        match = re.search(
            r"^<div class='docx-preview'[^>]*>(.*)</div>$",
            rich_html,
            flags=re.DOTALL,
        )
        if not match:
            return [rich_html]
        inner = match.group(1)
        blocks = re.findall(
            r"(<h[1-3][^>]*>.*?</h[1-3]>|<p[^>]*>.*?</p>|<li[^>]*>.*?</li>|<ul>|</ul>|<ol>|</ol>)",
            inner,
            flags=re.DOTALL,
        )
        if not blocks:
            return [rich_html]
        def strip_tags(html: str) -> str:
            text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", "", text)
            return text

        def estimate_block_height(block_html: str) -> float:
            block = block_html.strip().lower()
            if block in {"<ul>", "</ul>", "<ol>", "</ol>"}:
                return 6.0

            text = strip_tags(block_html)
            text_len = len(text.strip())
            br_count = block_html.lower().count("<br")
            has_page_break = "docx-page-break" in block_html

            if block.startswith("<h1"):
                chars_per_line = 34
                line_height = 34.0
                base = 24.0
            elif block.startswith("<h2"):
                chars_per_line = 40
                line_height = 30.0
                base = 20.0
            elif block.startswith("<h3"):
                chars_per_line = 46
                line_height = 27.0
                base = 16.0
            elif block.startswith("<li"):
                chars_per_line = 62
                line_height = 24.0
                base = 8.0
            else:
                chars_per_line = 72
                line_height = 24.0
                base = 10.0

            lines = max(
                1,
                int((text_len + max(1, chars_per_line) - 1) / max(1, chars_per_line)),
            )
            lines += br_count
            height = base + lines * line_height
            if has_page_break:
                height += 1200.0
            return height

        max_page_height = 980.0
        pages: list[str] = []
        current: list[str] = []
        current_height = 0.0
        for block in blocks:
            block_height = estimate_block_height(block)
            force_break = "docx-page-break" in block

            if current and (current_height + block_height > max_page_height):
                pages.append("<div class='docx-preview'>" + "".join(current) + "</div>")
                current = []
                current_height = 0.0

            current.append(block)
            current_height += block_height

            if force_break:
                pages.append("<div class='docx-preview'>" + "".join(current) + "</div>")
                current = []
                current_height = 0.0

        if current:
            pages.append("<div class='docx-preview'>" + "".join(current) + "</div>")
        return pages

    @staticmethod
    def _read_text_file(file_path: str, max_chars: int = 9000) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        for enc in ("utf-8", "utf-16", "latin-1", "gbk"):
            try:
                with open(file_path, "r", encoding=enc, errors="ignore") as f:
                    content = f.read(max_chars * 2)
                return content[:max_chars]
            except Exception:
                continue
        return ""

    @staticmethod
    def _extract_docx_text(file_path: str, max_chars: int = 9000) -> str:
        texts: list[str] = []
        try:
            with zipfile.ZipFile(file_path) as zf:
                with zf.open("word/document.xml") as fp:
                    root = ET.fromstring(fp.read())
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    texts.append(node.text)
                    if sum(len(t) for t in texts) >= max_chars:
                        break
        except Exception:
            return ""
        return " ".join(texts)[:max_chars]

    @staticmethod
    def _extract_docx_html(file_path: str, max_chars: int = 12000) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        try:
            doc = DocxDocument(file_path)
        except Exception:
            return ""

        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        rels = doc.part.rels
        base_font_name = "Times New Roman"
        base_font_size_pt = 12.0
        try:
            normal_style = doc.styles["Normal"]
            if normal_style and normal_style.font:
                if normal_style.font.name:
                    base_font_name = str(normal_style.font.name)
                if normal_style.font.size:
                    base_font_size_pt = float(normal_style.font.size.pt)
        except Exception:
            pass
        base_font_size_pt = max(9.0, min(18.0, base_font_size_pt))
        base_font_size_em = max(0.85, min(1.35, base_font_size_pt / 12.0))
        num_to_abstract: dict[str, str] = {}
        abstract_level_fmt: dict[tuple[str, int], str] = {}
        try:
            numbering_root = doc.part.numbering_part.element
            for num in numbering_root.findall(".//w:num", ns):
                num_id = num.attrib.get(qn("w:numId"), "")
                abstract_el = num.find("w:abstractNumId", ns)
                if num_id and abstract_el is not None:
                    abs_id = abstract_el.attrib.get(qn("w:val"), "")
                    if abs_id:
                        num_to_abstract[num_id] = abs_id
            for abs_num in numbering_root.findall(".//w:abstractNum", ns):
                abs_id = abs_num.attrib.get(qn("w:abstractNumId"), "")
                if not abs_id:
                    continue
                for lvl in abs_num.findall("w:lvl", ns):
                    lvl_id = lvl.attrib.get(qn("w:ilvl"), "0")
                    num_fmt_el = lvl.find("w:numFmt", ns)
                    if num_fmt_el is None:
                        continue
                    fmt = (num_fmt_el.attrib.get(qn("w:val"), "") or "").strip().lower()
                    try:
                        abstract_level_fmt[(abs_id, int(lvl_id))] = fmt
                    except Exception:
                        continue
        except Exception:
            pass

        def local_name(tag: str) -> str:
            return tag.split("}", 1)[-1] if "}" in tag else tag

        def render_run_element(run_el) -> str:
            text_parts: list[str] = []
            for node in run_el:
                n = local_name(node.tag)
                if n == "t" and node.text:
                    text_parts.append(escape(node.text))
                elif n in {"br", "cr"}:
                    if n == "br":
                        br_type = (node.attrib.get(qn("w:type"), "") or "").strip().lower()
                        if br_type == "page":
                            text_parts.append("<span class='docx-page-break'></span>")
                        else:
                            text_parts.append("<br/>")
                    else:
                        text_parts.append("<br/>")
                elif n == "tab":
                    text_parts.append("&emsp;")
            text_html = "".join(text_parts)
            if not text_html:
                return ""

            rpr = run_el.find("w:rPr", ns)
            style_tokens: list[str] = []
            bold = False
            italic = False
            underline = False
            if rpr is not None:
                if rpr.find("w:b", ns) is not None:
                    bold = True
                if rpr.find("w:i", ns) is not None:
                    italic = True
                if rpr.find("w:u", ns) is not None:
                    underline = True

                color_el = rpr.find("w:color", ns)
                if color_el is not None:
                    color_val = (color_el.attrib.get(qn("w:val"), "") or "").strip()
                    if re.fullmatch(r"[0-9A-Fa-f]{6}", color_val):
                        style_tokens.append(f"color:#{color_val};")

                size_el = rpr.find("w:sz", ns)
                if size_el is not None:
                    size_val = (size_el.attrib.get(qn("w:val"), "") or "").strip()
                    try:
                        half_points = int(size_val)
                        points = max(8.0, min(20.0, half_points / 2.0))
                        scale = max(0.82, min(1.35, points / 12.0))
                        style_tokens.append(f"font-size:{scale:.2f}em;")
                    except Exception:
                        pass

                font_el = rpr.find("w:rFonts", ns)
                if font_el is not None:
                    font_name = (
                        font_el.attrib.get(qn("w:ascii"), "")
                        or font_el.attrib.get(qn("w:hAnsi"), "")
                        or ""
                    ).strip()
                    if font_name:
                        style_tokens.append(
                            f"font-family:'{escape(font_name)}','{escape(base_font_name)}',serif;"
                        )

            if bold:
                text_html = f"<strong>{text_html}</strong>"
            if italic:
                text_html = f"<em>{text_html}</em>"
            if underline:
                text_html = f"<u>{text_html}</u>"

            style_attr = f" style=\"{''.join(style_tokens)}\"" if style_tokens else ""
            return f"<span{style_attr}>{text_html}</span>"

        def render_hyperlink_element(link_el) -> str:
            rid = link_el.attrib.get(qn("r:id"), "")
            href = ""
            if rid in rels:
                try:
                    href = str(rels[rid].target_ref or "")
                except Exception:
                    href = ""
            run_html_parts: list[str] = []
            for run_el in link_el.findall("w:r", ns):
                run_html = render_run_element(run_el)
                if run_html:
                    run_html_parts.append(run_html)
            inner = "".join(run_html_parts).strip()
            if not inner:
                return ""
            if href:
                return (
                    f"<a href=\"{escape(href)}\" target=\"_blank\" rel=\"noopener noreferrer\">"
                    f"{inner}</a>"
                )
            return inner

        def detect_list_info(para_obj) -> tuple[str | None, int]:
            style_name = (para_obj.style.name or "").lower() if para_obj.style else ""
            ppr = para_obj._p.pPr
            ilvl = 0
            num_id = ""
            if ppr is not None and ppr.numPr is not None and ppr.numPr.ilvl is not None:
                try:
                    ilvl = int(ppr.numPr.ilvl.val)
                except Exception:
                    ilvl = 0
            if ppr is not None and ppr.numPr is not None and ppr.numPr.numId is not None:
                try:
                    num_id = str(ppr.numPr.numId.val)
                except Exception:
                    num_id = ""

            if num_id:
                abs_id = num_to_abstract.get(num_id, "")
                fmt = abstract_level_fmt.get((abs_id, ilvl), "")
                if fmt in {"bullet"}:
                    return "ul", ilvl
                if fmt:
                    return "ol", ilvl

            if "list bullet" in style_name or "bullet" in style_name:
                return "ul", ilvl
            if "list number" in style_name or "number" in style_name:
                return "ol", ilvl
            if ppr is not None and ppr.numPr is not None:
                # If numbering style is unknown, default to bullet to avoid false 1/2/3 output.
                return "ul", ilvl
            return None, 0

        parts: list[str] = [
            (
                "<div class='docx-preview' "
                f"style=\"font-family:'{escape(base_font_name)}',serif;"
                f"font-size:{base_font_size_em:.2f}em;\">"
            )
        ]
        active_list_stack: list[str] = []

        def close_lists():
            while active_list_stack:
                list_tag = active_list_stack.pop()
                parts.append(f"</{list_tag}>")

        consumed = 0
        for para in doc.paragraphs:
            text = para.text or ""
            if not text.strip():
                continue
            consumed += len(text)
            if consumed > max_chars:
                break

            style_name = (para.style.name or "").lower() if para.style else ""
            tag = "p"
            if "heading 1" in style_name or style_name == "title":
                tag = "h1"
            elif "heading 2" in style_name:
                tag = "h2"
            elif "heading 3" in style_name:
                tag = "h3"

            style_tokens: list[str] = []
            list_tag, list_level = detect_list_info(para)
            if para.paragraph_format and para.paragraph_format.left_indent:
                try:
                    indent_pt = para.paragraph_format.left_indent.pt
                    if indent_pt:
                        if list_tag:
                            style_tokens.append(
                                f"padding-left:{max(0, int(indent_pt))}pt;"
                            )
                        else:
                            style_tokens.append(
                                f"padding-left:{max(0, int(indent_pt))}pt;"
                            )
                except Exception:
                    pass
            if para.paragraph_format and para.paragraph_format.first_line_indent:
                try:
                    first_indent_pt = para.paragraph_format.first_line_indent.pt
                    if first_indent_pt:
                        # Negative hanging indent frequently appears in Word lists
                        # and causes overflow in HTML preview; ignore for lists.
                        if (not list_tag) and first_indent_pt > 0:
                            style_tokens.append(
                                f"text-indent:{int(first_indent_pt)}pt;"
                            )
                except Exception:
                    pass
            para_alignment = para.alignment
            if para_alignment is None and para.style and para.style.paragraph_format:
                para_alignment = para.style.paragraph_format.alignment
            if para_alignment is not None:
                align_map = {0: "left", 1: "center", 2: "right", 3: "justify"}
                align_val = align_map.get(int(para_alignment))
                if align_val:
                    style_tokens.append(f"text-align:{align_val};")

            run_html_parts: list[str] = []
            for child in para._p:
                child_name = local_name(child.tag)
                if child_name == "r":
                    run_html = render_run_element(child)
                    if run_html:
                        run_html_parts.append(run_html)
                elif child_name == "hyperlink":
                    link_html = render_hyperlink_element(child)
                    if link_html:
                        run_html_parts.append(link_html)

            paragraph_inner = "".join(run_html_parts) or escape(text)
            para_style_attr = (
                f" style=\"{''.join(style_tokens)}\"" if style_tokens else ""
            )
            if list_tag:
                target_depth = max(1, int(list_level or 0) + 1)
                while len(active_list_stack) > target_depth:
                    last_tag = active_list_stack.pop()
                    parts.append(f"</{last_tag}>")
                while len(active_list_stack) < target_depth:
                    active_list_stack.append(list_tag)
                    parts.append(f"<{list_tag}>")
                if active_list_stack and active_list_stack[-1] != list_tag:
                    last_tag = active_list_stack.pop()
                    parts.append(f"</{last_tag}>")
                    active_list_stack.append(list_tag)
                    parts.append(f"<{list_tag}>")
                parts.append(f"<li{para_style_attr}>{paragraph_inner}</li>")
            else:
                close_lists()
                parts.append(f"<{tag}{para_style_attr}>{paragraph_inner}</{tag}>")

        close_lists()
        parts.append("</div>")
        html = "".join(parts)
        if html == "<div class='docx-preview'></div>":
            return ""
        return html

    @staticmethod
    def _extract_pptx_text(file_path: str, max_chars: int = 9000) -> str:
        texts: list[str] = []
        try:
            with zipfile.ZipFile(file_path) as zf:
                slide_names = sorted(
                    [n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml", n)]
                )
                for slide in slide_names:
                    with zf.open(slide) as fp:
                        root = ET.fromstring(fp.read())
                    for node in root.iter():
                        if node.tag.endswith("}t") and node.text:
                            texts.append(node.text)
                    if sum(len(t) for t in texts) >= max_chars:
                        break
        except Exception:
            return ""
        return " ".join(texts)[:max_chars]

    @staticmethod
    def _extract_xlsx_text(file_path: str, max_chars: int = 9000) -> str:
        try:
            with zipfile.ZipFile(file_path) as zf:
                shared_strings: list[str] = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    with zf.open("xl/sharedStrings.xml") as fp:
                        ss_root = ET.fromstring(fp.read())
                    for node in ss_root.iter():
                        if node.tag.endswith("}t") and node.text:
                            shared_strings.append(node.text)

                cells: list[str] = []
                sheet_names = sorted(
                    [n for n in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", n)]
                )
                for sheet in sheet_names:
                    with zf.open(sheet) as fp:
                        root = ET.fromstring(fp.read())
                    for c in root.iter():
                        if not c.tag.endswith("}c"):
                            continue
                        c_type = c.attrib.get("t", "")
                        value = ""
                        for child in c:
                            if child.tag.endswith("}v") and child.text:
                                value = child.text
                                break
                        if not value:
                            continue
                        if c_type == "s":
                            try:
                                idx = int(value)
                                if 0 <= idx < len(shared_strings):
                                    value = shared_strings[idx]
                            except Exception:
                                pass
                        cells.append(value)
                        if sum(len(t) for t in cells) >= max_chars:
                            break
                    if sum(len(t) for t in cells) >= max_chars:
                        break
        except Exception:
            return ""
        return " ".join(cells)[:max_chars]

    def _extract_text_from_file(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        ext = os.path.splitext(file_name or file_path)[1].lower()
        if ext in {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html"}:
            return self._read_text_file(file_path)
        if ext == ".docx":
            return self._extract_docx_text(file_path)
        if ext == ".pptx":
            return self._extract_pptx_text(file_path)
        if ext == ".xlsx":
            return self._extract_xlsx_text(file_path)
        return ""

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
            logger.warning("Failed to render page preview: %s", exc)

        page_map[page_key] = ""
        return ""

    @staticmethod
    def _notice_html(message: str) -> str:
        return f"<div class='pdf-preview-notice'>{message or ''}</div>"

    @staticmethod
    def _safe_int(value, fallback: int = 1) -> int:
        try:
            return int(value)
        except Exception:
            return int(fallback)

    def _safe_pdf_page_count(self, pdf_path: str, fallback: int = 1) -> int:
        fallback = max(1, self._safe_int(fallback, 1))
        if not pdf_path or not os.path.isfile(pdf_path):
            return fallback
        try:
            return max(1, len(PdfReader(pdf_path, strict=False).pages))
        except Exception as exc:
            logger.warning("Failed to read PDF total pages from %s: %s", pdf_path, exc)
            return fallback

    def _get_office_job_status(self, file_path: str) -> str:
        if not file_path:
            return ""
        job_key = self._get_file_signature(file_path)
        with self._office_pdf_job_lock:
            return self._office_pdf_job_status.get(job_key, "")

    def _build_preview_payload(
        self,
        file_id: str,
        file_name: str,
        file_path: str,
        requested_page: int,
        known_total_pages: int = 1,
    ) -> tuple[int, int, str, str]:
        page = max(1, self._safe_int(requested_page, 1))
        cached_total = max(1, self._safe_int(known_total_pages, 1))
        if file_id:
            cached_total = max(
                cached_total, self._safe_int(self._total_pages_cache.get(file_id, 1), 1)
            )

        if not file_id and not file_path:
            return (
                1,
                1,
                "",
                self._notice_html("Select a PDF file to preview."),
            )

        effective_name = file_name or self._resolve_file_name_by_file_id(file_id)
        effective_path = file_path or self._resolve_file_path_by_file_id(file_id)
        if not effective_path or not os.path.isfile(effective_path):
            return (
                1,
                1,
                "",
                self._notice_html("Selected file is unavailable."),
            )

        # 1) Native PDF: keep branch isolated from office conversion logic.
        if self._is_pdf_source(effective_name, effective_path):
            total_pages = self._safe_pdf_page_count(effective_path, cached_total)
            page = self._clamp_page(page, total_pages)
            viewer_src = self._get_pdfjs_viewer_src(
                effective_path, page, fit_mode="pdf"
            )
            if viewer_src:
                if file_id:
                    self._total_pages_cache[file_id] = total_pages
                return page, total_pages, viewer_src, self._notice_html("")

            preview_path = effective_path.replace("\\", "/")
            fallback_src = f"{BASE_PATH}/file={preview_path}#page={page}"
            if file_id:
                self._total_pages_cache[file_id] = total_pages
            return page, total_pages, fallback_src, self._notice_html("")

        # 2) Office files: HTML placeholder first, then cached PDF when ready.
        if self._is_office_source(effective_name, effective_path):
            office_pdf = self._get_cached_office_pdf_preview(effective_path)
            if office_pdf and os.path.isfile(office_pdf):
                show_placeholder_once = bool(
                    file_id and file_id not in self._office_placeholder_shown
                )
                if show_placeholder_once:
                    pages = self._non_pdf_preview_cache.get(file_id, [])
                    if not pages:
                        _ = self._get_non_pdf_preview_src(
                            file_id, effective_name, effective_path, page
                        )
                        pages = self._non_pdf_preview_cache.get(file_id, [])
                    if pages:
                        total_pages = max(1, len(pages))
                        page = self._clamp_page(page, total_pages)
                        self._office_placeholder_shown.add(file_id)
                        self._total_pages_cache[file_id] = total_pages
                        return (
                            page,
                            total_pages,
                            pages[page - 1],
                            self._notice_html("Generating PDF preview in background..."),
                        )

            if office_pdf and os.path.isfile(office_pdf):
                total_pages = self._safe_pdf_page_count(office_pdf, cached_total)
                page = self._clamp_page(page, total_pages)
                viewer_src = self._get_pdfjs_viewer_src(
                    office_pdf, page, fit_mode="office"
                )
                if viewer_src:
                    if file_id:
                        self._total_pages_cache[file_id] = total_pages
                        self._non_pdf_preview_cache.pop(file_id, None)
                    return page, total_pages, viewer_src, self._notice_html("")

                office_pdf_path = office_pdf.replace("\\", "/")
                fallback_src = f"{BASE_PATH}/file={office_pdf_path}#page={page}"
                if file_id:
                    self._total_pages_cache[file_id] = total_pages
                    self._non_pdf_preview_cache.pop(file_id, None)
                return page, total_pages, fallback_src, self._notice_html("")

            self._schedule_office_pdf_conversion(effective_path, effective_name)

            pages = self._non_pdf_preview_cache.get(file_id, [])
            if not pages:
                _ = self._get_non_pdf_preview_src(
                    file_id, effective_name, effective_path, page
                )
                pages = self._non_pdf_preview_cache.get(file_id, [])
            total_pages = max(1, len(pages or []))
            page = self._clamp_page(page, total_pages)
            placeholder_src = (
                pages[page - 1]
                if pages
                else self._get_non_pdf_preview_src(
                    file_id, effective_name, effective_path, page
                )
            )
            status = self._get_office_job_status(effective_path)
            if status == "failed":
                notice = "PDF conversion failed. Showing text preview."
            else:
                notice = "Generating PDF preview in background..."
            if file_id:
                self._total_pages_cache[file_id] = total_pages
            return page, total_pages, placeholder_src, self._notice_html(notice)

        # 3) Other non-PDF files: preview text only.
        non_pdf_src = self._get_non_pdf_preview_src(
            file_id, effective_name, effective_path, page
        )
        pages = self._non_pdf_preview_cache.get(file_id, [])
        total_pages = max(1, len(pages or []))
        page = self._clamp_page(page, total_pages)
        if pages:
            non_pdf_src = pages[page - 1]
        if file_id:
            self._total_pages_cache[file_id] = total_pages
        if non_pdf_src:
            return page, total_pages, non_pdf_src, self._notice_html("")

        return (
            page,
            total_pages,
            "",
            self._notice_html(
                "Preview is available for PDF files only. You can still ask questions about this file."
            ),
        )

    def _get_pdf_preview_src_and_notice(
        self, file_id: str, file_name: str, file_path: str, page: int
    ) -> tuple[str, str]:
        _, _, preview_src, preview_notice = self._build_preview_payload(
            file_id, file_name, file_path, page, self._total_pages_cache.get(file_id, 1)
        )
        return preview_src, preview_notice

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

    def _get_total_pages(self, file_id: str, file_name: str, file_path: str) -> int:
        _, total_pages, _, _ = self._build_preview_payload(
            file_id, file_name, file_path, 1, self._total_pages_cache.get(file_id, 1)
        )
        return total_pages

    @staticmethod
    def _clamp_page(page: int, total_pages: int) -> int:
        if total_pages < 1:
            total_pages = 1
        return min(max(1, int(page or 1)), int(total_pages))

    def _ensure_pdf_preview_copy(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        if not self._is_pdf_source(file_name, file_path):
            return file_path

        gradio_temp_dir = os.environ.get("GRADIO_TEMP_DIR", tempfile.gettempdir())
        preview_dir = os.path.join(gradio_temp_dir, "pdf_previews")
        os.makedirs(preview_dir, exist_ok=True)

        preview_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.pdf"
        preview_path = os.path.join(preview_dir, preview_name)

        if not os.path.isfile(preview_path):
            shutil.copyfile(file_path, preview_path)
        elif os.path.getsize(preview_path) != os.path.getsize(file_path):
            shutil.copyfile(file_path, preview_path)

        return preview_path

    def _convert_office_to_pdf_preview(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        ext = self._detect_office_extension(file_name, file_path)
        if ext not in {".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"}:
            return ""
        cache_key = self._get_file_signature(file_path)
        if cache_key in self._office_pdf_cache and os.path.isfile(
            self._office_pdf_cache[cache_key]
        ):
            return self._office_pdf_cache[cache_key]

        gradio_temp_dir = os.environ.get("GRADIO_TEMP_DIR", tempfile.gettempdir())
        preview_dir = os.path.join(gradio_temp_dir, "pdf_previews")
        os.makedirs(preview_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(file_path))[0]
        libreoffice_output_pdf = os.path.join(preview_dir, f"{stem}.pdf")

        output_pdf = os.path.join(
            preview_dir, f"{stem}_{cache_key[:12]}.pdf"
        )
        convert_input_path = file_path
        temp_input_path = ""
        current_ext = os.path.splitext(file_path)[1].lower()
        if not current_ext and ext:
            temp_input_path = os.path.join(
                preview_dir, f"{stem}_{cache_key[:12]}{ext}"
            )
            try:
                shutil.copyfile(file_path, temp_input_path)
                convert_input_path = temp_input_path
            except Exception:
                convert_input_path = file_path

        soffice_cmd = self._find_soffice_binary()
        if soffice_cmd:
            try:
                result = subprocess.run(
                    [
                        soffice_cmd,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        preview_dir,
                        convert_input_path,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120,
                )
                # LibreOffice always exports with source stem name. Move/copy to
                # hash-based cache name to avoid collisions across same-stem files.
                if os.path.isfile(libreoffice_output_pdf):
                    if libreoffice_output_pdf != output_pdf:
                        try:
                            shutil.copyfile(libreoffice_output_pdf, output_pdf)
                        except Exception:
                            output_pdf = libreoffice_output_pdf
                    self._office_pdf_cache[cache_key] = output_pdf
                    if temp_input_path and os.path.isfile(temp_input_path):
                        try:
                            os.remove(temp_input_path)
                        except Exception:
                            pass
                    return output_pdf
                if os.path.isfile(output_pdf):
                    self._office_pdf_cache[cache_key] = output_pdf
                    if temp_input_path and os.path.isfile(temp_input_path):
                        try:
                            os.remove(temp_input_path)
                        except Exception:
                            pass
                    return output_pdf
                stderr_msg = (result.stderr or "").strip()
                stdout_msg = (result.stdout or "").strip()
                if stderr_msg or stdout_msg:
                    logger.warning(
                        "LibreOffice conversion finished without output file. "
                        f"stdout={stdout_msg[:500]} stderr={stderr_msg[:500]}"
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to convert office file to PDF preview via soffice: "
                    f"{repr(exc)}"
                )
        else:
            logger.info(
                "LibreOffice soffice binary not found. Skipping soffice conversion."
            )

        # Windows/macOS fallback for docx conversion when LibreOffice isn't available.
        if ext in {".docx", ".doc"}:
            try:
                from docx2pdf import convert as docx2pdf_convert

                docx2pdf_convert(convert_input_path, output_pdf)
                if os.path.isfile(output_pdf):
                    self._office_pdf_cache[cache_key] = output_pdf
                    if temp_input_path and os.path.isfile(temp_input_path):
                        try:
                            os.remove(temp_input_path)
                        except Exception:
                            pass
                    return output_pdf
            except Exception as exc:
                logger.warning(
                    "Failed to convert office file to PDF preview via docx2pdf: "
                    f"{repr(exc)}"
                )
        if temp_input_path and os.path.isfile(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception:
                pass
        return ""

    def _get_cached_office_pdf_preview(self, file_path: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        cache_key = self._get_file_signature(file_path)
        cached_pdf = self._office_pdf_cache.get(cache_key, "")
        if cached_pdf and os.path.isfile(cached_pdf) and self._is_valid_pdf(cached_pdf):
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[cache_key] = "done"
            return cached_pdf
        # Recover conversion cache across app restarts.
        gradio_temp_dir = os.environ.get("GRADIO_TEMP_DIR", tempfile.gettempdir())
        preview_dir = os.path.join(gradio_temp_dir, "pdf_previews")
        stem = os.path.splitext(os.path.basename(file_path))[0]
        recovered_pdf = os.path.join(preview_dir, f"{stem}_{cache_key[:12]}.pdf")
        if os.path.isfile(recovered_pdf) and self._is_valid_pdf(recovered_pdf):
            self._office_pdf_cache[cache_key] = recovered_pdf
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[cache_key] = "done"
            return recovered_pdf
        return ""

    @staticmethod
    def _is_valid_pdf(pdf_path: str) -> bool:
        try:
            if not pdf_path or (not os.path.isfile(pdf_path)):
                return False
            if os.path.getsize(pdf_path) < 64:
                return False
            pages = len(PdfReader(pdf_path, strict=False).pages)
            return pages > 0
        except Exception:
            return False

    def _schedule_office_pdf_conversion(self, file_path: str, file_name: str):
        if not self._is_office_source(file_name, file_path):
            return
        if not file_path or not os.path.isfile(file_path):
            return
        cached_pdf = self._get_cached_office_pdf_preview(file_path)
        if cached_pdf:
            return

        job_key = self._get_file_signature(file_path)
        now = time.time()
        with self._office_pdf_job_lock:
            current_status = self._office_pdf_job_status.get(job_key, "")
            last_ts = float(self._office_pdf_job_ts.get(job_key, 0.0) or 0.0)
            is_stale = (now - last_ts) > 180 if last_ts > 0 else True
            if current_status in {"queued", "running"} and (not is_stale):
                return
            if current_status == "done":
                # "done" is valid only when output file still exists.
                if cached_pdf and os.path.isfile(cached_pdf):
                    return
            self._office_pdf_job_status[job_key] = "queued"
            self._office_pdf_job_ts[job_key] = now

        def _job():
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[job_key] = "running"
                self._office_pdf_job_ts[job_key] = time.time()
            try:
                output_pdf = self._convert_office_to_pdf_preview(file_path, file_name)
                with self._office_pdf_job_lock:
                    self._office_pdf_job_status[job_key] = (
                        "done" if output_pdf and os.path.isfile(output_pdf) else "failed"
                    )
                    self._office_pdf_job_ts[job_key] = time.time()
            except Exception as exc:
                logger.warning("Background office->pdf conversion failed: %s", exc)
                with self._office_pdf_job_lock:
                    self._office_pdf_job_status[job_key] = "failed"
                    self._office_pdf_job_ts[job_key] = time.time()

        threading.Thread(
            target=_job,
            name=f"office-pdf-preview-{job_key[:8]}",
            daemon=True,
        ).start()

    def resolve_pdf_source(self, first_selector_choices, selected_file_ids):
        del first_selector_choices

        file_id = self._extract_first_selected_file_id(selected_file_ids)
        if not file_id:
            return "", "", ""
        file_name = ""
        resolved_path = ""

        for index in self._app.index_manager.indices:
            resources = getattr(index, "_resources", {}) or {}
            source_table = resources.get("Source")
            file_storage_path = resources.get("FileStoragePath")
            if source_table is None:
                continue

            with Session(engine) as session:
                statement = select(source_table).where(source_table.id == file_id)
                source_obj = session.exec(statement).first()

            if not source_obj:
                continue

            file_name = getattr(source_obj, "name", "") or ""
            stored_path = getattr(source_obj, "path", "") or ""

            if stored_path and file_storage_path:
                candidate_storage_path = os.path.join(
                    str(file_storage_path), stored_path
                )
                if os.path.isfile(candidate_storage_path):
                    resolved_path = candidate_storage_path
                    break

            if stored_path and os.path.isfile(stored_path):
                resolved_path = stored_path
                break

        if not file_name:
            file_name = self._resolve_file_name_by_file_id(file_id)
        if not resolved_path:
            resolved_path = self._resolve_file_path_by_file_id(file_id)

        resolved_path = self._ensure_pdf_preview_copy(resolved_path, file_name)

        return file_id, file_name, resolved_path

    def clear_page_outputs(self):
        return (
            "",
            MINDMAP_PLACEHOLDER_HTML,
            gr.update(visible=False),
            None,
            ANSWER_PLACEHOLDER_TEXT,
        )

    def get_cached_page_outputs(self, page_outputs_cache: dict, page_number: int):
        if not isinstance(page_outputs_cache, dict):
            return self.clear_page_outputs()

        page_key = str(max(1, int(page_number or 1)))
        page_output = page_outputs_cache.get(page_key, {})
        if not isinstance(page_output, dict):
            return self.clear_page_outputs()

        last_question = page_output.get("last_question", "") or ""
        mindmap_html = page_output.get("mindmap_html", "") or ""
        answer_text = page_output.get("answer_text", "") or ""
        if not (last_question or mindmap_html or answer_text):
            return self.clear_page_outputs()

        if not mindmap_html:
            mindmap_html = MINDMAP_PLACEHOLDER_HTML
        if not answer_text:
            answer_text = ANSWER_PLACEHOLDER_TEXT

        return (
            last_question,
            mindmap_html,
            gr.update(visible=False),
            None,
            answer_text,
        )

    def cache_page_outputs(
        self,
        page_outputs_cache: dict,
        page_number: int,
        last_question: str,
        mindmap_html: str,
        answer_text: str,
    ):
        if not isinstance(page_outputs_cache, dict):
            page_outputs_cache = {}

        page_key = str(max(1, int(page_number or 1)))
        updated_cache = dict(page_outputs_cache)
        updated_cache[page_key] = {
            "last_question": last_question or "",
            "mindmap_html": mindmap_html or "",
            "answer_text": answer_text or "",
        }
        return updated_cache

    def on_selected_file_change(
        self, first_selector_choices, selected_file_ids, page_outputs_cache
    ):
        file_id, file_name, file_path = self.resolve_pdf_source(
            first_selector_choices, selected_file_ids
        )
        self._force_first_page_file_id = file_id or ""
        if file_id:
            self._office_placeholder_shown.discard(file_id)
        page_number, total_pages, preview_src, preview_notice = self._build_preview_payload(
            file_id, file_name, file_path, 1, 1
        )
        return (
            file_id,
            file_name,
            file_path,
            page_number,
            total_pages,
            preview_src,
            preview_notice,
            *self.clear_page_outputs(),
            {},
        )

    def on_page_change(
        self, current_page, delta, file_id, file_path, page_outputs_cache, total_pages
    ):
        if not file_id or not file_path:
            _, total_pages, preview_src, preview_notice = self._build_preview_payload(
                file_id, "", file_path, 1, 1
            )
            return (
                1,
                total_pages,
                preview_src,
                preview_notice,
                *self.clear_page_outputs(),
            )

        file_name = self._resolve_file_name_by_file_id(file_id)
        requested_page = int(current_page or 1) + int(delta or 0)
        next_page, total_pages, preview_src, preview_notice = self._build_preview_payload(
            file_id,
            file_name,
            file_path,
            requested_page,
            total_pages,
        )
        return (
            next_page,
            total_pages,
            preview_src,
            preview_notice,
            *self.get_cached_page_outputs(page_outputs_cache, next_page),
        )

    def on_prev_page(
        self, current_page, file_id, file_path, page_outputs_cache, total_pages
    ):
        return self.on_page_change(
            current_page, -1, file_id, file_path, page_outputs_cache, total_pages
        )

    def on_next_page(
        self, current_page, file_id, file_path, page_outputs_cache, total_pages
    ):
        return self.on_page_change(
            current_page, 1, file_id, file_path, page_outputs_cache, total_pages
        )

    def on_page_set(
        self, current_page, file_id, file_path, page_outputs_cache, total_pages
    ):
        if not file_id or not file_path:
            _, total_pages, preview_src, preview_notice = self._build_preview_payload(
                file_id, "", file_path, 1, 1
            )
            return (
                1,
                total_pages,
                preview_src,
                preview_notice,
                *self.clear_page_outputs(),
            )

        file_name = self._resolve_file_name_by_file_id(file_id)
        next_page, total_pages, preview_src, preview_notice = self._build_preview_payload(
            file_id,
            file_name,
            file_path,
            current_page,
            total_pages,
        )
        return (
            next_page,
            total_pages,
            preview_src,
            preview_notice,
            *self.get_cached_page_outputs(page_outputs_cache, next_page),
        )

    def refresh_selected_file_preview(
        self, first_selector_choices, selected_file_ids, current_page, total_pages
    ):
        file_id, file_name, file_path = self.resolve_pdf_source(
            first_selector_choices, selected_file_ids
        )
        next_file_id, must_force_first, target_page = self._resolve_target_page(
            file_id, current_page
        )
        page_number, total_pages, preview_src, preview_notice = self._build_preview_payload(
            file_id,
            file_name,
            file_path,
            target_page,
            total_pages,
        )
        self._sync_preview_tracking(next_file_id, must_force_first, page_number)
        return (
            file_id,
            file_name,
            file_path,
            page_number,
            total_pages,
            preview_src,
            preview_notice,
        )

    def on_preview_tick(self, *args):
        # Gradio Timer payload shape can vary across versions/runtime.
        # Accept both the expected 7 inputs and an extra leading timer value.
        values = list(args)
        if len(values) >= 8:
            values = values[-7:]
        if len(values) < 7:
            return gr.skip(), gr.skip(), gr.skip(), gr.skip()
        (
            file_id,
            file_name,
            file_path,
            current_page,
            total_pages,
            current_preview_src,
            current_preview_notice,
        ) = values[:7]
        next_file_id, must_force_first, target_page = self._resolve_target_page(
            file_id, current_page
        )
        page_number, next_total_pages, preview_src, preview_notice = self._build_preview_payload(
            file_id,
            file_name,
            file_path,
            target_page,
            total_pages,
        )
        self._sync_preview_tracking(next_file_id, must_force_first, page_number)
        if (
            int(page_number or 1) == int(target_page or 1)
            and int(next_total_pages or 1) == int(total_pages or 1)
            and (preview_src or "") == (current_preview_src or "")
            and (preview_notice or "") == (current_preview_notice or "")
        ):
            return gr.skip(), gr.skip(), gr.skip(), gr.skip()
        return page_number, next_total_pages, preview_src, preview_notice

    def _resolve_target_page(self, file_id: str, current_page: int):
        next_file_id = file_id or ""
        prev_file_id = self._last_preview_file_id or ""
        must_force_first = bool(
            next_file_id and next_file_id == (self._force_first_page_file_id or "")
        )
        file_changed = bool(next_file_id and next_file_id != prev_file_id)
        target_page = 1 if (must_force_first or file_changed) else current_page
        return next_file_id, must_force_first, target_page

    def _sync_preview_tracking(
        self, next_file_id: str, must_force_first: bool, page_number: int
    ):
        if must_force_first and int(page_number or 1) == 1:
            self._force_first_page_file_id = ""
        self._last_preview_file_id = next_file_id
