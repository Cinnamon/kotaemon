# Task 3 implementation report

Status: DONE

Implementation commit: `4d47c9ff187a3d0eceb2820f6a477702c68fc63e` — `feat: add code and structured document chunking`

Base: `4c6fc71f416a7dbc98e3a724fe29a9e70e339ef7`

## Changed files

- `libs/kotaemon/kotaemon/indices/knowledge/chunking/code.py`: Python AST class declarations/docstrings/data, functions and methods; decorator/async preservation; methods link to an emitted class chunk; module statements remain retrievable. Malformed, unsupported-language and symbol-free inputs use the supplied token fallback.
- `chunking/structured.py`: existing PDF section_path or heading metadata, parser slide boundaries, and spreadsheet row boundaries form semantic units, with token subdivision for oversized units. Missing boundaries use fallback.
- `chunking/registry.py`: register code, PDF, PPT and Excel strategies.
- `libs/kotaemon/kotaemon/loaders/excel_loader.py`: add ExcelRowReader using installed pandas/openpyxl; emit labeled non-empty rows for all worksheets or CSV; preserve original physical row numbering across empty rows and configured skiprows; retain file and sheet provenance. Parse errors delegate to the injected legacy reader, PandasExcelReader, or CSV TxtReader.
- `libs/kotaemon/kotaemon/loaders/pptx_loader.py`: existing UnstructuredReader requested with split_documents=True; group all elements by reported slide_number/page_number; retain presentation, slide title and citation page label. Missing or partial boundaries produce one flat document with all text for downstream token fallback.
- `libs/kotaemon/tests/test_knowledge_chunking.py`: Python symbols, source IDs/exclusions, class-parent links, decorators/async functions, module statements, parse/language/symbol-free fallback, oversized symbols, inline classes, PDF heading/page metadata, PPT/Excel boundaries.
- `libs/kotaemon/tests/test_structured_readers.py`: multiple sheets, empty rows and physical provenance, CSV parsing/fallback, legacy spreadsheet fallback, skiprows, PPT grouping/flat fallback and reader delegation.

## RED/GREEN evidence

The tests were written before implementation. Initial command:

`uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py -q`

RED: collection failed because ExcelRowReader did not exist. Initial implementation GREEN: **27 passed**.

Self-review identified missing inline class declaration and skiprows provenance coverage. Added both tests before fixes and ran the same command: **2 failed, 27 passed**. The failures showed `class Coupon: pass` became only `pass`, and skiprows returned row numbers `[2, 3]` instead of physical `[3, 5]`.

Fixed AST header extraction using UTF-8 byte positions and mapped pandas row positions through configured skipped rows. Final focused GREEN after formatting and style edits: **29 passed in 5.26s**.

Black completed. Focused Flake8 passed with the repository's max-line-length=88 and E203 exclusion. Working and staged `git diff --check` passed.

## Self-review

- Only Task 3 files changed; no Task 4 ingestion wiring, schema changes, unrelated retriever changes or dependencies.
- Existing Document source/channel and metadata exclusion lists survive semantic units and fallback. Canonical document/chunk IDs and loader provenance remain available.
- Python class units avoid duplicating method bodies; each method references an actual emitted class chunk ID. Multiple token fragments of a function retain its symbol metadata and shared semantic parent.
- PDF structure is accepted only from existing reader metadata; no heading inference or PDF parser replacement.
- PPT grouping uses every element, and missing boundaries trigger a flat document rather than dropping unassigned elements or guessing slides. Parser failures remain the existing reader's responsibility; no unreadable presentation is silently treated as empty.
- No virtual_path filesystem reads or absolute-path default namespaces were introduced.

## Concerns / limits

No blocking concerns. The implementation remains conservative: Python is the supported AST language, PDF consumes reader-provided headings, and PPT requires reliable parser boundaries. Advanced CSV configurations that suppress rows implicitly (for example comment filtering or skip_blank_lines=True) can alter physical row accounting; default CSV behavior preserves blank rows, and explicit skiprows is supported. Actual PPT parser execution was not exercised; the focused reader fixture validates parser delegation and grouping with its documented page_number metadata. Default reader integration belongs to Task 4.

## Independent-review fixes

Follow-up implementation commit: `29da3649bc3485747f558f72f86ca39b7f55d53d` — `fix: preserve selected sheets and code comments`.

Review identified two Important issues: numeric worksheet selection recorded the index rather than the real workbook tab name, and parse fallback omitted the selected worksheet. It also identified a Minor code-content loss: AST extraction omitted comments outside node spans.

Added regression tests before fixes for a numeric single worksheet and a numeric worksheet list, selected-sheet fallback with include_sheetname and source metadata, and comments before a class, between class members, and after a symbol. Focused RED: **4 failed, 29 passed in 4.12s**. The numeric cases returned `["0"]` / `["0", "1"]`; fallback received include_sheetname but no sheet_name; leading code comments were absent from every chunk.

The smallest fixes resolve numeric selectors through pandas ExcelFile.sheet_names, forward the original sheet_name and existing reader options on spreadsheet fallback, and preserve otherwise omitted COMMENT tokens in the module knowledge unit using the standard-library tokenizer. No new dependency, schema or Task 4 change.

Focused GREEN after fixes and formatting: `uv run pytest libs/kotaemon/tests/test_knowledge_chunking.py libs/kotaemon/tests/test_structured_readers.py -q` → **33 passed in 4.21s**. Black, focused Flake8 and working/staged diff checks passed. All review findings were addressed.
