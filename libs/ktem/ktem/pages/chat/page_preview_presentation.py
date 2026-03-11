import re
import zipfile
import xml.etree.ElementTree as ET


def extract_pptx_text(file_path: str, max_chars: int = 9000) -> str:
    texts: list[str] = []
    try:
        with zipfile.ZipFile(file_path) as zf:
            slide_names = sorted(
                [name for name in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml", name)]
            )
            for slide in slide_names:
                with zf.open(slide) as file_obj:
                    root = ET.fromstring(file_obj.read())
                for node in root.iter():
                    if node.tag.endswith("}t") and node.text:
                        texts.append(node.text)
                if sum(len(text) for text in texts) >= max_chars:
                    break
    except Exception:
        return ""
    return " ".join(texts)[:max_chars]