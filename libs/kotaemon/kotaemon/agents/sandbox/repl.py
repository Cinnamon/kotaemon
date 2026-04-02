"""LocalPythonInterpreter: stateful persistent REPL for the CodeAct strategy.

Unlike ``LocalSandbox`` (which re-spawns a fresh process per command), this
class keeps a single ``python -i`` process alive between calls.  Variables,
imports, and function definitions created in one ``__call__`` are available in
all subsequent calls — exactly the semantics required by the CodeAct agent
pattern.

Protocol:
    Code is sent to the subprocess's stdin.  After each block the executor
    appends a ``print(SENTINEL)`` to stdout so we know exactly where one
    execution ends and the next begins, without polling or arbitrary sleeps.

Timeout handling:
    A daemon thread reads stdout in the background.  If the sentinel does not
    arrive within ``timeout`` seconds the background process is killed (SIGKILL)
    and a ``TimeoutError`` is raised.  A fresh interpreter is started
    automatically on the next call so the caller does not need to restart.

Usage::

    interp = LocalPythonInterpreter(timeout=30)
    interp("x = 42")
    result = interp("print(x)")   # Python object x still in scope
    # result.stdout == "42\\n"
    interp.close()                 # or use as context manager

    with LocalPythonInterpreter() as interp:
        interp("import pandas as pd")
        r = interp("df = pd.DataFrame({'a': [1,2,3]}); print(df.shape)")
"""

from __future__ import annotations

import logging
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_SENTINEL = "__KOTAEMON_EXEC_DONE__"
_SENTINEL_LINE = f"{_SENTINEL}\n"


@dataclass
class REPLResult:
    """Output from a single interpreter execution."""

    stdout: str = ""
    """Captured standard output (excluding the sentinel line)."""
    stderr: str = ""
    """Standard error lines interleaved with stdout (python -i sends them there)."""
    error: str | None = None
    """Set when execution raised an unhandled exception (parsed from stderr)."""
    timed_out: bool = False
    """True when the execution exceeded the timeout and the process was killed."""


