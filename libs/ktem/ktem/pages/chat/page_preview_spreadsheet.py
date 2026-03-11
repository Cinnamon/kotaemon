import re
import zipfile
import xml.etree.ElementTree as ET


def extract_xlsx_text(file_path: str, max_chars: int = 9000) -> str:
    try:
        with zipfile.ZipFile(file_path) as zf:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                with zf.open("xl/sharedStrings.xml") as file_obj:
                    ss_root = ET.fromstring(file_obj.read())
                for node in ss_root.iter():
                    if node.tag.endswith("}t") and node.text:
                        shared_strings.append(node.text)

            cells: list[str] = []
            sheet_names = sorted(
                [name for name in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml", name)]
            )
            for sheet in sheet_names:
                with zf.open(sheet) as file_obj:
                    root = ET.fromstring(file_obj.read())
                for cell in root.iter():
                    if not cell.tag.endswith("}c"):
                        continue
                    cell_type = cell.attrib.get("t", "")
                    value = ""
                    for child in cell:
                        if child.tag.endswith("}v") and child.text:
                            value = child.text
                            break
                    if not value:
                        continue
                    if cell_type == "s":
                        try:
                            idx = int(value)
                            if 0 <= idx < len(shared_strings):
                                value = shared_strings[idx]
                        except Exception:
                            pass
                    cells.append(value)
                    if sum(len(text) for text in cells) >= max_chars:
                        break
                if sum(len(text) for text in cells) >= max_chars:
                    break
    except Exception:
        return ""
    return " ".join(cells)[:max_chars]