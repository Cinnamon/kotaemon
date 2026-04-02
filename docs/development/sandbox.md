# Sandbox Infrastructure

Kotaemon's sandbox layer provides a safe, flexible execution environment for
agent-driven code and file operations. It is **agent-agnostic** — any reasoning
strategy (ReAct, ReWOO, CodeAct, etc.) can use the sandbox to interact with the
host filesystem or evaluate Python code without touching lower-level subprocess
APIs directly.

---

## Architecture Overview

The sandbox is split into two complementary abstractions with distinct
responsibilities:

```
kotaemon.agents.sandbox
├── base.py        → SandboxBackendProtocol + BaseSandbox  (stateless file ops)
├── local.py       → LocalSandbox                          (concrete: local host)
└── repl.py        → LocalPythonInterpreter                (stateful Python REPL)
```

### 1. Stateless Sandbox — `BaseSandbox` / `LocalSandbox`

Provides safe file-system primitives (`ls`, `read`, `write`, `edit`, `grep`,
`glob`) that any agent tool can call. Every operation is implemented as a
self-contained `python3 -c "..."` script executed via the abstract `execute()`
method. Paths and content payloads are always **Base64-encoded** before being
interpolated into the command string, completely preventing shell injection via
user-controlled filenames or content.

```python
from kotaemon.agents.sandbox import LocalSandbox

sb = LocalSandbox()
result = sb.read("/path/to/file.txt")
sb.edit("/path/to/file.txt", old_string="foo", new_string="bar")
```

### 2. Stateful Python REPL — `LocalPythonInterpreter`

Designed for the **CodeAct reasoning strategy** where the LLM generates
iterative Python code blocks and variable state must persist between steps:

```python
from kotaemon.agents.sandbox import LocalPythonInterpreter

with LocalPythonInterpreter() as interp:
    interp("df = pd.read_csv('data.csv')")   # step 1: load data
    result = interp("print(df.describe())")  # step 2: df still in scope ✓
```

A single `python -i` subprocess is kept alive across calls. A sentinel-based
stdout protocol (`__KOTAEMON_EXEC_DONE__`) signals completion without polling.
A daemon reader thread drains output asynchronously. On timeout, the process is
killed and automatically restarted for the next call.

---

## Sandbox Comparison

| Feature | `LocalSandbox` | `LocalPythonInterpreter` |
|---|---|---|
| **Primary use** | File I/O for any agent tool | Code execution for CodeAct |
| **State across calls** | ❌ Stateless (fresh process each call) | ✅ Persistent (same process) |
| **Injection safety** | ✅ Base64-encoded inputs | ✅ Code wrapped in `try/except` |
| **Shell access** | ✅ Full shell via `execute()` | ❌ Python only |
| **Timeout handling** | ✅ `subprocess.run(timeout=N)` raises `TimeoutError` | ✅ Kill + auto-restart |
| **Error isolation** | Process exits and returns exit code | Exception captured, session survives |
| **File operations** | `ls`, `read`, `write`, `edit`, `grep`, `glob` | None (use `LocalSandbox` alongside) |
| **Memory footprint** | Minimal (spawned per call) | One persistent Python process |
| **Concurrency** | ✅ Naturally parallel (independent processes) | ⚠️ Single-threaded (one REPL per agent) |
| **Backend-swappable** | ✅ Yes (Docker, remote via subclass) | ❌ Local only |

---

## Security Model

!!! warning "MVP Security Notice"
    Both sandbox implementations run with the **same filesystem and network
    permissions as the parent Kotaemon process**. This is intentional for the
    MVP to avoid Docker infrastructure overhead, but means untrusted user-provided
    code has host-level access.

The following mitigations are in place:

- **Shell injection prevention**: All user-controlled strings (file paths,
  content) passed to `LocalSandbox.execute()` commands are Base64-encoded before
  interpolation. A path like `"; rm -rf /"` becomes harmless base64 inside the
  python script.
- **Runaway loop protection**: `LocalPythonInterpreter` enforces a per-call
  `timeout` (default 30s). On expiry the subprocess is `SIGKILL`-ed and
  restarted.
- **Exception isolation**: User code in `LocalPythonInterpreter` is wrapped in
  `try/except` so runtime errors (including `SyntaxError`) are captured and
  returned without crashing the persistent session.
- **Runtime warning**: `LocalSandbox` emits a `UserWarning` on instantiation to
  notify developers of the permission boundary.

---

## Pros & Cons

### `LocalSandbox`

| ✅ Pros | ⚠️ Cons |
|---|---|
| Injection-safe by design (Base64 protocol) | `shell=True` required for heredoc patterns |
| Backend-agnostic (swap local → Docker by subclassing) | No persistent state between calls |
| Full filesystem API for any agent to use | Host-level permissions (MVP limitation) |
| Simple to reason about (each call is isolated) | |

### `LocalPythonInterpreter`

| ✅ Pros | ⚠️ Cons |
|---|---|
| True multi-turn state (critical for CodeAct) | Local-only; not swappable to remote |
| Errors don't terminate the session | One REPL per agent instance (not concurrent) |
| Automatic kill + restart on timeout | `python -i` interactive mode may differ slightly from script mode |
| Output capped to prevent memory exhaustion | Sentinel protocol adds a small per-call overhead |

---

## Extending the Sandbox

To add a new backend (e.g. Docker, remote code execution service), subclass
`BaseSandbox` and implement three methods:

```python
from kotaemon.agents.sandbox.base import BaseSandbox, ExecuteResponse, FileUploadResponse, FileDownloadResponse

class DockerSandbox(BaseSandbox):

    @property
    def id(self) -> str:
        return self._container_id

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        # run command inside Docker container
        ...

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        # docker cp or tar stream
        ...

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        # docker cp
        ...
```

All higher-level operations (`ls`, `read`, `write`, `edit`, `grep`, `glob`) are
inherited automatically from `BaseSandbox` with no changes required.

---

## Related

- [`kotaemon.agents.sandbox`](../../kotaemon/libs/kotaemon/kotaemon/agents/sandbox/) — source
- [`tests/test_sandbox.py`](../../kotaemon/libs/kotaemon/tests/test_sandbox.py) — test suite
- [CodeAct Agent](./codeact-agent.md) — the primary consumer of `LocalPythonInterpreter`
