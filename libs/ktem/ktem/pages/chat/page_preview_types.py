import os
import zipfile


OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"}
TEXT_LIKE_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html"}


def is_pdf_source(file_name: str, file_path: str) -> bool:
    file_name = (file_name or "").lower()
    file_path = (file_path or "").lower()
    return file_name.endswith(".pdf") or file_path.endswith(".pdf")


def detect_office_extension(file_name: str, file_path: str) -> str:
    ext = os.path.splitext((file_name or file_path or ""))[1].lower()
    if ext in OFFICE_EXTENSIONS:
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
            with open(file_path, "rb") as file_obj:
                header = file_obj.read(8)
            if header.startswith(b"\xD0\xCF\x11\xE0"):
                # Legacy binary Office container (doc/ppt/xls).
                return ".doc"
        except Exception:
            pass

    return ""


def detect_source_extension(file_name: str, file_path: str) -> str:
    ext = os.path.splitext((file_name or file_path or ""))[1].lower()
    if ext:
        return ext
    office_ext = detect_office_extension(file_name, file_path)
    if office_ext:
        return office_ext
    return ""


def is_office_source(file_name: str, file_path: str) -> bool:
    return bool(detect_office_extension(file_name, file_path))


def is_text_like_source(file_name: str, file_path: str) -> bool:
    return detect_source_extension(file_name, file_path) in TEXT_LIKE_EXTENSIONS