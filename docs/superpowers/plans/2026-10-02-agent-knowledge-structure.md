# Knowledge Metadata and Structure-Aware Chunking Implementation Plan

> **For agentic workers:** Use `superpowers:subagent-driven-development` to execute this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add canonical knowledge metadata and source-aware chunk strategies to Kotaemon's existing ingestion path while preserving the current TokenSplitter fallback and legacy document compatibility.

**Architecture:** Add JSON-compatible normalization helpers and an extensible chunk-strategy registry to kotaemon core. Integrate the registry into ktem's existing IndexPipeline, preserve file-level scope metadata in the existing Source.note JSON field, and adapt the current Excel and Unstructured readers only where they expose reliable row or slide boundaries.

**Tech Stack:** Python 3.10+, Pydantic/LlamaIndex Document, existing TokenSplitter, Python ast, existing pandas/openpyxl and Unstructured optional readers, pytest, uv.

## Global Constraints

- Do not change Kotaemon's Document or RetrievedDocument schema.
- Store canonical metadata in Document.metadata and preserve loader-specific keys such as file_id, file_path, page_label, and sheet_name.
- Supported source types are wiki, markdown, pdf, faq, code, ppt, excel, and other.
- virtual_path is a logical namespace; never expose a temporary absolute upload path as the default logical path and never access the filesystem through virtual_path.
- Keep the existing configured TokenSplitter as fallback for unsupported source types, malformed structure, parser failures, unsupported languages, missing slide boundaries, and oversized semantic units.
- Do not add a mandatory parser dependency, Wiki connector, parallel RAG pipeline, vector database, or schema migration.
- Older chunks without canonical metadata remain valid. New metadata is populated on new and reindexed chunks only.
- Preserve the existing ktem file selector, storage lifecycle, and citation compatibility.

---

### Task 1: Canonical Knowledge Metadata

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/__init__.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/schema.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/metadata.py`
- Test: `libs/kotaemon/tests/test_knowledge_metadata.py`

**Interfaces:**
- Consumes: `kotaemon.base.Document`, its current metadata, and optional metadata overrides.
- Produces: `SUPPORTED_SOURCE_TYPES`, `infer_source_type(metadata, document_name=None) -> str`, `normalize_virtual_path(value, document_name) -> str`, and `normalize_knowledge_metadata(document, overrides=None) -> dict[str, Any]`.
- `normalize_knowledge_metadata` copies existing metadata, merges caller overrides, and returns a new dictionary containing every canonical key. It does not mutate or replace the Document.

- [ ] **Step 1: Write failing tests for metadata normalization**

```python
import pytest

from kotaemon.base import Document
from kotaemon.indices.knowledge.metadata import normalize_knowledge_metadata


def test_normalizes_metadata_and_preserves_loader_fields():
    document = Document(
        text="RAG work",
        metadata={
            "file_id": "file-7",
            "file_name": "Zhang San.md",
            "file_path": "/tmp/upload-2/Zhang San.md",
            "page_label": 3,
            "loader_tag": "keep",
        },
        source="original-source",
    )

    metadata = normalize_knowledge_metadata(
        document, {"virtual_path": "/Interns/App/Zhang San"}
    )

    assert metadata["source_type"] == "markdown"
    assert metadata["virtual_path"] == "/Interns/App/Zhang San"
    assert metadata["document_id"] == "file-7"
    assert metadata["document_name"] == "Zhang San.md"
    assert metadata["chunk_id"] == document.doc_id
    assert metadata["page"] == 3
    assert metadata["entity"] == {}
    assert metadata["file_path"] == "/tmp/upload-2/Zhang San.md"
    assert metadata["page_label"] == 3
    assert metadata["loader_tag"] == "keep"
    assert metadata["source"] == "original-source"


def test_default_virtual_path_uses_name_not_absolute_file_path():
    document = Document(
        text="body",
        metadata={"file_name": "manual.pdf", "file_path": "/private/tmp/manual.pdf"},
    )

    metadata = normalize_knowledge_metadata(document)

    assert metadata["virtual_path"] == "/manual.pdf"
    assert "/private" not in metadata["virtual_path"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("sample.py", "code"), ("table.xlsx", "excel"), ("notes.md", "markdown")],
)
def test_infers_source_type_from_document_name(name, expected):
    document = Document(text="body", metadata={"file_name": name})
    assert normalize_knowledge_metadata(document)["source_type"] == expected


def test_invalid_explicit_source_type_becomes_other():
    document = Document(text="body", metadata={"file_name": "notes.md"})
    metadata = normalize_knowledge_metadata(document, {"source_type": "unknown"})
    assert metadata["source_type"] == "other"


def test_explicit_wiki_source_type_is_preserved():
    document = Document(
        text="# Interns", metadata={"file_name": "interns.md", "source_type": "wiki"}
    )
    assert normalize_knowledge_metadata(document)["source_type"] == "wiki"


