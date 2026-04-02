"""BaseSandbox: stateless, injection-safe file-operation API for agent tools.

Architecture (adapted from langchain/deepagent BaseSandbox pattern):

All complex operations (read, write, edit, ls, glob, grep) are implemented
as self-contained ``python3 -c "..."`` scripts invoked via the abstract
``execute()`` method.  Filesystem paths and content payloads are always
base64-encoded before being interpolated into the command string, completely
neutralising shell-injection via filenames or content containing quotes,
semicolons, backticks, etc.

Concrete subclasses only need to implement:
  - ``execute(command, timeout)`` → ``ExecuteResponse``
  - ``upload_files(files)`` → ``list[FileUploadResponse]``
  - ``download_files(paths)`` → ``list[FileDownloadResponse]``

This design keeps the sandbox backend swappable (local subprocess today,
Docker/remote tomorrow) without touching any of the higher-level logic.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data-transfer objects
# ---------------------------------------------------------------------------


@dataclass
class ExecuteResponse:
    """Result of a sandbox command execution."""

    output: str
    """Combined stdout + stderr from the command."""
    exit_code: int = 0
    """Process exit code (0 = success)."""
    truncated: bool = False
    """True when output was truncated due to size limits."""


@dataclass
class FileInfo:
    """Metadata for a single filesystem entry."""

    path: str
    is_dir: bool


@dataclass
class FileData:
    """File content with encoding hint."""

    content: str
    encoding: str = "utf-8"


@dataclass
class LsResult:
    entries: list[FileInfo] = field(default_factory=list)
    error: str | None = None


@dataclass
class ReadResult:
    file_data: FileData | None = None
    error: str | None = None


@dataclass
class WriteResult:
    path: str | None = None
    error: str | None = None


@dataclass
class EditResult:
    path: str | None = None
    occurrences: int = 0
    error: str | None = None


@dataclass
class GrepMatch:
    path: str
    line: int
    text: str


@dataclass
class GrepResult:
    matches: list[GrepMatch] = field(default_factory=list)
    error: str | None = None


@dataclass
class GlobResult:
    matches: list[FileInfo] = field(default_factory=list)
    error: str | None = None


@dataclass
class FileUploadResponse:
    path: str | None = None
    error: str | None = None


@dataclass
class FileDownloadResponse:
    path: str | None = None
    content: bytes | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Shell command templates (base64 encoded inputs to prevent injection)
# ---------------------------------------------------------------------------

_LS_COMMAND_TEMPLATE = """python3 -c "
import os, json, base64
path = base64.b64decode('{path_b64}').decode('utf-8')
try:
    with os.scandir(path) as it:
        for entry in it:
            print(json.dumps({{'path': os.path.join(path, entry.name), 'is_dir': entry.is_dir(follow_symlinks=False)}}))
except (FileNotFoundError, PermissionError):
    pass
" 2>/dev/null"""

_READ_COMMAND_TEMPLATE = """python3 -c "
import os, sys, base64, json
path = base64.b64decode('{path_b64}').decode('utf-8')
if not os.path.isfile(path):
    print(json.dumps({{'error': 'file_not_found'}})); sys.exit(0)
if os.path.getsize(path) == 0:
    print(json.dumps({{'encoding': 'utf-8', 'content': ''}})); sys.exit(0)
with open(path, 'rb') as f:
    raw = f.read()
try:
    text = raw.decode('utf-8')
except UnicodeDecodeError:
    print(json.dumps({{'encoding': 'base64', 'content': base64.b64encode(raw).decode('ascii')}})); sys.exit(0)
lines = text.splitlines()
offset = {offset}
limit = {limit}
if offset >= len(lines) and lines:
    print(json.dumps({{'error': 'offset ' + str(offset) + ' exceeds file length ' + str(len(lines))}})); sys.exit(0)
text = chr(10).join(lines[offset:offset + limit])
print(json.dumps({{'encoding': 'utf-8', 'content': text}}))
" 2>&1"""

_WRITE_CHECK_TEMPLATE = """python3 -c "
import os, sys, base64
path = base64.b64decode('{path_b64}').decode('utf-8')
if os.path.exists(path):
    print('Error: File already exists: ' + repr(path)); sys.exit(1)
os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
" 2>&1"""

_EDIT_INLINE_MAX_BYTES: int = 50_000

