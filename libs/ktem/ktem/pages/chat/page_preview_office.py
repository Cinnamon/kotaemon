import logging
import os
import shutil
import subprocess
import threading
import time

from .page_preview_runtime import get_file_signature, get_pdf_preview_dir, is_valid_pdf
from .page_preview_types import detect_office_extension, is_office_source


class OfficePreviewConversionService:
    def __init__(self, logger: logging.Logger | None = None):
        self._logger = logger or logging.getLogger(__name__)
        self._office_pdf_cache: dict[str, str] = {}
        self._office_pdf_job_status: dict[str, str] = {}
        self._office_pdf_job_ts: dict[str, float] = {}
        self._office_pdf_job_lock = threading.Lock()

    @staticmethod
    def find_soffice_binary() -> str:
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

    def get_status(self, file_path: str) -> str:
        if not file_path:
            return ""
        job_key = get_file_signature(file_path)
        with self._office_pdf_job_lock:
            return self._office_pdf_job_status.get(job_key, "")

    def convert_to_pdf_preview(self, file_path: str, file_name: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        ext = detect_office_extension(file_name, file_path)
        if ext not in {".docx", ".pptx", ".xlsx", ".doc", ".ppt", ".xls"}:
            return ""
        cache_key = get_file_signature(file_path)
        cached_output = self._office_pdf_cache.get(cache_key, "")
        if cached_output and os.path.isfile(cached_output):
            return cached_output

        preview_dir = get_pdf_preview_dir()
        stem = os.path.splitext(os.path.basename(file_path))[0]
        libreoffice_output_pdf = os.path.join(preview_dir, f"{stem}.pdf")
        output_pdf = os.path.join(preview_dir, f"{stem}_{cache_key[:12]}.pdf")

        convert_input_path = file_path
        temp_input_path = ""
        current_ext = os.path.splitext(file_path)[1].lower()
        if not current_ext and ext:
            temp_input_path = os.path.join(preview_dir, f"{stem}_{cache_key[:12]}{ext}")
            try:
                shutil.copyfile(file_path, temp_input_path)
                convert_input_path = temp_input_path
            except Exception:
                convert_input_path = file_path

        soffice_cmd = self.find_soffice_binary()
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
                if os.path.isfile(libreoffice_output_pdf):
                    if libreoffice_output_pdf != output_pdf:
                        try:
                            shutil.copyfile(libreoffice_output_pdf, output_pdf)
                        except Exception:
                            output_pdf = libreoffice_output_pdf
                    self._office_pdf_cache[cache_key] = output_pdf
                    self._cleanup_temp_input(temp_input_path)
                    return output_pdf
                if os.path.isfile(output_pdf):
                    self._office_pdf_cache[cache_key] = output_pdf
                    self._cleanup_temp_input(temp_input_path)
                    return output_pdf
                stderr_msg = (result.stderr or "").strip()
                stdout_msg = (result.stdout or "").strip()
                if stderr_msg or stdout_msg:
                    self._logger.warning(
                        "LibreOffice conversion finished without output file. stdout=%s stderr=%s",
                        stdout_msg[:500],
                        stderr_msg[:500],
                    )
            except Exception as exc:
                self._logger.warning(
                    "Failed to convert office file to PDF preview via soffice: %s",
                    repr(exc),
                )
        else:
            self._logger.info(
                "LibreOffice soffice binary not found. Skipping soffice conversion."
            )

        if ext in {".docx", ".doc"}:
            try:
                from docx2pdf import convert as docx2pdf_convert

                docx2pdf_convert(convert_input_path, output_pdf)
                if os.path.isfile(output_pdf):
                    self._office_pdf_cache[cache_key] = output_pdf
                    self._cleanup_temp_input(temp_input_path)
                    return output_pdf
            except Exception as exc:
                self._logger.warning(
                    "Failed to convert office file to PDF preview via docx2pdf: %s",
                    repr(exc),
                )

        self._cleanup_temp_input(temp_input_path)
        return ""

    def get_cached_pdf_preview(self, file_path: str) -> str:
        if not file_path or not os.path.isfile(file_path):
            return ""
        cache_key = get_file_signature(file_path)
        cached_pdf = self._office_pdf_cache.get(cache_key, "")
        if cached_pdf and os.path.isfile(cached_pdf) and is_valid_pdf(cached_pdf):
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[cache_key] = "done"
            return cached_pdf

        preview_dir = get_pdf_preview_dir()
        stem = os.path.splitext(os.path.basename(file_path))[0]
        recovered_pdf = os.path.join(preview_dir, f"{stem}_{cache_key[:12]}.pdf")
        if os.path.isfile(recovered_pdf) and is_valid_pdf(recovered_pdf):
            self._office_pdf_cache[cache_key] = recovered_pdf
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[cache_key] = "done"
            return recovered_pdf
        
        # Also check for PDFs that might exist from previous sessions
        # Try to find any PDF with matching stem in the preview directory
        try:
            if os.path.isdir(preview_dir):
                for filename in os.listdir(preview_dir):
                    if filename.startswith(stem + "_") and filename.endswith(".pdf"):
                        candidate_path = os.path.join(preview_dir, filename)
                        if os.path.isfile(candidate_path) and is_valid_pdf(candidate_path):
                            self._office_pdf_cache[cache_key] = candidate_path
                            with self._office_pdf_job_lock:
                                self._office_pdf_job_status[cache_key] = "done"
                            return candidate_path
        except Exception:
            pass  # Ignore errors when scanning preview directory
        
        return ""

    def schedule_conversion(self, file_path: str, file_name: str):
        if not is_office_source(file_name, file_path):
            return
        if not file_path or not os.path.isfile(file_path):
            return
        cached_pdf = self.get_cached_pdf_preview(file_path)
        if cached_pdf:
            return

        job_key = get_file_signature(file_path)
        now = time.time()
        with self._office_pdf_job_lock:
            current_status = self._office_pdf_job_status.get(job_key, "")
            last_ts = float(self._office_pdf_job_ts.get(job_key, 0.0) or 0.0)
            is_stale = (now - last_ts) > 180 if last_ts > 0 else True
            if current_status in {"queued", "running"} and (not is_stale):
                return
            if current_status == "done":
                if cached_pdf and os.path.isfile(cached_pdf):
                    return
            self._office_pdf_job_status[job_key] = "queued"
            self._office_pdf_job_ts[job_key] = now

        def _job():
            with self._office_pdf_job_lock:
                self._office_pdf_job_status[job_key] = "running"
                self._office_pdf_job_ts[job_key] = time.time()
            try:
                output_pdf = self.convert_to_pdf_preview(file_path, file_name)
                with self._office_pdf_job_lock:
                    self._office_pdf_job_status[job_key] = (
                        "done" if output_pdf and os.path.isfile(output_pdf) else "failed"
                    )
                    self._office_pdf_job_ts[job_key] = time.time()
            except Exception as exc:
                self._logger.warning("Background office->pdf conversion failed: %s", exc)
                with self._office_pdf_job_lock:
                    self._office_pdf_job_status[job_key] = "failed"
                    self._office_pdf_job_ts[job_key] = time.time()

        threading.Thread(
            target=_job,
            name=f"office-pdf-preview-{job_key[:8]}",
            daemon=True,
        ).start()

    @staticmethod
    def _cleanup_temp_input(temp_input_path: str):
        if temp_input_path and os.path.isfile(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception:
                pass