---
name: python-guidelines
description: Use when writing, reviewing, or refactoring Python code in this workspace. Applies local Python standards for typing, testing, data modeling, API boundaries, logging, and maintainable module design.
---

# Python

Apply these guidelines when the task materially involves Python code.

## Priorities

1. Keep changes scoped to the request.
2. Prefer the simplest implementation that matches the surrounding codebase.
3. Use modern Python features where they improve clarity, not novelty.
4. Make behavior easy to verify with focused tests.

## Coding Standards

- Follow Python and PEP guidance unless the codebase already uses a different local convention.
- Keep production code clear and direct; avoid speculative abstractions and single-use indirection.
- Use guard clauses and fail fast when preconditions are invalid.
- Use type hints on public functions, non-trivial internal helpers, and tests.
- Limit the use of global variables to reduce side effects.
- Use comprehensions when they improve readability; do not compress complex logic into one expression.
- Handle expected failure modes explicitly, typically with narrow `try`/`except` blocks. Do not add defensive exception handling for impossible paths.
- Prefer `pathlib` over `os.path` for filesystem paths.

## Modular Design

- Prefer small, cohesive modules with clear ownership boundaries.
- Prefer modular design with clear separation of responsibilities such as models, services, controllers, and utilities, unless the codebase already uses a different structure.
- When a module has distinct failure cases, define focused exceptions where they improve call-site clarity.

## Data and Modeling

- Separate data containers from behavioral services when that makes the code easier to reason about.
- Prefer placing behavior on the type it naturally belongs to when that avoids duplicated logic across call sites.
- Prefer explicit types and named fields over loosely typed dictionaries for stable internal or external shapes.
- Prefer passing and returning typed objects for non-trivial workflows when that makes interfaces clearer and more stable.
- Prefer explicit modes (Enum, strategy object, registry) over many interacting boolean flags at workflow boundaries.
  - Use `enum.StrEnum` (or equivalent) for wire-backed labels, with serialize or display helpers on the enum instead of parallel lookup dicts scattered at call sites.
  - Use `dataclasses.dataclass` for simple structured data.
  - Use `pydantic.dataclasses.dataclass` when dataclass ergonomics are preferred but validation is still required.
  - Use `pydantic.BaseModel` only where validation, serialization, or wire-shape guarantees are actually needed.

## External APIs and SDKs

- Type SDK and HTTP boundaries with library-provided or locally defined models where practical.
- Build request payloads from typed objects when that keeps call sites simpler and more reliable.
- Validate shared configuration once, close to settings or initialization, rather than repeating partial checks in consumers.
- Prefer explicit variant handling such as `isinstance` or `match` over `getattr` chains on opaque objects.

## Logging

- Use `structlog` for non-trivial workflows when the project already depends on it or structured logs are materially useful.
- Do not replace straightforward local feedback with heavy logging scaffolding unless the task needs it.

## Testing

- Add or update tests for behavior changes, bug fixes, and non-trivial refactors.
- Keep tests in `./tests` unless the codebase clearly uses another layout.
- Use `pytest`; do not introduce `unittest`.
- Use `pytest.mark.parametrize` for meaningful input matrices; pass parameter names as tuples.
- Use fixtures to isolate third-party dependencies and prefer `autospec` when mocking.
- Use `pytest.mark.asyncio` for async tests when required by the test stack.
- Type-annotate tests where the project already does so or where it improves clarity.
- Add `__init__.py` files only if the codebase's test/package layout requires them.

## Documentation

- Write docstrings for non-obvious public functions, classes, and modules.
- Keep docstrings concise and focused on behavior or contract.
- Update nearby documentation or README content only when the user-facing behavior or setup actually changed.