_EDIT_COMMAND_TEMPLATE = """python3 -c "
import sys, os, base64, json
payload = json.loads(base64.b64decode(sys.stdin.read().strip()).decode('utf-8'))
path, old, new = payload['path'], payload['old'], payload['new']
replace_all = payload.get('replace_all', False)
if not os.path.isfile(path):
    print(json.dumps({{'error': 'file_not_found'}})); sys.exit(0)
with open(path, 'rb') as f:
    raw = f.read()
try:
    text = raw.decode('utf-8')
except UnicodeDecodeError:
    print(json.dumps({{'error': 'not_a_text_file'}})); sys.exit(0)
count = text.count(old)
if count == 0:
    print(json.dumps({{'error': 'string_not_found'}})); sys.exit(0)
if count > 1 and not replace_all:
    print(json.dumps({{'error': 'multiple_occurrences', 'count': count}})); sys.exit(0)
result = text.replace(old, new) if replace_all else text.replace(old, new, 1)
with open(path, 'wb') as f:
    f.write(result.encode('utf-8'))
print(json.dumps({{'count': count}}))
" 2>&1 <<'__SANDBOX_EDIT_EOF__'
{payload_b64}
__SANDBOX_EDIT_EOF__"""

_GLOB_COMMAND_TEMPLATE = """python3 -c "
import glob, os, json, base64
path = base64.b64decode('{path_b64}').decode('utf-8')
pattern = base64.b64decode('{pattern_b64}').decode('utf-8')
os.chdir(path)
for m in sorted(glob.glob(pattern, recursive=True)):
    stat = os.stat(m)
    print(json.dumps({{'path': m, 'is_dir': os.path.isdir(m)}}))
" 2>&1"""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SandboxBackendProtocol(Protocol):
    """Interface contract for all sandbox backends."""

    @property
    def id(self) -> str: ...

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse: ...

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]: ...

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]: ...

    def ls(self, path: str) -> LsResult: ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult: ...

    def write(self, file_path: str, content: str) -> WriteResult: ...

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult: ...

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult: ...

    def glob(self, pattern: str, path: str = "/") -> GlobResult: ...


# ---------------------------------------------------------------------------
# Base implementation
# ---------------------------------------------------------------------------


