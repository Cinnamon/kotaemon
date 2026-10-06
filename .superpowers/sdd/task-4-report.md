# Task 4: Integrate Metadata and Chunking into the Existing File Index — Implementation Report

## Result

Integrated canonical metadata and the source-aware chunk strategy registry into Kotaemon's existing file indexing path. Existing document, vectorstore, SQL index, and citation schemas remain unchanged. New reader defaults, metadata propagation, Source note summaries, and a Chroma-compatible metadata projection are covered by integration regressions.

## TDD evidence

The previous implementer's handoff recorded an initial Chroma RED: default Chroma rejected nested `entity` metadata with flat metadata validation. The Chroma adapter now projects mappings and sequences to JSON strings on copied vector nodes while leaving scalar filter fields such as `virtual_path` intact. Native structured values remain in the docstore.

During this continuation, the direct Chroma projection test exposed a second RED when callers supplied a canonical `document_id` without explicit vector IDs: LlamaIndex replaced the field with `"None"` because no source relationship existed.

**RED command:**

```text
uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py::test_chroma_node_metadata_projection_preserves_input -q
```

**RED output:** one assertion failed: expected Chroma metadata `document_id` to be `"source"`, received `"None"`.

The adapter now sets the source relationship on its private node copy when canonical `document_id` metadata is present and no IDs were supplied. The input document's metadata and relationships remain unchanged.

**GREEN command:**

```text
uv run pytest libs/ktem/ktem_tests/test_knowledge_indexing.py::test_chroma_node_metadata_projection_preserves_input -q
```

**GREEN output:** `1 passed in 5.03s`.

**Focused integration and regression command:**

```text
./.venv/bin/python -m pytest libs/ktem/ktem_tests/test_knowledge_indexing.py libs/kotaemon/tests/test_splitter.py libs/kotaemon/tests/test_indexing_retrieval.py libs/kotaemon/tests/test_vectorstore.py -q
```

**Output:** `31 passed, 7 warnings in 15.67s`; the process exited with code 0. Warnings are existing Pydantic `dict()` deprecation and Milvus/pkg_resources deprecation warnings.

Formatting and whitespace checks also passed:

```text
uv run black --check <five changed Python files>       # 5 files unchanged
uv run isort --profile black --check-only <same files> # exit 0
git diff --check                                       # exit 0
```

## Changed files

- `libs/kotaemon/kotaemon/indices/ingests/files.py`
- `libs/kotaemon/kotaemon/indices/vectorindex.py`
- `libs/kotaemon/kotaemon/storages/vectorstores/chroma.py`
- `libs/ktem/ktem/index/file/pipelines.py`
- `libs/ktem/ktem_tests/test_knowledge_indexing.py`

## Self-review findings

- The existing indexing lifecycle and chunk strategy registry are reused. Text metadata is normalized before strategy selection and again after splitting; table, image, and thumbnail records are normalized before storage. Normalization still runs when no splitter is configured.
- Single-file metadata is merged into reader metadata. Batch metadata is looked up against each original input path before conversion to `Path`, then forwarded to that file's pipeline.
- `Source.note["knowledge"]` receives normalized source type, logical path, document name, and entity while existing note keys are retained. The fallback virtual path is rooted at the document name, not the upload's absolute path.
- Reader defaults cover FAQ and code text, row-oriented Excel/CSV, and slide-aware PPT/PPTX. Developer reader overrides continue to take precedence.
- Vector indexing passes `Document.metadata` through the existing `BaseVectorStore.add(metadatas=...)` interface. The Chroma adapter serializes non-scalar values on private node copies because Chroma accepts scalar metadata values. Scalar fields remain filterable, and tests cover virtual-path filtering, canonical document IDs, and preservation of the input document's metadata and relationships.
- The existing vectorstore regression suite passed, including Chroma deletion by chunk IDs.

## Concerns

Chroma stores list and mapping metadata as JSON strings, so nested values are preserved for retrieval from the docstore but are not directly queryable as native nested Chroma fields. Scalar fields such as `source_type`, `virtual_path`, `file_id`, and `page` remain available to vector filters. This limitation should be considered when the later scoped-retrieval task defines entity filtering.

The complete repository test suite was not run; verification was limited to the focused integration, splitter, indexing/retrieval, and vectorstore suites above.

## Commit

Implementation commit: `1aa85186232b6b5bbe0accc33bfedb4fb47da3f0`. This report is committed separately.
