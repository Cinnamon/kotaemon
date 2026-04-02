"""Tests for kotaemon.agents.sandbox — LocalSandbox and LocalPythonInterpreter.

Run with:
    pytest kotaemon/libs/kotaemon/tests/test_sandbox.py -v
"""

from __future__ import annotations

import os
import textwrap
import warnings
import time
from pathlib import Path

import pytest

from kotaemon.agents.sandbox import LocalPythonInterpreter, LocalSandbox


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sandbox(tmp_path: Path) -> LocalSandbox:
    """Return a LocalSandbox rooted in a temporary directory."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        sb = LocalSandbox(working_dir=str(tmp_path), warn_on_init=False)
    return sb


@pytest.fixture()
def sample_file(sandbox: LocalSandbox, tmp_path: Path) -> Path:
    """Create a small text file for read/edit tests."""
    p = tmp_path / "hello.txt"
    p.write_text("Hello, world!\nLine two.\nLine three.\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# LocalSandbox — execute
# ---------------------------------------------------------------------------


class TestLocalSandboxExecute:
    def test_basic_echo(self, sandbox: LocalSandbox) -> None:
        resp = sandbox.execute("echo 'ping'")
        assert resp.exit_code == 0
        assert "ping" in resp.output

    def test_nonzero_exit_code(self, sandbox: LocalSandbox) -> None:
        resp = sandbox.execute("exit 42", timeout=5)
        assert resp.exit_code == 42

    def test_timeout_raises(self, sandbox: LocalSandbox) -> None:
        with pytest.raises(TimeoutError):
            sandbox.execute("sleep 60", timeout=1)

    def test_stderr_captured(self, sandbox: LocalSandbox) -> None:
        resp = sandbox.execute("python3 -c \"import sys; sys.stderr.write('err\\n')\"")
        assert "err" in resp.output


# ---------------------------------------------------------------------------
# LocalSandbox — ls
# ---------------------------------------------------------------------------


class TestLocalSandboxLs:
    def test_ls_existing_dir(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("x")
        (tmp_path / "subdir").mkdir()
        result = sandbox.ls(str(tmp_path))
        assert result.error is None
        paths = [e.path for e in result.entries]
        assert any("a.txt" in p for p in paths)
        dirs = [e for e in result.entries if e.is_dir]
        assert any("subdir" in e.path for e in dirs)

    def test_ls_nonexistent(self, sandbox: LocalSandbox) -> None:
        result = sandbox.ls("/nonexistent_1234567890")
        # Graceful: returns empty, no error
        assert result.entries == []


# ---------------------------------------------------------------------------
# LocalSandbox — read / write
# ---------------------------------------------------------------------------


class TestLocalSandboxReadWrite:
    def test_read_existing_file(
        self, sandbox: LocalSandbox, sample_file: Path
    ) -> None:
        result = sandbox.read(str(sample_file))
        assert result.error is None
        assert result.file_data is not None
        assert "Hello, world!" in result.file_data.content

    def test_read_with_pagination(
        self, sandbox: LocalSandbox, sample_file: Path
    ) -> None:
        result = sandbox.read(str(sample_file), offset=1, limit=1)
        assert result.error is None
        assert result.file_data is not None
        assert "Line two." in result.file_data.content
        assert "Hello" not in result.file_data.content

    def test_read_nonexistent(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        result = sandbox.read(str(tmp_path / "ghost.txt"))
        assert result.error is not None
        assert result.file_data is None

    def test_write_creates_file(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        target = tmp_path / "new.txt"
        assert not target.exists()
        result = sandbox.write(str(target), "fresh content\n")
        assert result.error is None
        assert target.read_text() == "fresh content\n"

    def test_write_fails_if_exists(
        self, sandbox: LocalSandbox, sample_file: Path
    ) -> None:
        result = sandbox.write(str(sample_file), "overwrite attempt")
        assert result.error is not None
        # Original content unchanged
        assert "Hello, world!" in sample_file.read_text()


# ---------------------------------------------------------------------------
# LocalSandbox — edit  (key security + correctness tests)
# ---------------------------------------------------------------------------


class TestLocalSandboxEdit:
    def test_simple_replace(
        self, sandbox: LocalSandbox, sample_file: Path
    ) -> None:
        result = sandbox.edit(str(sample_file), "Hello, world!", "Goodbye!")
        assert result.error is None
        assert result.occurrences == 1
        assert "Goodbye!" in sample_file.read_text()

    def test_string_not_found(
        self, sandbox: LocalSandbox, sample_file: Path
    ) -> None:
        result = sandbox.edit(str(sample_file), "DOES_NOT_EXIST", "x")
        assert result.error is not None
        assert "not found" in result.error.lower()

    def test_replace_all(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        p = tmp_path / "dup.txt"
        p.write_text("aaa bbb aaa ccc aaa")
        result = sandbox.edit(str(p), "aaa", "ZZZ", replace_all=True)
        assert result.error is None
        assert result.occurrences == 3
        assert p.read_text() == "ZZZ bbb ZZZ ccc ZZZ"

    def test_multiple_occurrences_without_replace_all(
        self, sandbox: LocalSandbox, tmp_path: Path
    ) -> None:
        p = tmp_path / "dup2.txt"
        p.write_text("x x x")
        result = sandbox.edit(str(p), "x", "y")
        assert result.error is not None
        assert "multiple" in result.error.lower()

    def test_injection_safe_path(
        self, sandbox: LocalSandbox, tmp_path: Path
    ) -> None:
        """Path containing shell metacharacters must not execute arbitrary code."""
        # We pass the *safe* tmp_path file path; the dangerous string only appears
        # as content, not as a shell command.
        dangerous_old = '"; rm -rf /tmp/injection_test; echo "'
        p = tmp_path / "inject.txt"
        p.write_text(f"prefix {dangerous_old} suffix")
        result = sandbox.edit(str(p), dangerous_old, "REPLACED")
        # Either succeeds (replacement found) or fails gracefully — must NOT
        # delete files or execute extra shell commands.
        assert result.error is None or "not found" in (result.error or "").lower()

    def test_injection_safe_content(
        self, sandbox: LocalSandbox, tmp_path: Path
    ) -> None:
        """new_string containing shell metacharacters is written verbatim."""
        p = tmp_path / "safe.txt"
        p.write_text("replace me")
        evil_new = "$(rm -rf /tmp/should_not_run) `echo pwned`"
        result = sandbox.edit(str(p), "replace me", evil_new)
        assert result.error is None
        assert p.read_text() == evil_new  # literal content, not executed


# ---------------------------------------------------------------------------
# LocalSandbox — grep / glob
# ---------------------------------------------------------------------------


class TestLocalSandboxGrepGlob:
    def test_grep_finds_pattern(
        self, sandbox: LocalSandbox, tmp_path: Path
    ) -> None:
        (tmp_path / "a.py").write_text("def foo():\n    pass\n")
        (tmp_path / "b.py").write_text("def bar():\n    pass\n")
        result = sandbox.grep("def foo", path=str(tmp_path))
        assert result.error is None
        assert len(result.matches) >= 1
        assert any("a.py" in m.path for m in result.matches)

    def test_grep_no_match(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        (tmp_path / "x.txt").write_text("nothing here")
        result = sandbox.grep("XYZZY_NOTHERE", path=str(tmp_path))
        assert result.matches == []

    def test_glob_finds_files(self, sandbox: LocalSandbox, tmp_path: Path) -> None:
        (tmp_path / "one.py").write_text("")
        (tmp_path / "two.py").write_text("")
        (tmp_path / "three.txt").write_text("")
        result = sandbox.glob("*.py", path=str(tmp_path))
        paths = [m.path for m in result.matches]
        assert len(paths) == 2
        assert all(p.endswith(".py") for p in paths)


# ---------------------------------------------------------------------------
# LocalPythonInterpreter — stateful REPL
# ---------------------------------------------------------------------------


class TestLocalPythonInterpreter:
    def test_basic_execution(self) -> None:
        with LocalPythonInterpreter() as interp:
            result = interp("print('hello repl')")
        assert "hello repl" in result.stdout

    def test_state_persists_across_calls(self) -> None:
        """Core CodeAct requirement: variable set in step 1 survives in step 2."""
        with LocalPythonInterpreter() as interp:
            interp("x = 12345")
            result = interp("print(x)")
        assert "12345" in result.stdout
        assert result.error is None

    def test_multi_step_computation(self) -> None:
        with LocalPythonInterpreter() as interp:
            interp("total = 0")
            interp("for i in range(5): total += i")
            result = interp("print(total)")
        assert "10" in result.stdout

    def test_import_persists(self) -> None:
        with LocalPythonInterpreter() as interp:
            interp("import math")
            result = interp("print(math.pi > 3)")
        assert "True" in result.stdout

    def test_exception_captured_not_crash(self) -> None:
        """Runtime errors must not kill the interpreter session."""
        with LocalPythonInterpreter() as interp:
            result = interp("1 / 0")
            assert result.error is not None
            assert "ZeroDivisionError" in result.error
            # Interpreter still alive — can continue
            r2 = interp("print('still alive')")
        assert "still alive" in r2.stdout

    def test_syntax_error_captured(self) -> None:
        with LocalPythonInterpreter() as interp:
            result = interp("def broken(:")
            assert result.error is not None
            # Interpreter still alive
            r2 = interp("print('ok')")
        assert "ok" in r2.stdout

    def test_timeout_kills_and_restarts(self) -> None:
        """Infinite loop must not hang forever — must TimeoutError and survive."""
        with LocalPythonInterpreter(timeout=1) as interp:
            result = interp("while True: pass")
            assert result.timed_out is True
            assert result.error is not None
            # After kill+restart, interpreter should be usable again
            r2 = interp("print('recovered')")
        assert "recovered" in r2.stdout

    def test_large_output_truncated(self) -> None:
        with LocalPythonInterpreter(max_output_chars=100) as interp:
            result = interp("print('x' * 10000)")
        assert "truncated" in result.stdout

    def test_wall_clock_timeout_even_with_continuous_output(self) -> None:
        with LocalPythonInterpreter(timeout=1, max_output_chars=200) as interp:
            started_at = time.monotonic()
            result = interp(
                "import time\n"
                "while True:\n"
                "    print('tick')\n"
                "    time.sleep(0.1)\n"
            )
            elapsed = time.monotonic() - started_at

        assert result.timed_out is True
        assert result.error is not None
        assert elapsed < 3

    def test_output_bounded_before_completion(self) -> None:
        with LocalPythonInterpreter(max_output_chars=40) as interp:
            result = interp(
                "for _ in range(200):\n"
                "    print('abcdefghijklmnopqrstuvwxyz')\n"
            )

        assert "truncated at 40 chars" in result.stdout
        assert len(result.stdout) < 120

    def test_context_manager_closes_cleanly(self) -> None:
        interp = LocalPythonInterpreter()
        interp("y = 99")
        interp.close()
        # Process should be dead
        assert interp._proc is None or interp._proc.poll() is not None