def test_normalizes_path_and_aliases_and_rejects_invalid_entity():
    document = Document(
        text="body",
        metadata={
            "file_name": "notes.md",
            "virtual_path": "/Teams//./../Platform/Notes",
            "section_path": "Platform",
            "page_number": 8,
            "entity": ["not", "a", "mapping"],
        },
    )
    metadata = normalize_knowledge_metadata(document)
    assert metadata["virtual_path"] == "/Platform/Notes"
    assert metadata["section_path"] == ["Platform"]
    assert metadata["page"] == 8
    assert metadata["entity"] == {}


def test_source_relationship_provides_document_and_parent_ids():
    from llama_index.core.schema import NodeRelationship, RelatedNodeInfo

    document = Document(
        text="body",
        metadata={"file_name": "notes.md"},
        relationships={
            NodeRelationship.SOURCE: RelatedNodeInfo(node_id="source-9")
        },
    )
    metadata = normalize_knowledge_metadata(document)
    assert metadata["document_id"] == "source-9"
    assert metadata["parent_id"] == "source-9"
    assert metadata["chunk_id"] == document.doc_id
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_metadata.py -q`
Expected: collection fails because `kotaemon.indices.knowledge` does not exist.

- [ ] **Step 3: Implement the metadata types and normalizers**

In `schema.py`, define the eight-value source-type Literal and immutable supported-type tuple. In `metadata.py`, use slash-segment normalization without filesystem calls; map extensions exactly as specified in the design; prefer explicit supported source_type, then infer; normalize entity to a dict; resolve document_id from explicit metadata, file_id, then source relationship/document id; resolve parent_id from explicit metadata, SOURCE relationship, then input document id; derive chunk_id from Document.doc_id; resolve page from page, page_label, page_number; preserve source and all original keys.

```python
from pathlib import PurePosixPath
from typing import Any, Mapping

from llama_index.core.schema import NodeRelationship

from kotaemon.base import Document
from .schema import SUPPORTED_SOURCE_TYPES

EXTENSION_SOURCE_TYPES = {
    ".md": "markdown", ".markdown": "markdown", ".pdf": "pdf",
    ".faq": "faq", ".ppt": "ppt", ".pptx": "ppt",
    ".xls": "excel", ".xlsx": "excel", ".csv": "excel",
    ".py": "code", ".js": "code", ".jsx": "code", ".ts": "code",
    ".tsx": "code", ".java": "code", ".go": "code", ".rs": "code",
    ".c": "code", ".h": "code", ".cpp": "code", ".hpp": "code",
}


def infer_source_type(metadata: Mapping[str, Any], document_name=None) -> str:
    explicit = metadata.get("source_type")
    if explicit is not None:
        return explicit if explicit in SUPPORTED_SOURCE_TYPES else "other"
    name = document_name or metadata.get("file_name") or metadata.get("file_path", "")
    suffix = PurePosixPath(str(name).replace("\\", "/")).suffix.lower()
    return EXTENSION_SOURCE_TYPES.get(suffix, "other")


def normalize_virtual_path(value, document_name: str) -> str:
    raw = value if isinstance(value, str) and value.strip() else f"/{document_name}"
    parts = []
    for part in raw.strip().replace("\\", "/").split("/"):
        if part in {"", "."}:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/" + "/".join(parts) if parts else "/document"


