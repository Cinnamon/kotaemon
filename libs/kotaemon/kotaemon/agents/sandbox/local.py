"""LocalSandbox: concrete BaseSandbox backed by the local filesystem.

Uses ``subprocess.run`` on the host machine — no Docker, no remote calls.
Suitable for trusted-local or MVP deployments.

Security note:
    LocalSandbox has the same filesystem/network permissions as the parent
    process.  Commands passed via ``execute()`` run through /bin/sh (shell=True
    unavoidable for the base64-heredoc patterns in BaseSandbox templates) but
    *all content interpolated into those commands is base64-encoded*, which
    prevents injection via user-controlled paths or strings.  A runtime warning
    is emitted when the sandbox is first instantiated.

Upload/download are direct ``open()`` calls — no network round-trip.
"""

from __future__ import annotations

import logging
import os
import subprocess
import uuid
import warnings

from .base import (
    BaseSandbox,
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30  # seconds


class LocalSandbox(BaseSandbox):
    """Concrete sandbox running commands on the local host via subprocess.

    Args:
        working_dir: Optional directory to use as cwd for all commands.
            Defaults to CWD of the parent process.
        default_timeout: Default execution timeout in seconds (default 30).
        warn_on_init: Emit a ``UserWarning`` at construction time reminding
            callers that this sandbox has host-level permissions.
    """

    def __init__(
        self,
        working_dir: str | None = None,
        default_timeout: int = _DEFAULT_TIMEOUT,
        warn_on_init: bool = True,
    ) -> None:
        self._id = str(uuid.uuid4())
        self._working_dir = working_dir or os.getcwd()
        self._default_timeout = default_timeout

        if warn_on_init:
            warnings.warn(
                "LocalSandbox is running with the same filesystem and network "
                "permissions as the parent process.  Only use with trusted code.",
                UserWarning,
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self._id

    # ------------------------------------------------------------------
    # Core primitive
    # ------------------------------------------------------------------

    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Run ``command`` in /bin/sh and return combined stdout+stderr.

        Args:
            command: Shell command string.
            timeout: Seconds before ``subprocess.TimeoutExpired`` is raised;
                     falls back to ``default_timeout`` when None.

        Returns:
            ``ExecuteResponse`` with combined output and exit code.

        Raises:
            TimeoutError: When the command exceeds the timeout.
        """
        effective_timeout = timeout if timeout is not None else self._default_timeout
        try:
            proc = subprocess.run(
                command,
                shell=True,  # required — commands use heredoc and python3 -c patterns
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=self._working_dir,
            )
            output = proc.stdout + proc.stderr
            return ExecuteResponse(
                output=output,
                exit_code=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Command timed out after {effective_timeout}s: {command[:80]!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Upload / download (local: direct file I/O)
    # ------------------------------------------------------------------

    def upload_files(
        self, files: list[tuple[str, bytes]]
    ) -> list[FileUploadResponse]:
        """Write bytes to local paths.  Creates parent directories as needed."""
        responses: list[FileUploadResponse] = []
        for path, content in files:
            try:
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "wb") as fh:
                    fh.write(content)
                responses.append(FileUploadResponse(path=path))
            except Exception as exc:  # noqa: BLE001
                responses.append(FileUploadResponse(error=str(exc)))
        return responses

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Read file bytes from local paths."""
        responses: list[FileDownloadResponse] = []
        for path in paths:
            try:
                with open(path, "rb") as fh:
                    responses.append(FileDownloadResponse(path=path, content=fh.read()))
            except Exception as exc:  # noqa: BLE001
                responses.append(FileDownloadResponse(path=path, error=str(exc)))
        return responses
