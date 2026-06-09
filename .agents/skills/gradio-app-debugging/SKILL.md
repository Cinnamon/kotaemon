---
name: gradio-app-debugging
description: >-
  Debug Kotaemon Gradio app by running python app.py, fixing Traceback errors
  from terminal logs, and iterating with the user on basic UI smoke tests.
  Appends a session log of bugs and fixes. Use when the user asks to debug the
  app, test UI after code changes, watch terminal logs, or run an interactive
  debug session.
---

# Debugging Gradio App

Interactive debug loop for Kotaemon (`app.py` + Gradio UI).

## Prerequisites

- Run from **repo root** (`kotaemon/`).
- Use project venv when available: `.venv/bin/python app.py`.
- **Debug mode must be on** so errors surface in the terminal:
  - `KH_GRADIO_DEBUG=true` (project default), or
  - `debug=True` passed to `demo.launch()` in `app.py`.
- `debug=True` shows errors in the terminal; it does **not** hot-reload code.
  After every code fix, **restart** the server (kill old process → run again).
- Optional faster iteration: `GRADIO_WATCH_DIRS="libs/kotaemon,libs/ktem" gradio app.py`
  (requires `app.py` compatible with Gradio reload mode).

## What to fix vs ignore

| Signal                                                       | Action                                   |
| ------------------------------------------------------------ | ---------------------------------------- |
| `Traceback (most recent call last)`                          | **Fix** — only this counts as a bug      |
| Startup crash before server is up (caused by traceback)      | **Fix**                                  |
| `Warning`, `WARN`, `SAWarning`, `DeprecationWarning`         | **Ignore**                               |
| `ERROR` / `Exception` without a traceback                    | **Ignore** unless user reports broken UI |
| HTTP 500 without traceback in terminal                       | **Ignore** unless user reports broken UI |
| Browser console noise                                        | **Ignore** (user must paste if relevant) |
| Benign info (model download, Gradio startup, LanceDB create) | **Ignore**                               |

**Rule:** Only fix when terminal shows a Python **Traceback**. Do not chase
warnings or noisy log lines.

## Session log (required)

At the **start** of each debug session, create a log file:

```
.cursor/debug-sessions/YYYY-MM-DD_HH-MM-SS.md
```

Use local time or UTC consistently within one session. Also write/overwrite:

```
.cursor/debug-sessions/latest.md
```

(symlink not required — copy or same content is fine.)

### Log header (once per session)

```markdown
# Debug session — YYYY-MM-DD HH:MM:SS

- **Command:** `.venv/bin/python app.py` (or equivalent)
- **URL:** (fill when server is up)

## Fixes

(none yet)
```

### Append one block per fix

After each traceback fix, **append** to the session log:

```markdown
### Fix N — short title

- **Trigger:** startup | UI — describe user action if UI
- **Error:** one-line summary (exception type + message)
- **Traceback (excerpt):**
```

last 5–10 relevant lines

```
- **Root cause:** one sentence
- **Files changed:** `path/to/file.py`
- **Fix:** what changed and why (1–3 sentences)
- **Verified:** restart OK / user retried action OK
```

If the session ends with **no** fixes, write `## Fixes\n\nNo tracebacks in this session.`

The user uses this file later to summarize bugs and fixes — keep entries factual
and concise.

## Workflow

```
- [ ] 0. Create session log file
- [ ] 1. Startup — run app, fix tracebacks until server is healthy
- [ ] 2. UI smoke — user clicks through UI, agent watches logs, fix tracebacks & loop
- [ ] 3. Report — point user to session log + brief summary
```

---

## Bước 1: Startup

- Bước 1: hãy chạy python app.py tử terminal. Nếu có bugs thì hãy fix (phải bật chế độ debug để có thể reflect những gì đã sửa).

### Run

Start in a **background** terminal (keep it alive for Step 2):

```bash
cd /path/to/kotaemon
.venv/bin/python app.py
```

If a server is already running on the same port, **stop it first** (kill the
old shell/process) before restarting after a fix.

### Poll until ready or failed

Use `Await` on the terminal file. Success signals:

- `Running on local URL: http://127.0.0.1:7860` (port may differ)
- Server listening on 7860, no traceback after startup

Failure — fix only if traceback present:

- `Traceback (most recent call last)` (+ following exception lines)

### Fix loop

1. Read the **full** traceback from terminal output.
2. Fix the root cause (minimal diff; match project style).
3. **Append fix entry** to session log.
4. Kill the crashed/running server.
5. Re-run `python app.py`.
6. Repeat until startup has no traceback.

**Do not** claim Step 1 is done while the server is down or still traceback-ing.

---

## Bước 2: UI smoke test with log watch

- Bước 2: hãy yêu cầu người dùng thao tác với UI các thao tác cơ bản, bạn ngồi canh logs từ terminal, nếu có thì fix và lặp lại. cho tới khi người dùng xong

### Tell the user

Share the local URL from Step 1 logs, then ask them to perform **basic
operations** (adapt to visible tabs):

| Area        | Actions                                                                   |
| ----------- | ------------------------------------------------------------------------- |
| Login       | Sign in (default dev creds: `admin` / `admin` when user management is on) |
| Chat        | Open Chat tab, send a short message, wait for response                    |
| Collections | Open file/index tab, list or upload a small test file if available        |
| Settings    | Open Settings, change a harmless option or open model pools               |
| Resources   | Open Resources / Users tab if present                                     |
| Help        | Open Help tab                                                             |

Ask the user to **report what they clicked** and **what looked wrong** in the
UI, not only errors.

### Watch logs

Keep polling the **same** background terminal.

- **Fix:** `Traceback (most recent call last)` during or after a user action
- **Ignore:** warnings, deprecation notices, SAWarning, benign INFO lines

### Fix loop

When logs show a **traceback**:

1. Note **user action → error** mapping.
2. Fix code (minimal scope).
3. **Append fix entry** to session log.
4. Restart `python app.py` (debug still on).
5. Ask user to **retry the same action**.
6. Confirm no new traceback for that path before moving on.

Continue until the user says they are **done** with UI testing.

---

## Commands reference

```bash
# Start (background — preferred for Step 2 log watching)
.venv/bin/python app.py

# Quick import smoke test (no browser; catches many startup errors faster)
.venv/bin/python -c "from ktem.main import App; App().make(); print('OK')"

# After touching Python files (optional, before restart)
pre-commit run --files path/to/changed.py
```

## Scope rules

- Fix **only** tracebacks found in this session.
- Do **not** fix warnings unless the user explicitly asks.
- No drive-by refactors.
- Prefer root-cause fixes over silencing errors.
- If the fix needs env/API keys the user lacks, log as **blocked** in session
  file and skip that UI path.

## When stuck

Report back with:

- Exact terminal traceback
- User action that triggered it
- Session log path
- Files changed and what was tried
- Whether the server is currently running and on which URL

Ask the user before: disabling features globally, weakening error handling, or
large architectural changes just to pass smoke tests.

## Step 3: Report

When the user is done:

1. Point to **`.cursor/debug-sessions/latest.md`** (and timestamped copy).
2. Brief summary: count of fixes, server URL, still running or not.
3. **Untested paths** (missing credentials, features disabled, etc.).
