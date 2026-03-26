"""Tests for ktem.logging_config — centralized logging bootstrap."""

from __future__ import annotations

import logging
import os

import pytest


@pytest.fixture(autouse=True)
def _reset_logging_state(monkeypatch):
    """Ensure each test starts with a fresh logging setup."""
    import ktem.logging_config as lc

    lc._SETUP_DONE = False
    lc._PROJECT_ROOT = None
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)
    monkeypatch.delenv("KH_LOG_LEVEL", raising=False)
    monkeypatch.delenv("KH_LOG_FILE", raising=False)
    monkeypatch.delenv("KH_LOG_DIR", raising=False)
    monkeypatch.delenv("KH_LOG_BASENAME", raising=False)
    monkeypatch.delenv("KH_PROJECT_ROOT", raising=False)


def test_setup_logging_adds_console_handler():
    from ktem.logging_config import setup_logging

    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    assert root.level == logging.INFO  # default


def test_setup_logging_respects_kh_log_level(monkeypatch):
    monkeypatch.setenv("KH_LOG_LEVEL", "DEBUG")
    from ktem.logging_config import setup_logging

    setup_logging()
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_idempotent():
    from ktem.logging_config import setup_logging

    setup_logging()
    n = len(logging.getLogger().handlers)
    setup_logging()
    assert len(logging.getLogger().handlers) == n


def test_child_logger_inherits_handler():
    from ktem.logging_config import setup_logging

    setup_logging()
    child = logging.getLogger("ktem.reasoning.simple")
    assert child.getEffectiveLevel() == logging.getLogger().level
    assert child.handlers == []  # inherits from root, no own handlers


def test_file_handler_writes(monkeypatch, tmp_path):
    log_file = str(tmp_path / "test.log")
    monkeypatch.setenv("KH_LOG_FILE", log_file)
    from ktem.logging_config import setup_logging

    setup_logging()
    logging.getLogger("file_test").info("hello file")
    # flush
    for h in logging.getLogger().handlers:
        h.flush()
    content = open(log_file).read()
    assert "hello file" in content


def test_no_file_handler_when_env_unset():
    from ktem.logging_config import setup_logging

    setup_logging()
    file_handlers = [
        h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)
    ]
    assert file_handlers == []


def test_file_handler_daily_path_under_kh_log_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("KH_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("KH_LOG_BASENAME", "app.log")
    from ktem.logging_config import create_date_path, setup_logging

    setup_logging()
    logging.getLogger("daily").info("daily line")
    for h in logging.getLogger().handlers:
        h.flush()
    dated = os.path.join(tmp_path, create_date_path(), "app.log")
    assert os.path.isfile(dated)
    assert "daily line" in open(dated, encoding="utf-8").read()


def test_kh_log_file_takes_priority_over_kh_log_dir(monkeypatch, tmp_path):
    explicit = str(tmp_path / "explicit.log")
    monkeypatch.setenv("KH_LOG_FILE", explicit)
    monkeypatch.setenv("KH_LOG_DIR", str(tmp_path / "ignored"))
    from ktem.logging_config import setup_logging

    setup_logging()
    logging.getLogger("p").info("explicit")
    for h in logging.getLogger().handlers:
        h.flush()
    assert os.path.isfile(explicit)
    assert "explicit" in open(explicit, encoding="utf-8").read()


def test_noisy_loggers_suppressed():
    from ktem.logging_config import setup_logging

    setup_logging()
    for name in ("httpx", "httpcore", "chromadb", "gradio"):
        assert logging.getLogger(name).level >= logging.WARNING


def test_relative_path_from_project():
    from pathlib import Path

    import ktem.logging_config as lc

    root = Path(lc.__file__).resolve().parents[3]
    some_file = root / "libs" / "ktem" / "ktem" / "foo.py"
    rel = lc.relative_path_from_project(str(some_file))
    assert not rel.startswith(os.sep)
    assert "libs/ktem" in rel.replace("\\", "/")
