---
name: pluggable-modules-creating
description: Guides creation of new pluggable kotaemon modules (LLM, embedding, reranking, vector store) using dataclass implementations, vendor enums, and factory registries. Use when adding a new provider class, creating factory.py, refactoring away from theflow Param/Node/BaseComponent, or mirroring the llms/embeddings module layout.
---

# Creating Pluggable Modules

Follow the LLM and embedding modules as the reference layout when adding a
new pluggable component type to `libs/kotaemon/`.

Reference implementations:

- `kotaemon/llms/chats/` — LLM vendors
- `kotaemon/embeddings/` — embedding vendors
- `kotaemon/rerankings/` — reranking vendors (same pattern)

## Module layout

```
kotaemon/<domain>/
├── base.py          # abstract base + shared behaviour
├── factory.py       # Vendor enum + MP_VENDOR_CLS + Factory
├── openai.py        # one file per vendor (or group)
└── ...
```

## Checklist — new pluggable type

```
- [ ] 1. Define base class
- [ ] 2. Implement vendor classes with typed fields
- [ ] 3. Create factory.py (enum + registry + Factory)
```

## 1. Base class

Use `@dataclass(kw_only=True)`. Python native, do not use any extra imports from 3rd packages such as theflow (Param, Node,...).

```python
from dataclasses import dataclass

from kotaemon.base.describe import DataclassDescribe, describe_dataclass


@dataclass(kw_only=True)
class BaseEmbeddings:
    @classmethod
    def describe(cls) -> DataclassDescribe:
        return describe_dataclass(cls)

    def run(self, text: str) -> list[float]:
        raise NotImplementedError
```

- Shared logic across unrelated bases → extract to a module-level function
  (see `kotaemon/base/describe.py`).

## 2. Vendor implementation

Each vendor is a plain `@dataclass` subclass. Fields replace `Param`:

```python
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class OpenAIEmbeddings(BaseEmbeddings):
    api_key: str = field(metadata={"description": "API key"})
    model: str = field(
        default="text-embedding-3-large",
        metadata={"description": "Model name"},
    )
    timeout: float | None = field(
        default=None,
        metadata={"description": "Request timeout"},
    )
```

Rules:

- `field(metadata={"description": ...})` feeds UI via `describe_dataclass`
- Dependencies injected via constructor — not `Node(...)`
- Lazy sub-components → `@cached_property`, not `@Node.auto`
- Object construction → `functools.partial` or `make_*()` factory, not `.withx()`

## 3. Factory registry

Every pluggable set gets a `factory.py`:

```python
from enum import Enum

from .base import BaseEmbeddings
from .openai import OpenAIEmbeddings


class EmbeddingVendor(str, Enum):
    OPENAI = "OpenAIEmbeddings"   # value = class __qualname__


MP_VENDOR_CLS: dict[EmbeddingVendor, type[BaseEmbeddings]] = {
    EmbeddingVendor.OPENAI: OpenAIEmbeddings,
}


class EmbeddingFactory:
    @staticmethod
    def get_cls(vendor: EmbeddingVendor | str) -> type[BaseEmbeddings]:
        key = EmbeddingVendor(vendor)
        if key not in MP_VENDOR_CLS:
            raise ValueError(f"Invalid embedding vendor: {vendor!r}")
        return MP_VENDOR_CLS[key]

    @staticmethod
    def supported_vendors() -> list[EmbeddingVendor]:
        return list(MP_VENDOR_CLS.keys())
```

Naming conventions:

| Item       | Convention                                               |
| ---------- | -------------------------------------------------------- |
| Enum       | `class FooVendor(str, Enum)`                             |
| Enum value | class `__qualname__` (e.g. `"OpenAIEmbeddings"`)         |
| Registry   | `MP_VENDOR_CLS: dict[FooVendor, type[BaseFoo]]` — public |
| Factory    | `get_cls(vendor)` + `supported_vendors()`                |

`get_cls` must accept `VendorEnum | str` so legacy DB rows keep working.

## 4. Adding a new vendor to an existing type

```
- [ ] 1. Implement the class in its own file
- [ ] 2. Add enum member: NEW_VENDOR = "NewClassName"
- [ ] 3. Register in MP_VENDOR_CLS
- [ ] 4. Export if needed from package __init__.py
- [ ] 5. UI dropdown picks it up via Factory.supported_vendors()
```

No `deserialize`, `import_dotted_string`, or `__type__` in spec dicts.

## 5. Typed return shapes

Use `TypedDict` for fixed-key dicts returned from public functions:

```python
class DataclassDescribe(TypedDict):
    type: str
    params: dict[str, DataclassParamDesc]
```

Avoid `dict[str, Any]` on public APIs when the key schema is known.

## Anti-patterns

| Don't                        | Do instead                                           |
| ---------------------------- | ---------------------------------------------------- |
| `Param(help=...)`            | `@dataclass` field + `metadata={"description": ...}` |
| `Node(...)`                  | constructor argument                                 |
| `@Node.auto(...)`            | `@cached_property`                                   |
| `BaseComponent` / `Function` | plain class + narrow Protocol                        |
| `deserialize(spec)`          | `Factory.get_cls(vendor)(**spec)`                    |
| `serialize(obj)`             | plain kwargs dict; type in `vendor` column           |
| `.withx()`                   | `partial()` or named factory                         |
| duplicate classmethod bodies | module-level function                                |

## Verify

After changes, confirm the app starts and the pool loads:

```bash
python app.py
```