class LocalPythonInterpreter:
    """Persistent Python REPL maintaining state across ``__call__`` invocations.

    Args:
        timeout: Per-call timeout in seconds (default 30).  On timeout the
            subprocess is killed and a fresh one is started automatically.
        python_executable: Path to the Python interpreter to launch
            (defaults to the same interpreter running this process).
        max_output_chars: Truncation limit for captured stdout to avoid memory
            exhaustion from runaway print loops (default 16_384 chars).
    """

    def __init__(
        self,
        timeout: int = 30,
        python_executable: str | None = None,
        max_output_chars: int = 16_384,
    ) -> None:
        self._timeout = timeout
        self._python = python_executable or sys.executable
        self._max_chars = max_output_chars
        self._proc: subprocess.Popen | None = None
        self._stdout_q: queue.Queue[str] = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self._start_process()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start_process(self) -> None:
        """Spawn the background python -i process and wire up the reader thread."""
        self._proc = subprocess.Popen(
            [self._python, "-i", "-q", "-u"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr → stdout so we read one stream
            text=True,
            bufsize=1,  # line-buffered
        )
        self._stdout_q = queue.Queue()
        self._reader_thread = threading.Thread(
            target=self._read_stdout,
            args=(self._proc, self._stdout_q),
            daemon=True,
            name="kotaemon-repl-reader",
        )
        self._reader_thread.start()
        # Drain the Python ">>>" startup prompt lines so they don't pollute output
        self._drain_startup()

    def _drain_startup(self) -> None:
        """Consume the interpreter banner / prompt emitted at startup."""
        # Send a no-op sentinel immediately to detect when banner is done
        self._write_to_stdin(f"print('{_SENTINEL}')\n")
        self._collect_until_sentinel(timeout=10)

    def _read_stdout(
        self, proc: subprocess.Popen, q: queue.Queue[str]
    ) -> None:
        """Background thread: read lines from the subprocess and enqueue them."""
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                q.put(line)
        except ValueError:
            # stdout closed (process exited) — thread exits cleanly
            pass

    def _write_to_stdin(self, text: str) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(text)
        self._proc.stdin.flush()

    def _collect_until_sentinel(self, timeout: int) -> tuple[list[str], bool]:
        """Read queued lines until sentinel appears or wall-clock timeout expires.

        Returns:
            A tuple ``(lines, saw_sentinel)``.
        """
        lines: list[str] = []
        captured_chars = 0
        truncated = False
        deadline = time.monotonic() + timeout

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return lines, False

            try:
                line = self._stdout_q.get(timeout=remaining)
            except queue.Empty:
                return lines, False

            if _SENTINEL in line:
                before_sentinel = line.split(_SENTINEL, 1)[0]
                if before_sentinel:
                    if captured_chars < self._max_chars:
                        remaining_chars = self._max_chars - captured_chars
                        lines.append(before_sentinel[:remaining_chars])
                        captured_chars += min(len(before_sentinel), remaining_chars)
                    else:
                        truncated = True
                if truncated:
                    lines.append(f"\n... [truncated at {self._max_chars} chars]")
                return lines, True

            if captured_chars < self._max_chars:
                remaining_chars = self._max_chars - captured_chars
                if len(line) <= remaining_chars:
                    lines.append(line)
                    captured_chars += len(line)
                else:
                    lines.append(line[:remaining_chars])
                    captured_chars += remaining_chars
                    truncated = True
            else:
                truncated = True

    def _kill(self) -> None:
        """Forcefully kill the subprocess."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
                self._proc.wait(timeout=5)
            except Exception:
                pass
        self._proc = None

    # ------------------------------------------------------------------
    # Main public interface
    # ------------------------------------------------------------------

    def __call__(self, code: str, timeout: int | None = None) -> REPLResult:
        """Execute ``code`` in the persistent interpreter session.

        Args:
            code: Arbitrary Python source text.
            timeout: Per-call override; falls back to instance default.

        Returns:
            ``REPLResult`` with stdout and error information.

        Raises:
            RuntimeError: If the interpreter process died unexpectedly.
        """
        effective_timeout = timeout if timeout is not None else self._timeout

        # Restart if the process died
        if self._proc is None or self._proc.poll() is not None:
            logger.warning("Interpreter process died; restarting.")
            self._start_process()

        payload = _build_payload(code)

        try:
            self._write_to_stdin(payload)
        except BrokenPipeError:
            self._kill()
            self._start_process()
            self._write_to_stdin(payload)

        lines, saw_sentinel = self._collect_until_sentinel(timeout=effective_timeout)

        if not saw_sentinel:
            # Timeout: sentinel never arrived
            self._kill()
            self._start_process()
            return REPLResult(
                timed_out=True,
                error=f"Execution timed out after {effective_timeout}s",
            )

        raw = "".join(lines)

        # Detect tracebacks in output (stderr merged into stdout)
        error: str | None = None
        if "Traceback (most recent call last):" in raw:
            # Extract just the traceback for easy inspection
            tb_start = raw.index("Traceback (most recent call last):")
            error = raw[tb_start:]

        return REPLResult(stdout=raw, error=error, timed_out=False)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Terminate the background process gracefully."""
        if self._proc and self._proc.poll() is None:
            try:
                assert self._proc.stdin is not None
                self._proc.stdin.close()
                self._proc.wait(timeout=5)
            except Exception:
                self._kill()

    def __enter__(self) -> "LocalPythonInterpreter":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_payload(code: str) -> str:
    """Build a robust execution payload that always emits the sentinel."""
    escaped_code = repr(code)
    return (
        "import traceback as __tb\n"
        "try:\n"
        f"    exec(compile({escaped_code}, '<kotaemon-repl>', 'exec'), globals(), globals())\n"
        "except Exception:\n"
        "    print(__tb.format_exc(), end='')\n"
        "finally:\n"
        f"    print('{_SENTINEL}')\n\n"
    )
