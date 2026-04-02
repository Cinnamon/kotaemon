# Repository Guidelines

## Project Structure & Module Organization
- `libs/kotaemon/`: core Python library (agents, loaders, LLM/embedding integrations, storage, indexing).
- `libs/ktem/`: web app/UI package and app-level services (`ktem/main.py`, `ktem/pages/*`, assets).
- `app.py`, `sso_app.py`, `sso_app_demo.py`: runtime entry points.
- `libs/kotaemon/tests/` and `libs/ktem/ktem_tests/`: unit/integration tests.
- `docs/`: MkDocs content; `scripts/`: setup/update/runtime utilities; `templates/`: cookiecutter templates.

## Build, Test, and Development Commands
- `pip install -e "libs/kotaemon[dev]" && pip install -e "libs/ktem"`: install editable dev dependencies.
- `python app.py`: run the default local Gradio app.
- `bash scripts/run_linux.sh` (or `run_macos.sh` / `run_windows.bat`): OS-specific bootstrap/run flow.
- `pre-commit run --all-files`: run formatting, linting, typing, and safety hooks.
- `pytest libs/kotaemon/tests libs/ktem/ktem_tests`: run test suites.

## Coding Style & Naming Conventions
- Target Python `>=3.11`.
- Format with `black` (line length `88`) and `isort --profile black`.
- Lint with `flake8` (`--max-line-length 88 --extend-ignore E203`).
- Type-check with `mypy` (configured in pre-commit with `--check-untyped-defs`).
- Use `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.

## Testing Guidelines
- Framework: `pytest` (see `libs/kotaemon/pytest.ini`; minimum version `7.4`).
- Test files should be named `test_*.py`; keep fixtures in `conftest.py`.
- Add/adjust tests in the package you changed (`libs/kotaemon/tests` or `libs/ktem/ktem_tests`).
- No explicit coverage gate is defined; include regression tests for bug fixes and new behavior.

## Commit & Pull Request Guidelines
- Follow Conventional Commit style seen in history: `feat: ...`, `fix: ...`, `tests: ...`, `docs: ...`.
- Keep PR titles compliant with commit convention (squash merge uses PR title as final commit).
- PRs should include: concise change summary, linked issue(s), and screenshots/GIFs for UI changes.
- Ensure CI is green: pre-commit checks, tests, and PR title validation.

## Security & Configuration Tips
- Copy `.env.example` to `.env` for local config; never commit secrets.
- Pre-commit includes secret checks (`detect-aws-credentials`, `detect-private-key`) and large-file checks.
