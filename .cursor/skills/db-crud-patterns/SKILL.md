---
name: db-crud-patterns
description: Guides DB model design, CRUD classes, and manager loading for persisted pluggable config in ktem — vendor column separation, spec as kwargs-only JSON, BaseCRUD context manager, and migrating away from __type__ in spec. Use when adding DB tables, writing CRUD for model pools, refactoring managers, or migrating legacy deserialize/__type__ query logic.
---

# DB & CRUD Patterns

Follow the LLM and embedding stack as the reference when persisting
pluggable modules (model pools) in `libs/ktem/`.

Reference implementations:

- `ktem/db/models/llm.py` + `ktem/db/cruds/llm.py` + `ktem/llms/manager.py`
- `ktem/db/models/embedding.py` + `ktem/db/cruds/embedding.py` + `ktem/embeddings/manager.py`
- `ktem/rerankings/manager.py` — same load pattern

Pair with: [creating-pluggable-modules](../creating-pluggable-modules/SKILL.md)
for the kotaemon-side factory/registry.

## Core principle — separate type from data

```
vendor column  →  which class to instantiate (factory key)
spec column    →  constructor kwargs only (plain JSON)
```

Never embed `"__type__"` in `spec`. Never `deepcopy` + `del params["__type__"]`.

```python
# Load — one expression, no key surgery
model = LLMFactory.get_cls(item.vendor)(**item.spec)
```

## Checklist — new persisted pool

```
- [ ] 1. Abstract DB model: name, vendor, spec, default
- [ ] 2. Concrete table in ktem/db/models/tables.py
- [ ] 3. CRUD class extending BaseCRUD
- [ ] 4. Manager: load via Factory.get_cls(item.vendor)(**item.spec)
- [ ] 5. UI: pass vendor separately on create/update
- [ ] 6. Migration script if replacing __type__-in-spec rows
```

## 1. DB model

```python
from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from kotaemon.llms.chats.factory import LLMVendor

from .base import Base


class BaseLLM(Base):
    __abstract__ = True

    name: Mapped[str] = mapped_column(String, primary_key=True)
    vendor: Mapped[LLMVendor] = mapped_column(String)
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    default: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def ui(self) -> dict[str, Any]:
        return {"name": self.name, "vendor": self.vendor, "default": self.default}
```

Rules:

- `vendor` typed as the `str, Enum` from kotaemon factory
- `spec` is kwargs-only — no framework metadata, no `__type__`
- `ui` property exposes what Gradio needs; keep spec out of it

## 2. CRUD class

Extend `BaseCRUD` — always use as a context manager:

```python
with LLMCRUD(engine) as crud:
    item = crud.get("my-model")
    crud.update("my-model", spec={"api_key": "..."})
```

Standard methods for model pools:

| Method                                                  | Purpose                               |
| ------------------------------------------------------- | ------------------------------------- |
| `create(name, vendor, spec, *, default=False)`          | insert; demote others if default      |
| `get(name)`                                             | primary-key lookup                    |
| `list_all()`                                            | `select(Table)` → list                |
| `update(name, *, vendor=None, spec=None, default=None)` | partial update                        |
| `delete(name)`                                          | remove row                            |
| `clear_defaults()`                                      | `update(Table).values(default=False)` |

Signature pattern — `vendor` is always separate from `spec`:

```python
def create(
    self,
    name: str,
    vendor: LLMVendor,
    spec: dict[str, Any],
    *,
    default: bool = False,
) -> LLMTable:
    if not name:
        raise ValueError("Name must not be empty")
    if self.get(name) is not None:
        raise ValueError(f"LLM '{name}' already exists")
    if default:
        self.clear_defaults()
    item = LLMTable(name=name, vendor=vendor, spec=spec, default=default)
    self.session.add(item)
    self.commit()
    self.session.refresh(item)
    return item
```

CRUD rules:

- Validate early (`ValueError` on empty name, duplicate, not found)
- `default=True` → call `clear_defaults()` in the same transaction
- Use `self.commit()` (rolls back on failure) — not raw session commits
- Keyword-only booleans (`*, default: bool = False`)

## 3. Manager loading

Manager owns the in-memory pool; CRUD owns DB access.

```python
class LLMManager:
    def load(self) -> None:
        self._models, self._info, self._default = {}, {}, ""
        with LLMCRUD(engine) as crud:
            for item in crud.list_all():
                cls = LLMFactory.get_cls(item.vendor)
                self._models[item.name] = cls(**item.spec)
                self._info[item.name] = item
                if item.default:
                    self._default = item.name

    def add(self, name: str, vendor: LLMVendor, spec: dict, default: bool) -> None:
        with LLMCRUD(engine) as crud:
            crud.create(name=name, vendor=vendor, spec=spec, default=default)
        self.load()

    def update(self, name: str, vendor: LLMVendor, spec: dict, default: bool,
               new_name: str = "") -> None:
        # rename = delete + add; otherwise crud.update(...)
        self.load()
```

Manager rules:

- Reload pool after every mutating operation (`self.load()`)
- `add` / `update` take `vendor` and `spec` as separate args
- No `deserialize`, no spec key surgery in the manager

## 4. UI integration

```python
# Dropdown — enum values as plain strings
choices=[v.value for v in LLMFactory.supported_vendors()]

# Create — coerce UI string to enum
vendor = LLMVendor(selected_vendor)
llms.add(name, vendor=vendor, spec=spec, default=default)

# Edit — spec is already clean
edit_spec = yaml.dump(item.spec)   # no spec.pop("__type__")

# Save — vendor from row, not from spec
llms.update(name, vendor=item.vendor, spec=spec, default=default)

# Test connection — merge edited params, construct via factory
params = {**item.spec, **yaml.load(edited_yaml)}
llm = LLMFactory.get_cls(item.vendor)(**params)
```

## 5. Migrating legacy **type**-in-spec rows

When refactoring an existing table:

```sql
ALTER TABLE llm_table ADD COLUMN vendor VARCHAR;
UPDATE llm_table SET vendor = json_extract(spec, '$.__type__');
-- then strip __type__ from spec JSON in application code or migration script
```

Before (remove this pattern):

```python
params = deepcopy(item.spec)
del params["__type__"]
model = deserialize(item.spec, safe=False)
```

After:

```python
model = LLMFactory.get_cls(item.vendor)(**item.spec)
```

Symptom of wrong schema: any `deepcopy` + `del` on spec keys. Fix the
schema, not the call site.

## 6. Query patterns

Use SQLAlchemy 2.0 style via the session on `BaseCRUD`:

```python
from sqlalchemy import select, update

# list all
list(self.session.scalars(select(LLMTable)).all())

# primary key
self.session.get(LLMTable, name)

# bulk update
self.session.execute(update(LLMTable).values(default=False))
```

Keep queries inside CRUD — managers call CRUD methods, not raw SQL.

## Anti-patterns

| Don't                                 | Do instead                                  |
| ------------------------------------- | ------------------------------------------- |
| `spec["__type__"]` in JSON            | `vendor` column                             |
| `deserialize(spec, safe=False)`       | `Factory.get_cls(item.vendor)(**item.spec)` |
| `deepcopy` + `del params["__type__"]` | clean schema with separate vendor           |
| CRUD `create(name, spec)` only        | `create(name, vendor, spec)`                |
| Manager constructs from spec alone    | manager uses vendor + spec                  |
| Raw session outside context manager   | `with FooCRUD(engine) as crud:`             |

## Verify

```bash
python app.py
```

Confirm pool loads, UI create/edit/save works, and no `__type__` appears
in new rows.
