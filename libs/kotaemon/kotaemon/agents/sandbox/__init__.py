"""Sandbox infrastructure for safe agent-side code and file operations.

This package provides:
- ``BaseSandbox`` / ``SandboxBackendProtocol``: stateless, injection-safe API
  for file I/O (read, write, edit, ls, glob, grep) backed by base64-encoded
  python3 sub-scripts.  Any agent (ReAct, ReWOO, CodeAct) can use these.
- ``LocalSandbox``: concrete implementation using ``subprocess.run`` on the
  local filesystem.
- ``LocalPythonInterpreter``: stateful persistent REPL designed for the
  CodeAct strategy where variable state must persist across execution steps.
"""

from .base import BaseSandbox, ExecuteResponse, SandboxBackendProtocol
from .local import LocalSandbox
from .repl import LocalPythonInterpreter

__all__ = [
    "SandboxBackendProtocol",
    "BaseSandbox",
    "ExecuteResponse",
    "LocalSandbox",
    "LocalPythonInterpreter",
]
