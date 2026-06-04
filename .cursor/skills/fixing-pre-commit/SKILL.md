---
name: fixing-pre-commit
description: Fix pre-commit hook failures in kotaemon by running hooks, mapping errors to the right tool (black, isort, flake8, mypy, codespell, etc.), and re-running until clean. Use when pre-commit fails, the user asks to fix lint/format/CI locally, or before committing when hooks must pass.
---

# Fixing Pre-commit

Get hooks green before commit or PR. Config: `.pre-commit-config.yaml` at repo root.

## Workflow

```
- [ ] 1. Run hooks and capture full output
- [ ] 2. Fix one hook category at a time (smallest diff)
- [ ] 3. Re-run failed hook(s), then full suite
- [ ] 4. Stop only when `pre-commit run --all-files` exits 0
```

**Never** use `git commit --no-verify` unless the user explicitly asks.

**Never** `git commit --amend` after a failed hook — fix files and make a **new** commit.

## Commands

```bash
# Full suite (preferred verification)
pre-commit run --all-files

# Single hook (after a targeted fix)
pre-commit run black --all-files
pre-commit run flake8 --all-files

# Only changed files (faster iteration)
pre-commit run --files path/to/file.py

# First-time setup (if hooks missing locally)
pre-commit install
```

If `pre-commit` is not found, install from dev deps (`pip install pre-commit`) then `pre-commit install`.

## Fix order (this repo)

Apply fixes in this order to avoid fighting formatters:

1. **autoflake** — unused imports/vars (`tests/*` excluded)
2. **black** — formatting (line length 88)
3. **isort** — imports (`--profile black`, `known_first_party = ["kotaemon"]`)
4. **flake8** — lint (`max-line-length 88`, `E203` ignored for black)
5. **mypy** — types (`templates/` excluded)
6. **codespell** — spelling (`llm`, `fo` ignored; see `pyproject.toml`)
7. **pre-commit-hooks** — EOF, trailing whitespace, yaml/toml, large files (750kb)
8. **prettier** — markdown/yaml only

Re-run the specific hook, then `--all-files`.

## Hook cheat sheet

| Hook                                        | Typical failure                   | Fix                                                                           |
| ------------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------- |
| `black`                                     | reformatted file                  | Save file; do not hand-format around black                                    |
| `isort`                                     | import order                      | Run isort or let pre-commit rewrite                                           |
| `flake8`                                    | E501, F401, F841, etc.            | Shorten lines, remove dead code, rename unused vars with `_`                  |
| `autoflake`                                 | unused import                     | Delete import; do not noqa unless unavoidable                                 |
| `mypy`                                      | missing types, incompatible types | Add annotations; narrow `Any`; match project mypy args                        |
| `codespell`                                 | typo                              | Fix word or add to ignore list only if project-approved                       |
| `check-added-large-files`                   | file > 750kb                      | Remove asset, gitignore, or use external storage — do not bump limit casually |
| `detect-private-key`                        | key in diff                       | Remove secret; rotate if exposed                                              |
| `trailing-whitespace` / `end-of-file-fixer` | whitespace                        | Accept hook auto-fix                                                          |
| `prettier`                                  | md/yaml layout                    | Accept prettier output                                                        |

## Scope rules

- Fix **only** what hooks report; no drive-by refactors.
- Match existing style in the touched file (see `.cursor/rules/`).
- For mypy on third-party imports: prefer correct types locally; do not weaken global mypy config unless asked.
- Do not change `.pre-commit-config.yaml` or CI to “make green” without user approval.

## Staged vs unstaged

If the user is mid-commit and hooks auto-modified files:

1. Stage hook fixes: `git add` the reformatted paths.
2. Re-run `pre-commit run` (or commit again if hooks run on commit).

## When stuck

Report back with:

- Failing hook id(s)
- File paths and error lines
- What you tried

Ask before: disabling a hook, adding broad `# noqa` / `# type: ignore`, or large config changes.

## Verify

```bash
pre-commit run --all-files
```

Exit code must be `0` before claiming pre-commit is fixed.