class BaseSandbox(ABC):
    """Abstract base providing full SandboxBackendProtocol via execute().

    Subclasses must implement ``execute()``, ``upload_files()``,
    ``download_files()``, and ``id``.  All higher-level operations are
    derived from those three primitives using base64-encoded python3 scripts.
    """

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for this sandbox instance."""

    @abstractmethod
    def execute(
        self,
        command: str,
        *,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Run a shell command and return its combined output."""

    @abstractmethod
    def upload_files(
        self, files: list[tuple[str, bytes]]
    ) -> list[FileUploadResponse]:
        """Write bytes to paths in the sandbox. Partial failures are allowed."""

    @abstractmethod
    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Read file bytes from the sandbox. Partial failures are allowed."""

    # ------------------------------------------------------------------
    # Derived operations (stateless, injection-safe)
    # ------------------------------------------------------------------

    def ls(self, path: str) -> LsResult:
        """List directory contents with is_dir metadata."""
        path_b64 = base64.b64encode(path.encode()).decode("ascii")
        result = self.execute(_LS_COMMAND_TEMPLATE.format(path_b64=path_b64))
        entries: list[FileInfo] = []
        for line in result.output.strip().splitlines():
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(FileInfo(path=data["path"], is_dir=data["is_dir"]))
            except (json.JSONDecodeError, KeyError):
                continue
        return LsResult(entries=entries)

    def read(
        self,
        file_path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> ReadResult:
        """Read file content with server-side pagination (text files only)."""
        path_b64 = base64.b64encode(file_path.encode()).decode("ascii")
        cmd = _READ_COMMAND_TEMPLATE.format(
            path_b64=path_b64,
            offset=int(offset),
            limit=int(limit),
        )
        result = self.execute(cmd)
        raw = result.output.rstrip()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return ReadResult(error=f"Unexpected response reading '{file_path}': {raw[:200]}")
        if "error" in data:
            return ReadResult(error=f"'{file_path}': {data['error']}")
        return ReadResult(
            file_data=FileData(
                content=data["content"],
                encoding=data.get("encoding", "utf-8"),
            )
        )

    def write(self, file_path: str, content: str) -> WriteResult:
        """Create a new file; fails if the path already exists."""
        path_b64 = base64.b64encode(file_path.encode()).decode("ascii")
        check_result = self.execute(_WRITE_CHECK_TEMPLATE.format(path_b64=path_b64))
        if check_result.exit_code != 0 or "Error:" in check_result.output:
            msg = check_result.output.strip() or f"Failed pre-flight check for '{file_path}'"
            return WriteResult(error=msg)
        try:
            responses = self.upload_files([(file_path, content.encode("utf-8"))])
        except Exception as exc:
            return WriteResult(error=f"Upload failed for '{file_path}': {exc}")
        if not responses or responses[0].error:
            err = responses[0].error if responses else "no response"
            return WriteResult(error=f"Upload error for '{file_path}': {err}")
        return WriteResult(path=file_path)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Replace exact string occurrences in a file."""
        payload_size = len(old_string.encode()) + len(new_string.encode())
        if payload_size <= _EDIT_INLINE_MAX_BYTES:
            return self._edit_inline(file_path, old_string, new_string, replace_all)
        return self._edit_via_upload(file_path, old_string, new_string, replace_all)

    def _edit_inline(
        self,
        file_path: str,
        old: str,
        new: str,
        replace_all: bool,
    ) -> EditResult:
        payload = json.dumps({"path": file_path, "old": old, "new": new, "replace_all": replace_all})
        payload_b64 = base64.b64encode(payload.encode()).decode("ascii")
        cmd = _EDIT_COMMAND_TEMPLATE.format(payload_b64=payload_b64)
        result = self.execute(cmd)
        raw = result.output.rstrip()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return EditResult(error=f"Unexpected response editing '{file_path}': {raw[:200]}")
        if "error" in data:
            return self._map_edit_error(data["error"], file_path, old)
        return EditResult(path=file_path, occurrences=data.get("count", 1))

    def _edit_via_upload(
        self,
        file_path: str,
        old: str,
        new: str,
        replace_all: bool,
    ) -> EditResult:
        """Fallback for large payloads: upload old/new as temp files."""
        uid = base64.b32encode(os.urandom(10)).decode("ascii").lower()
        old_tmp = f"/tmp/.sandbox_edit_{uid}_old"
        new_tmp = f"/tmp/.sandbox_edit_{uid}_new"
        resps = self.upload_files([(old_tmp, old.encode()), (new_tmp, new.encode())])
        if len(resps) < 2 or any(r.error for r in resps):
            errs = [r.error for r in resps if r.error]
            return EditResult(error=f"Temp upload failed for '{file_path}': {errs}")

        old_b64 = base64.b64encode(old_tmp.encode()).decode("ascii")
        new_b64 = base64.b64encode(new_tmp.encode()).decode("ascii")
        tgt_b64 = base64.b64encode(file_path.encode()).decode("ascii")
        cmd = f"""python3 -c "
import os, sys, json, base64
old = open(base64.b64decode('{old_b64}').decode()).read()
new = open(base64.b64decode('{new_b64}').decode()).read()
target = base64.b64decode('{tgt_b64}').decode()
for p in (base64.b64decode('{old_b64}').decode(), base64.b64decode('{new_b64}').decode()):
    try: os.remove(p)
    except OSError: pass
with open(target, 'rb') as f: raw = f.read()
text = raw.decode('utf-8')
count = text.count(old)
if count == 0: print(json.dumps({{'error': 'string_not_found'}})); sys.exit(0)
result = text.replace(old, new) if {replace_all} else text.replace(old, new, 1)
open(target, 'wb').write(result.encode('utf-8'))
print(json.dumps({{'count': count}}))
" 2>&1"""
        result = self.execute(cmd)
        raw = result.output.rstrip()
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return EditResult(error=f"Unexpected response editing '{file_path}': {raw[:200]}")
        if "error" in data:
            return self._map_edit_error(data["error"], file_path, old)
        return EditResult(path=file_path, occurrences=data.get("count", 1))

    @staticmethod
    def _map_edit_error(error: str, file_path: str, old: str) -> EditResult:
        messages = {
            "file_not_found": f"File not found: '{file_path}'",
            "not_a_text_file": f"Not a text file: '{file_path}'",
            "string_not_found": f"String not found in '{file_path}': {old!r}",
            "multiple_occurrences": (
                f"String appears multiple times in '{file_path}'. "
                "Use replace_all=True to replace all occurrences."
            ),
        }
        return EditResult(error=messages.get(error, f"Edit error in '{file_path}': {error}"))

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> GrepResult:
        """Search file contents for a literal string (grep -F)."""
        search_path = shlex.quote(path or ".")
        glob_flag = f"--include='{glob}'" if glob else ""
        cmd = (
            f"grep -rHnF {glob_flag} -e {shlex.quote(pattern)} {search_path} "
            "2>/dev/null || true"
        )
        result = self.execute(cmd)
        matches: list[GrepMatch] = []
        for line in result.output.rstrip().splitlines():
            parts = line.split(":", 2)
            if len(parts) >= 3:  # noqa: PLR2004
                try:
                    matches.append(
                        GrepMatch(path=parts[0], line=int(parts[1]), text=parts[2])
                    )
                except ValueError:
                    continue
        return GrepResult(matches=matches)

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        """Structured glob matching with metadata."""
        pattern_b64 = base64.b64encode(pattern.encode()).decode("ascii")
        path_b64 = base64.b64encode(path.encode()).decode("ascii")
        cmd = _GLOB_COMMAND_TEMPLATE.format(pattern_b64=pattern_b64, path_b64=path_b64)
        result = self.execute(cmd)
        matches: list[FileInfo] = []
        for line in result.output.strip().splitlines():
            try:
                data = json.loads(line)
                matches.append(FileInfo(path=data["path"], is_dir=data["is_dir"]))
            except (json.JSONDecodeError, KeyError):
                continue
        return GlobResult(matches=matches)
