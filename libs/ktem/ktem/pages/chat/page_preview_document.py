import os
import re
import zipfile
import xml.etree.ElementTree as ET
from html import escape

from docx import Document as DocxDocument
from docx.oxml.ns import qn


def extract_docx_text(file_path: str, max_chars: int = 9000) -> str:
    texts: list[str] = []
    try:
        with zipfile.ZipFile(file_path) as zf:
            with zf.open("word/document.xml") as file_obj:
                root = ET.fromstring(file_obj.read())
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                texts.append(node.text)
                if sum(len(text) for text in texts) >= max_chars:
                    break
    except Exception:
        return ""
    return " ".join(texts)[:max_chars]


def paginate_docx_html(rich_html: str) -> list[str]:
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


def extract_docx_html(file_path: str, max_chars: int = 12000) -> str:
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
            name = local_name(node.tag)
            if name == "t" and node.text:
                text_parts.append(escape(node.text))
            elif name in {"br", "cr"}:
                if name == "br":
                    br_type = (node.attrib.get(qn("w:type"), "") or "").strip().lower()
                    if br_type == "page":
                        text_parts.append("<span class='docx-page-break'></span>")
                    else:
                        text_parts.append("<br/>")
                else:
                    text_parts.append("<br/>")
            elif name == "tab":
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
                    style_tokens.append(f"padding-left:{max(0, int(indent_pt))}pt;")
            except Exception:
                pass
        if para.paragraph_format and para.paragraph_format.first_line_indent:
            try:
                first_indent_pt = para.paragraph_format.first_line_indent.pt
                if (not list_tag) and first_indent_pt and first_indent_pt > 0:
                    style_tokens.append(f"text-indent:{int(first_indent_pt)}pt;")
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
        para_style_attr = f" style=\"{''.join(style_tokens)}\"" if style_tokens else ""
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