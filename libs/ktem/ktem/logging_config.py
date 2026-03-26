"""Centralized logging configuration for Kotaemon.

Call ``setup_logging()`` once at application startup (e.g. in ``app.py``).
Console output uses ANSI level colors (similar to a custom formatter pattern).
Optional file logging: plain text, no ANSI.

Environment variables
---------------------
KH_LOG_LEVEL      : DEBUG / INFO (default) / WARNING / ERROR / CRITICAL
KH_LOG_FILE       : If set, append logs to this exact file path (plain text).
KH_LOG_DIR        : If set (and KH_LOG_FILE is unset), write daily rotating
                    path: ``{KH_LOG_DIR}/{YYYY}/{MM}/{DD}/{KH_LOG_BASENAME}``.
KH_LOG_BASENAME   : Log filename under the daily folder (default: kotaemon.log).
KH_PROJECT_ROOT   : Optional override for the repo root used to shorten paths in logs.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

_SETUP_DONE = False
_PROJECT_ROOT: Path | None = None

LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
CONSOLE_FORMAT = (
    "%(asctime)s - %(levelname)s - [%(name)s] %(pathname)s:%(lineno)d - %(message)s"
)
TIMER_FORMAT = "%(asctime)s - %(levelname)s - [Timer] - %(message)s"
FILE_LOG_FORMAT = (
    "%(asctime)s - %(levelname)-8s - %(name)s - %(pathname)s:%(lineno)d - %(message)s"
)


class COLOR:
    NOCOLOR = "\033[0m"
    RED = "\033[0;31m"
    PURPLE = "\033[0;35m"
    YELLOW = "\033[1;33m"
    LIGHTBLUE = "\033[1;34m"
    LIGHTCYAN = "\033[1;36m"


def create_date_path() -> str:
    """Return ``year/month/day`` relative path for log directory nesting."""
    now = datetime.now()
    return os.path.join(now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))


def project_root() -> Path:
    """Repo root: ``.../kotaemon`` (parent of ``libs/``)."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        env = os.environ.get("KH_PROJECT_ROOT")
        if env:
            _PROJECT_ROOT = Path(env).resolve()
        else:
            # libs/ktem/ktem/logging_config.py -> parents[3] == repo root
            _PROJECT_ROOT = Path(__file__).resolve().parents[3]
    return _PROJECT_ROOT


def relative_path_from_project(pathname: str) -> str:
    """Shorten absolute paths to paths relative to the project root."""
    if not pathname:
        return pathname
    try:
        p = Path(pathname).resolve()
        rel = p.relative_to(project_root())
        return str(rel).replace("\\", "/")
    except ValueError:
        return pathname


class CustomFormatter(logging.Formatter):
    """ANSI-colored console lines per log level."""

    def __init__(
        self,
        format_log: str = CONSOLE_FORMAT,
        format_log_timer: str = TIMER_FORMAT,
    ) -> None:
        super().__init__()
        self.format_log = format_log
        self.format_log_timer = format_log_timer

    def _formats_for(self, template: str) -> dict[int, str]:
        return {
            logging.DEBUG: COLOR.LIGHTBLUE + template + COLOR.NOCOLOR,
            logging.INFO: COLOR.LIGHTCYAN + template + COLOR.NOCOLOR,
            logging.WARNING: COLOR.YELLOW + template + COLOR.NOCOLOR,
            logging.ERROR: COLOR.RED + template + COLOR.NOCOLOR,
            logging.CRITICAL: COLOR.PURPLE + template + COLOR.NOCOLOR,
        }

    def format(self, record: logging.LogRecord) -> str:
        pathname = getattr(record, "pathname", "") or ""
        template = (
            self.format_log_timer if "_timer.py" in pathname else self.format_log
        )
        formats = self._formats_for(template)
        log_fmt = formats.get(record.levelno)
        if log_fmt is None:
            log_fmt = template
        formatter = logging.Formatter(log_fmt, datefmt=LOG_DATE_FORMAT)
        orig_path = record.pathname
        try:
            record.pathname = relative_path_from_project(pathname)
            return formatter.format(record)
        finally:
            record.pathname = orig_path


class ProjectRelativeFileFormatter(logging.Formatter):
    """Plain file lines with ``pathname`` relative to project root."""

    def format(self, record: logging.LogRecord) -> str:
        pathname = getattr(record, "pathname", "") or ""
        orig_path = record.pathname
        try:
            record.pathname = relative_path_from_project(pathname)
            return super().format(record)
        finally:
            record.pathname = orig_path


def _resolve_level() -> int:
    name = os.environ.get("KH_LOG_LEVEL", "INFO").upper()
    return getattr(logging, name, logging.INFO)


def _resolve_file_path() -> str | None:
    """Return absolute path for file logging, or None to skip."""
    explicit = os.environ.get("KH_LOG_FILE")
    if explicit:
        return os.path.abspath(explicit)

    base_dir = os.environ.get("KH_LOG_DIR")
    if not base_dir:
        return None

    basename = os.environ.get("KH_LOG_BASENAME", "kotaemon.log")
    dated = os.path.join(os.path.abspath(base_dir), create_date_path())
    os.makedirs(dated, exist_ok=True)
    return os.path.join(dated, basename)


def setup_logging() -> None:
    """Configure the root logger for the whole Kotaemon process.

    Safe to call multiple times — only the first invocation has effect.
    """
    global _SETUP_DONE
    if _SETUP_DONE:
        return
    _SETUP_DONE = True

    level = _resolve_level()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(CustomFormatter())
    root.addHandler(console_handler)

    log_path = _resolve_file_path()
    if log_path:
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            ProjectRelativeFileFormatter(FILE_LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        root.addHandler(file_handler)

    for noisy in (
        "httpx",
        "httpcore",
        "urllib3",
        "openai",
        "chromadb",
        "gradio",
        "fsspec",
        "multipart",
        "matplotlib",
    ):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))

    os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
    os.environ.setdefault("GLOG_minloglevel", "2")