def normalize_knowledge_metadata(
    document: Document, overrides: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    metadata = dict(document.metadata or {})
    metadata.update(dict(overrides or {}))
    raw_name = metadata.get("document_name") or metadata.get("file_name")
    if not raw_name:
        raw_name = metadata.get("file_path") or "document"
    document_name = PurePosixPath(str(raw_name).replace("\\", "/")).name or "document"
    relationship = (document.relationships or {}).get(NodeRelationship.SOURCE)
    source_id = getattr(relationship, "node_id", None)
    section_path = metadata.get("section_path") or []
    if isinstance(section_path, str):
        section_path = [section_path]
    elif isinstance(section_path, (list, tuple)):
        section_path = [str(part) for part in section_path]
    else:
        section_path = []
    entity = metadata.get("entity")
    return {
        **metadata,
        "source_type": infer_source_type(metadata, document_name),
        "virtual_path": normalize_virtual_path(metadata.get("virtual_path"), document_name),
        "document_id": metadata.get("document_id") or metadata.get("file_id") or source_id or document.doc_id,
        "document_name": document_name,
        "section_path": list(section_path),
        "parent_id": metadata.get("parent_id") or source_id or document.doc_id,
        "chunk_id": document.doc_id,
        "entity": dict(entity) if isinstance(entity, dict) else {},
        "page": metadata.get("page", metadata.get("page_label", metadata.get("page_number"))),
        "source": metadata.get("source", document.source),
    }
```

- [ ] **Step 4: Run the focused metadata tests**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_metadata.py -q`. Expected: PASS for extension inference, caller overrides, fallback path, path traversal removal, page aliases, entity fallback, parent/document identifiers, and metadata preservation.

- [ ] **Step 5: Commit the metadata unit**

```bash
git add libs/kotaemon/kotaemon/indices/knowledge libs/kotaemon/tests/test_knowledge_metadata.py
git commit -m "feat: add canonical knowledge metadata"
```

### Task 2: Markdown and FAQ Chunk Strategies

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/__init__.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/base.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/registry.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/token.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/markdown.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/faq.py`
- Test: `libs/kotaemon/tests/test_knowledge_chunking.py`

**Interfaces:**
- Consumes: canonical source_type metadata, `Document`, and a configured existing `BaseSplitter` fallback.
- Produces: `ChunkStrategy.split(document) -> list[Document]`, `register_chunk_strategy(source_types, factory)`, and `get_chunk_strategy(source_type, token_splitter) -> ChunkStrategy`.
- wiki and markdown resolve to the same heading strategy; unknown source types resolve to TokenChunkStrategy.

- [ ] **Step 1: Write failing tests for headings, overlong sections, FAQ pairs, and fallback**

```python
from kotaemon.base import Document
from kotaemon.indices.knowledge.chunking import get_chunk_strategy
from kotaemon.indices.splitters import TokenSplitter


def test_markdown_chunks_keep_heading_paths():
    document = Document(
        text="# Interns\n\nintro\n\n## Zhang San\n\nBuilt a RAG API.",
        metadata={"source_type": "markdown", "file_name": "interns.md"},
    )

    chunks = get_chunk_strategy("markdown", TokenSplitter(chunk_size=100)).split(document)

    assert [chunk.metadata["section_path"] for chunk in chunks] == [
        ["Interns"], ["Interns", "Zhang San"]
    ]


def test_faq_keeps_each_question_and_answer_as_a_separate_unit():
    document = Document(
        text="Q: What is RAG?\nA: Retrieval plus generation.\n\n"
        "Question: Who owns the API?\nAnswer: Zhang San.",
        metadata={"source_type": "faq"},
    )

    chunks = get_chunk_strategy("faq", TokenSplitter(chunk_size=100)).split(document)

    assert len(chunks) == 2
    assert "What is RAG?" in chunks[0].text
    assert "Zhang San" in chunks[1].text


def test_markdown_keeps_nested_heading_path_and_falls_back_without_headings():
    nested = Document(
        text="# Handbook\n\n## API\n\n### Ownership\n\nZhang San",
        metadata={"source_type": "markdown"},
    )
    nested_chunks = get_chunk_strategy(
        "markdown", TokenSplitter(chunk_size=100)
    ).split(nested)
    assert nested_chunks[-1].metadata["section_path"] == [
        "Handbook", "API", "Ownership"
    ]

    plain = Document(text="plain text", metadata={"source_type": "markdown"})
    plain_chunks = get_chunk_strategy(
        "markdown", TokenSplitter(chunk_size=100)
    ).split(plain)
    assert [chunk.text for chunk in plain_chunks] == ["plain text"]


def test_oversized_markdown_section_keeps_its_path():
    document = Document(
        text="# Operations\n\n" + "detail " * 80,
        metadata={"source_type": "markdown"},
    )
    chunks = get_chunk_strategy(
        "markdown", TokenSplitter(chunk_size=8, chunk_overlap=0)
    ).split(document)
    assert len(chunks) > 1
    assert all(chunk.metadata["section_path"] == ["Operations"] for chunk in chunks)


def test_faq_metadata_and_multiline_answers_form_one_pair():
    explicit = Document(
        text="",
        metadata={"source_type": "faq", "question": "Owner?", "answer": "Zhang San"},
    )
    explicit_chunks = get_chunk_strategy(
        "faq", TokenSplitter(chunk_size=100)
    ).split(explicit)
    assert len(explicit_chunks) == 1
    assert "Owner?" in explicit_chunks[0].text
    assert "Zhang San" in explicit_chunks[0].text

    multiline = Document(
        text="Q: How?\nA: First line\nsecond line",
        metadata={"source_type": "faq"},
    )
    multiline_chunks = get_chunk_strategy(
        "faq", TokenSplitter(chunk_size=100)
    ).split(multiline)
    assert len(multiline_chunks) == 1
    assert "second line" in multiline_chunks[0].text


def test_incomplete_faq_pair_falls_back_without_merging_records():
    document = Document(
        text="Q: Who owns the API?\nA:", metadata={"source_type": "faq"}
    )
    chunks = get_chunk_strategy("faq", TokenSplitter(chunk_size=100)).split(document)
    assert len(chunks) == 1
    assert chunks[0].text == document.text


def test_unknown_source_type_uses_token_splitter():
    document = Document(text="plain fallback", metadata={"source_type": "other"})
    chunks = get_chunk_strategy("other", TokenSplitter(chunk_size=100)).split(document)
    assert [chunk.text for chunk in chunks] == ["plain fallback"]


def test_wiki_uses_markdown_heading_strategy_without_changing_source_type():
    document = Document(
        text="# Handbook\n\n## API\n\nEndpoint details",
        metadata={"source_type": "wiki"},
    )
    chunks = get_chunk_strategy("wiki", TokenSplitter(chunk_size=100)).split(document)
    assert chunks[-1].metadata["section_path"] == ["Handbook", "API"]
    assert chunks[-1].metadata["source_type"] == "wiki"
```

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py -q`
Expected: collection fails because the registry and strategy modules do not exist.

- [ ] **Step 3: Implement the strategy interface, fallback, registry, Markdown, and FAQ strategies**

The Markdown parser treats each heading and its following content as a section, maintains a heading stack by heading level, and falls back when there are no headings. The FAQ parser accepts explicit question/answer metadata or line markers Q:/Question: and A:/Answer:. Each complete pair becomes one Document. Any incomplete pair makes the whole input use TokenChunkStrategy. When a natural section or FAQ unit exceeds the configured limit, run the existing TokenSplitter on that unit and retain the semantic parent id and section_path.

```python
class ChunkStrategy(Protocol):
    def split(self, document: Document) -> list[Document]:
        raise NotImplementedError


def get_chunk_strategy(source_type: str, token_splitter: BaseSplitter) -> ChunkStrategy:
    factory = _STRATEGIES.get(source_type, TokenChunkStrategy)
    return factory(token_splitter=token_splitter)
```

- [ ] **Step 4: Run the focused chunking tests**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py -q`. Expected: PASS for nested heading levels, heading-less fallback, oversized sections, explicit FAQ metadata, multiline answers, and incomplete-pair fallback.

- [ ] **Step 5: Commit the strategy unit**

```bash
git add libs/kotaemon/kotaemon/indices/knowledge/chunking libs/kotaemon/tests/test_knowledge_chunking.py
git commit -m "feat: add markdown and faq chunk strategies"
```

### Task 3: Python, PDF, PPT, and Excel Strategies

**Files:**
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/code.py`
- Create: `libs/kotaemon/kotaemon/indices/knowledge/chunking/structured.py`
- Modify: `libs/kotaemon/kotaemon/loaders/excel_loader.py`
- Create: `libs/kotaemon/kotaemon/loaders/pptx_loader.py`
- Test: `libs/kotaemon/tests/test_knowledge_chunking.py`
- Test: `libs/kotaemon/tests/test_structured_readers.py`

**Interfaces:**
- Consumes: Documents from existing readers and parser metadata.
- Produces: Python AST chunks; PDF passthrough/secondary split strategy; one row per Excel Document; one grouped Document per parser-reported slide.
- Parser failures use the configured TokenSplitter. No new required package is added.

- [ ] **Step 1: Write failing tests for Python symbols and parse fallback**

```python
def test_python_ast_emits_class_method_and_function_units():
    document = Document(
        text=(
            "class Coupon:\n    def apply(self):\n        return True\n\n"
            "def calculate():\n    return 1\n"
        ),
        metadata={"source_type": "code", "file_name": "coupon.py"},
    )

    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)

    assert {chunk.metadata.get("class_name") for chunk in chunks} >= {"Coupon"}
    assert {chunk.metadata.get("function_name") for chunk in chunks} >= {
        "apply", "calculate"
    }


def test_python_method_points_to_its_class_unit():
    document = Document(
        text='class Coupon:\n    """Coupon rules."""\n\n    def apply(self):\n        return True',
        metadata={"source_type": "code", "file_name": "coupon.py"},
    )
    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)
    class_chunk = next(chunk for chunk in chunks if chunk.metadata.get("class_name"))
    method_chunk = next(
        chunk for chunk in chunks if chunk.metadata.get("function_name") == "apply"
    )
    assert "Coupon rules." in class_chunk.text
    assert method_chunk.metadata["parent_id"] == class_chunk.doc_id
    assert method_chunk.metadata["language"] == "python"


def test_python_parse_failure_and_oversized_symbol_use_token_fallback():
    malformed = Document(
        text="def broken(:\n    pass", metadata={"source_type": "code"}
    )
    malformed_chunks = get_chunk_strategy(
        "code", TokenSplitter(chunk_size=100)
    ).split(malformed)
    assert [chunk.text for chunk in malformed_chunks] == [malformed.text]

    oversized = Document(
        text="def calculate():\n" + "    value = 1\n" * 100,
        metadata={"source_type": "code", "file_name": "long.py"},
    )
    oversized_chunks = get_chunk_strategy(
        "code", TokenSplitter(chunk_size=12, chunk_overlap=0)
    ).split(oversized)
    assert len(oversized_chunks) > 1
    assert all(
        chunk.metadata["function_name"] == "calculate" for chunk in oversized_chunks
    )

    other_language = Document(
        text="function calculate() { return 1; }",
        metadata={"source_type": "code", "file_name": "calculate.ts"},
    )
    typescript_chunks = get_chunk_strategy(
        "code", TokenSplitter(chunk_size=100)
    ).split(other_language)
    assert [chunk.text for chunk in typescript_chunks] == [other_language.text]


def test_pdf_strategy_preserves_section_and_falls_back_without_one():
    structured = Document(
        text="Calibration procedure",
        metadata={"source_type": "pdf", "section_path": ["Setup"], "page_label": 4},
    )
    structured_chunks = get_chunk_strategy(
        "pdf", TokenSplitter(chunk_size=100)
    ).split(structured)
    assert structured_chunks[0].metadata["section_path"] == ["Setup"]
    assert structured_chunks[0].metadata["page_label"] == 4

    flat = Document(text="flat PDF text", metadata={"source_type": "pdf"})
    flat_chunks = get_chunk_strategy(
        "pdf", TokenSplitter(chunk_size=100)
    ).split(flat)
    assert [chunk.text for chunk in flat_chunks] == ["flat PDF text"]


# These reader tests are in test_structured_readers.py.
from kotaemon.loaders.excel_loader import ExcelRowReader
from kotaemon.loaders.pptx_loader import group_slide_documents


def test_excel_rows_preserve_header_values_and_source_rows(tmp_path):
    import pandas as pd

    file_path = tmp_path / "weekly.xlsx"
    pd.DataFrame(
        [{"person": "Zhang San", "work": "RAG"}, {"person": "Li Si", "work": "UI"}]
    ).to_excel(file_path, index=False, sheet_name="Week 1")
    documents = ExcelRowReader().load_data(file_path)
    assert len(documents) == 2
    assert documents[0].metadata["sheet_name"] == "Week 1"
    assert documents[0].metadata["row_number"] == 2
    assert "person: Zhang San" in documents[0].text
    assert "work: RAG" in documents[0].text


def test_excel_reader_delegates_parse_errors_to_its_legacy_reader(
    tmp_path, monkeypatch
):
    import pandas as pd

    class FallbackReader:
        def load_data(self, file, extra_info=None, **kwargs):
            return [Document(text="legacy parse", metadata=extra_info or {})]

    file_path = tmp_path / "broken.xlsx"
    file_path.write_text("not an xlsx", encoding="utf-8")
    def raise_parse_error(*args, **kwargs):
        raise ValueError("invalid spreadsheet")

    monkeypatch.setattr(pd, "read_excel", raise_parse_error)
    documents = ExcelRowReader(fallback_reader=FallbackReader()).load_data(file_path)
    assert [document.text for document in documents] == ["legacy parse"]


def test_pptx_grouping_uses_slide_boundaries_and_flattens_missing_boundaries():
    documents = [
        Document(text="title", metadata={"page_number": 1}),
        Document(text="body", metadata={"page_number": 1}),
        Document(text="next slide", metadata={"page_number": 2}),
    ]
    slides = group_slide_documents(documents)
    assert len(slides) == 2
    assert slides[0].metadata["slide_number"] == 1
    assert "title" in slides[0].text and "body" in slides[0].text

    flat = group_slide_documents([Document(text="one"), Document(text="two")])
    assert len(flat) == 1
    assert "one" in flat[0].text and "two" in flat[0].text
```

The `test_knowledge_chunking.py` imports from Task 2 remain at the top of that file. `test_structured_readers.py` also imports `Document` and `pytest`; `tmp_path` and `monkeypatch` are supplied by pytest.

- [ ] **Step 2: Run the focused tests and confirm they fail**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py -q`
Expected: the existing markdown/FAQ tests pass, while the code strategy and new reader imports fail because those implementations are not registered yet.

- [ ] **Step 3: Implement AST units, structured fallback, Excel rows, and PPT slides**

Python units include the class declaration/docstring, each top-level function, and each method. Method chunks keep class_name, function_name, language="python", and parent_id equal to the class unit id. Use `ast.get_source_segment`; catch SyntaxError and fall back. PDF strategy trusts section_path/heading metadata only. ExcelRowReader uses the existing pandas dependency, reads CSV with `read_csv` and spreadsheets with `read_excel`, treats the first row as headers, and emits one Document per non-empty data row with sheet_name, one-based row_number, and label/value text. On parse failure, delegate to the existing reader for that extension (`PandasExcelReader` for the current `.xlsx` default); `.csv` falls back to `TxtReader`. PptxReader requests `split_documents=True` from UnstructuredReader, groups elements by slide_number or page_number, and emits a flat fallback Document if no slide boundary is present.

```python
class PythonCodeChunkStrategy(ChunkStrategy):
    def split(self, document: Document) -> list[Document]:
        try:
            tree = ast.parse(document.text or "")
        except SyntaxError:
            return self.fallback.split(document)
        return self._symbols(document, tree)
```

- [ ] **Step 4: Run format-specific tests**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py -q`. Expected: PASS for valid and invalid Python, method-to-class parent links, oversized AST units, PDF metadata/fallback, Excel rows, and PPT slide grouping/fallback.

- [ ] **Step 5: Commit the format strategy unit**

```bash
git add libs/kotaemon/kotaemon/indices/knowledge/chunking libs/kotaemon/kotaemon/loaders/excel_loader.py libs/kotaemon/kotaemon/loaders/pptx_loader.py libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py
git commit -m "feat: add code and structured document chunking"
```

### Task 4: Integrate Metadata and Chunking into the Existing File Index

**Files:**
- Modify: `libs/kotaemon/kotaemon/indices/ingests/files.py`
- Modify: `libs/kotaemon/kotaemon/indices/vectorindex.py`
- Modify: `libs/ktem/ktem/index/file/pipelines.py`
- Test: `libs/ktem/ktem_tests/test_knowledge_indexing.py`

**Interfaces:**
- Consumes: `knowledge_metadata` for a single file and `knowledge_metadata_by_path` for batch indexing.
- Produces: normalized metadata on text/table/image chunks before docstore and vectorstore writes; file-level `Source.note["knowledge"]` summary; unchanged default upload call behavior.

- [ ] **Step 1: Write failing integration tests**

```python
from kotaemon.base import Document


def consume_stream(stream):
    while True:
        try:
            next(stream)
        except StopIteration:
            return


def test_stream_persists_caller_knowledge_metadata(index_pipeline_fixture, tmp_path):
    pipeline, reader, docstore, vectorstore, source_id, get_source = index_pipeline_fixture
    input_path = tmp_path / "Zhang San.md"
    input_path.write_text("fixture", encoding="utf-8")

    consume_stream(
        pipeline.stream(
            input_path,
            reindex=False,
            knowledge_metadata={"virtual_path": "/Interns/App/Zhang San"},
        )
    )

    assert reader.last_extra_info["file_id"] == source_id
    assert reader.last_extra_info["virtual_path"] == "/Interns/App/Zhang San"
    stored = docstore.get_all()
    assert stored
    assert all(
        item.metadata["virtual_path"] == "/Interns/App/Zhang San" for item in stored
    )
    assert all(item.metadata["file_id"] == source_id for item in stored)
    assert all(
        vectorstore.metadata_by_id[item.doc_id]["virtual_path"]
        == "/Interns/App/Zhang San"
        for item in stored
    )
    source = get_source()
    assert source.note["tokens"] > 0
    assert source.note["loader"] == "FixtureReader"
    assert source.note["preserve"] == "existing"
    assert source.note["knowledge"]["source_type"] == "markdown"
    assert source.note["knowledge"]["virtual_path"] == "/Interns/App/Zhang San"
    assert source.note["knowledge"]["document_name"] == "Zhang San.md"
    assert source.note["knowledge"]["entity"] == {}


def test_stream_without_knowledge_metadata_keeps_legacy_fallback(
    index_pipeline_fixture, tmp_path
):
    pipeline, _, docstore, _, _, _ = index_pipeline_fixture
    input_path = tmp_path / "legacy.txt"
    input_path.write_text("legacy fixture", encoding="utf-8")
    consume_stream(pipeline.stream(input_path, reindex=False))
    stored = docstore.get_all()
    assert stored
    assert all(item.metadata["virtual_path"] == "/legacy.txt" for item in stored)


def test_handle_docs_normalizes_all_stored_artifact_types(index_pipeline_fixture):
    pipeline, _, docstore, vectorstore, source_id, _ = index_pipeline_fixture
    documents = [
        Document(
            text="markdown body",
            metadata={
                "file_name": "artifacts.md",
                "file_id": source_id,
                "type": "text",
            },
        ),
        Document(
            text="table values",
            metadata={"file_name": "artifacts.md", "file_id": source_id, "type": "table"},
        ),
        Document(
            text="image description",
            metadata={"file_name": "artifacts.md", "file_id": source_id, "type": "image"},
        ),
        Document(
            text="thumbnail",
            metadata={
                "file_name": "artifacts.md",
                "file_id": source_id,
                "type": "thumbnail",
                "page_label": 1,
            },
        ),
    ]
    consume_stream(pipeline.handle_docs(documents, source_id, "artifacts.md"))
    stored = docstore.get_all()
    assert {item.metadata["type"] for item in stored} >= {
        "text", "table", "image", "thumbnail"
    }
    assert all(item.metadata["source_type"] == "markdown" for item in stored)
    assert all(item.metadata["chunk_id"] == item.doc_id for item in stored)
    assert all(item.doc_id in vectorstore.metadata_by_id for item in stored)


def test_batch_stream_uses_metadata_keyed_by_original_input_path(
    index_document_pipeline_fixture, tmp_path
):
    input_path = tmp_path / "Zhang San.md"
    input_path.write_text("fixture", encoding="utf-8")
    indexer, routed_pipeline = index_document_pipeline_fixture
    consume_stream(
        indexer.stream(
            [str(input_path)],
            knowledge_metadata_by_path={
                str(input_path): {"virtual_path": "/Interns/App/Zhang San"}
            },
        )
    )
    assert routed_pipeline.received_knowledge_metadata == {
        "virtual_path": "/Interns/App/Zhang San"
    }
```

Implement `index_pipeline_fixture` with a temporary SQLite database and mapped Source/Index fixtures, a `FixtureReader` that returns one Markdown Document and records `extra_info`, an `InMemoryDocumentStore`, an `InMemoryVectorStore` subclass that captures metadata passed to `add` as `metadata_by_id`, and a deterministic `BaseEmbeddings` test double. Override `get_id_if_exists` to return `None` and `store_file` to return a seeded Source id, avoiding user-index file storage. Seed Source.note with `{"tokens": 42, "preserve": "existing"}` and provide `get_source()` that reloads the row after indexing. `consume_stream` exhausts the generator and ignores its return value. Implement `index_document_pipeline_fixture` with a routed fake pipeline that records the metadata argument and returns a successful stream result. These fixtures must exercise the public single-file and batch stream entry points.

- [ ] **Step 2: Run the integration tests and confirm they fail**

Run: `uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py -q`
Expected: the current pipeline has no knowledge_metadata argument, registry selection, or Source.note knowledge summary.

- [ ] **Step 3: Wire the strategy registry through the existing pipeline**

Keep `IndexPipeline` and its docstore/vectorstore lifecycle. In `IndexPipeline.stream`, add an optional `knowledge_metadata` argument, merge it over generated reader metadata before calling `load_data`, and pass it to `finish` as an optional argument. In `handle_docs`, route each text Document by normalized source_type, use the configured TokenSplitter as the fallback, and normalize metadata on every resulting text, table, and image record before storage. Update `VectorIndexing.add_to_vectorstore` to pass each Document.metadata through BaseVectorStore.add's existing `metadatas` parameter; the current implementation stores embeddings and ids only, so otherwise later metadata filters cannot see canonical values. In `IndexDocumentPipeline.stream`, preserve each original input path before converting it to `Path`, consume `knowledge_metadata_by_path` once, and pass the exact matching mapping to that file's pipeline. Add default readers for .faq and Python/code text extensions (`TxtReader`), .xls/.xlsx/.csv (`ExcelRowReader`), and .ppt/.pptx (`PptxReader`); merge developer reader overrides last. In `finish`, normalize inferred or caller-provided source_type, virtual_path, document_name, and entity, then merge them into Source.note["knowledge"] without replacing token counts, loader name, or other note fields. The per-file virtual path fallback is slash-rooted document_name and must never use the upload's absolute path.
Keep `IndexPipeline` and its docstore/vectorstore lifecycle. Normalize each text Document before selecting its strategy; split with the source-type strategy and existing TokenSplitter fallback; then normalize each output chunk again so chunk_id reflects that chunk and strategy-specific parent/section metadata survives. Normalize non-text and thumbnail records before writing them. If the pipeline has no splitter, keep the existing unsplit behavior and still normalize metadata. Update `VectorIndexing.add_to_vectorstore` to pass each Document.metadata through BaseVectorStore.add's existing `metadatas` parameter; the current implementation stores embeddings and ids only, so otherwise later metadata filters cannot see canonical values. In `IndexPipeline.stream`, add an optional `knowledge_metadata` argument, merge it over generated reader metadata before calling `load_data`, and pass it to `finish` as an optional argument. In `IndexDocumentPipeline.stream`, preserve each original input path before converting it to `Path`, consume `knowledge_metadata_by_path` once, and pass the exact matching mapping to that file's pipeline. Add default readers for .faq and Python/code text extensions (`TxtReader`), .xls/.xlsx/.csv (`ExcelRowReader`), and .ppt/.pptx (`PptxReader`); merge developer reader overrides last. In `finish`, normalize inferred or caller-provided source_type, virtual_path, document_name, and entity, then merge those four fields into Source.note["knowledge"] without replacing token counts, loader name, or other note fields. The per-file virtual path fallback is slash-rooted document_name and must never use the upload's absolute path.

After the existing file-id and file-name resolution in `IndexPipeline.stream`, use this flow:

```python
def _split_and_normalize_text_docs(self, documents):
    output = []
    for document in documents:
        document.metadata = normalize_knowledge_metadata(document)
        if self.splitter:
            strategy = get_chunk_strategy(
                document.metadata["source_type"], self.splitter
            )
            chunks = strategy.split(document)
        else:
            chunks = [document]
        for chunk in chunks:
            chunk.metadata = normalize_knowledge_metadata(chunk)
            output.append(chunk)
    return output


def handle_docs(self, docs, file_id, file_name):
    text_docs = [doc for doc in docs if doc.metadata.get("type", "text") == "text"]
    non_text_docs = [doc for doc in docs if doc.metadata.get("type", "text") not in {"text", "thumbnail"}]
    thumbnail_docs = [doc for doc in docs if doc.metadata.get("type") == "thumbnail"]
    all_chunks = self._split_and_normalize_text_docs(text_docs)
    for document in non_text_docs + thumbnail_docs:
        document.metadata = normalize_knowledge_metadata(document)
    # Keep the existing thumbnail linking, batching, docstore, and vectorstore blocks.


def add_to_vectorstore(self, docs: list[Document]):
    if self.vector_store:
        embeddings = self.embedding(docs)
        self.vector_store.add(
            embeddings=embeddings,
            metadatas=[doc.metadata or {} for doc in docs],
            ids=[doc.doc_id for doc in docs],
    )


def finish(self, file_id, file_path, knowledge_metadata=None):
    # Keep the existing token-count and loader-note updates before this merge.
    file_name = file_path.name if isinstance(file_path, Path) else str(file_path)
    summary_document = Document(
        text="",
        metadata={
            "file_id": file_id,
            "file_name": file_name,
            **(knowledge_metadata or {}),
        },
    )
    normalized = normalize_knowledge_metadata(summary_document)
    summary = {
        key: normalized[key]
        for key in ("source_type", "virtual_path", "document_name", "entity")
    }
    note = dict(item.note or {})
    knowledge = dict(note.get("knowledge") or {})
    knowledge.update(summary)
    note["knowledge"] = knowledge
    item.note = note


# Inside IndexDocumentPipeline.stream:
def stream(self, file_paths, **kwargs):
    metadata_by_path = kwargs.pop("knowledge_metadata_by_path", {})
    for original_path in file_paths:
        knowledge_metadata = metadata_by_path.get(original_path)
        if knowledge_metadata is None:
            knowledge_metadata = metadata_by_path.get(str(original_path))
        pipeline = self.route(original_path)
        yield from pipeline.stream(
            original_path,
            knowledge_metadata=knowledge_metadata,
            **kwargs,
        )


# Inside IndexPipeline.stream, reject caller attempts to override Source identity
# before file-id lookup, Source writes, loading, or indexing:
def stream(self, file_path, reindex=False, knowledge_metadata=None, **kwargs):
    reserved = {"file_id", "document_id", "collection_name"} & set(
        knowledge_metadata or {}
    )
    if reserved:
        raise ValueError(
            "knowledge_metadata cannot override indexing-owned identity fields: "
            + ", ".join(sorted(reserved))
        )

# The existing path resolution, file-id lookup, and Source writes follow this guard.
# After that resolution, merge the ordinary metadata into the reader input:
if isinstance(file_path, Path):
        extra_info = default_file_metadata_func(str(file_path))
        file_name = file_path.name
    else:
        extra_info = {"file_name": file_path}
        file_name = file_path
    extra_info["file_id"] = file_id
    extra_info["collection_name"] = self.collection_name
    extra_info.update(knowledge_metadata or {})
    docs = self.loader.load_data(file_path, extra_info=extra_info)
    yield from self.handle_docs(docs, file_id, file_name)
    self.finish(file_id, file_path, knowledge_metadata=knowledge_metadata)
```

In `KH_DEFAULT_FILE_EXTRACTORS`, register `TxtReader` for `.faq` plus `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.java`, `.go`, `.rs`, `.c`, `.h`, `.cpp`, and `.hpp`; register `ExcelRowReader` for `.xls`, `.xlsx`, and `.csv` with the previous extension reader as fallback (`TxtReader` for `.csv`); register `PptxReader` for `.ppt` and `.pptx`. Keep `IndexDocumentPipeline.readers` applying `dev_readers` after these defaults so developer overrides retain precedence.

- [ ] **Step 4: Run integration tests and existing regression tests**

Run: `uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py libs/kotaemon/tests/test_splitter.py libs/kotaemon/tests/test_indexing_retrieval.py -q`. Expected: PASS; old callers keep the prior fallback, and metadata survives docstore/vectorstore writes.

- [ ] **Step 5: Commit the indexing integration**

```bash
git add libs/kotaemon/kotaemon/indices/ingests/files.py libs/kotaemon/kotaemon/indices/vectorindex.py libs/ktem/ktem/index/file/pipelines.py libs/ktem/ktem_tests/test_knowledge_indexing.py
git commit -m "feat: integrate knowledge chunking with file indexing"
```

### Task 5: Compatibility and Validation

**Files:**
- Modify: `docs/superpowers/specs/2026-10-02-agent-knowledge-structure-design.md` only if implementation decisions changed during work.
- Test: all new tests from Tasks 1–4.

- [ ] **Step 1: Run all focused knowledge tests**

Run: `uv run pytest libs/kotaemon/tests/test_knowledge_metadata.py libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py libs/ktem/ktem_tests/test_knowledge_indexing.py -q`. Expected: PASS.

- [ ] **Step 2: Run existing ingestion and retrieval regressions**

Run: `uv run pytest libs/kotaemon/tests/test_ingestor.py libs/kotaemon/tests/test_splitter.py libs/kotaemon/tests/test_indexing_retrieval.py -q`. Expected: PASS.

- [ ] **Step 3: Review final scope and status**

Run: `git diff --check` and `git status --short`. Expected: no whitespace errors; only planned implementation files and test files are changed.

- [ ] **Step 4: Report the first workstream outcome**

Summarize changed files, metadata contract, supported chunkers, old-data behavior, tests run, and remaining workstreams. Do not claim real corpus evaluation; the agreed fixture scope validates mechanics only.
