# Agent-Oriented Knowledge Structure Design

## Scope

This is the design for the first independently testable workstream in the requested Agent-oriented retrieval upgrade: canonical knowledge metadata and structure-aware chunking. The full upgrade is divided into three workstreams so each can be reviewed and validated without creating a parallel RAG stack:

1. Knowledge metadata and structure-aware chunking (this design).
2. Deterministic query scope planning, scoped hybrid retrieval, and the KnowledgeService API.
3. Result diversity, token-budget-aware context assembly, retrieval traces, and offline evaluation.

The first workstream modifies the existing ingestion path. It does not introduce a Wiki connector, a virtual filesystem, a new vector database, or a replacement retrieval pipeline. This repository currently provides a general file index; it does not contain an enterprise Wiki tree or an existing corpus of Wiki paths. An upstream loader or caller must provide a logical virtual_path when a hierarchy is available.

## Repository Findings

- kotaemon.base.Document already inherits LlamaIndex Document and stores arbitrary metadata. RetrievedDocument adds score and retrieval_metadata. A parallel document model is unnecessary.
- The default file path is reader → TokenSplitter → docstore/vectorstore. IndexPipeline.handle_docs indexes text separately from image and table artifacts. The configured splitter uses chunk_size and chunk_overlap from existing settings.
- The ktem file index records chunk-to-file relationships in its SQL Index table. It adds file_id to parsed document metadata; the uploaded source record stores name, storage hash, and a JSON note. The upload flow does not preserve a Wiki hierarchy by itself.
- VectorRetrieval supports vector, text, and hybrid modes. Its hybrid branch runs docstore full-text search only when a chunk scope is supplied. DocumentRetrievalPipeline currently returns no results when there is no selected source file. Scope planning therefore needs a separate workstream that preserves this UI contract while adding an Agent-facing search path.
- Rerankers are configurable. Cohere is one available choice, not a hard-coded dependency of VectorRetrieval.
- PrepareEvidencePipeline currently builds evidence from file_name and page_label and token-splits the combined evidence to its budget. Citation UI later maps cited text back to RetrievedDocument objects. Canonical metadata must preserve existing file_name and page_label fields.

## Goals

- Store a consistent, JSON-compatible knowledge metadata shape on newly indexed chunks without changing the Document class or requiring a storage migration.
- Preserve a caller-supplied logical namespace and derive a safe document-level virtual path when none is supplied.
- Select chunking strategies by normalized source_type, while retaining the configured TokenSplitter as the universal fallback and as secondary splitting for oversized semantic units.
- Preserve document, section, page, source, and parent-child provenance through indexing so later planner, retrieval, context, and citation work can use it.
- Keep existing file-index and QA behavior working for older records without the new metadata.

## Non-Goals

- Building or connecting an enterprise Wiki, Git service, or other external knowledge source.
- Extracting entities with an LLM. The entity field is preserved when supplied and defaults to an empty mapping.
- Changing retrieval ranking, scope planning, top-k, context assembly, or citation rendering in this workstream.
- Migrating or rewriting existing stored chunks. Existing records remain retrievable; reindexing is required to add the new metadata to historical content.

## Design

### Canonical metadata

Add a focused knowledge module under kotaemon/indices/knowledge. It will define the supported source types, metadata normalization helpers, the chunk strategy interface, and the strategy registry. Canonical values live in Document.metadata; Document and RetrievedDocument remain unchanged.

Every newly indexed chunk receives these keys:

| Key | Type and source |
| --- | --- |
| source_type | One of wiki, markdown, pdf, faq, code, ppt, excel, other. Explicit input wins; otherwise infer from file extension. Unknown or missing values become other. |
| virtual_path | A normalized slash-rooted logical path. Use explicit caller metadata when present. Otherwise use / plus document_name; never expose the temporary or absolute upload path as a logical path. |
| document_id | Stable source/file id when available, falling back to existing document id/name metadata. |
| document_name | Existing file_name or an equivalent caller value; otherwise a safe path basename. |
| section_path | List of heading names; empty when the parser exposes no section hierarchy. |
| parent_id | Semantic parent identifier when one exists; otherwise the parsed source document id. |
| chunk_id | The indexed Document.doc_id. |
| entity | A JSON-compatible mapping supplied by the caller; defaults to an empty mapping. |
| page | Existing page_label/page_number value when available; existing fields remain intact. |
| source | Existing source value, preserved without replacing file_name or file_path. |

Metadata normalization merges canonical keys into the existing metadata instead of replacing loader metadata. It retains compatibility aliases such as page_label, file_path, file_id, sheet_name, and parser-specific attributes. Explicit source_type and virtual_path values take precedence over inference. Path normalization removes duplicate separators and dot segments and prevents parent traversal; it performs no filesystem operation.

At file level, persist source_type, virtual_path, document_name, and entity under the existing SQL Source.note["knowledge"] mapping. Merge with the existing note so token counts, loader name, and other current fields survive. This gives the later planner a small SQL-backed metadata catalog without a schema migration. On chunks, resolve document_id from explicit document_id, then file_id, then the parsed source document id. Resolve parent_id from explicit parent_id, then the LlamaIndex SOURCE relationship, then the parsed document id. Resolve page from explicit page, then page_label, then page_number. A non-dictionary entity value becomes an empty mapping.

Source-type inference is explicit and deterministic: .md/.markdown → markdown; .pdf → pdf; .faq → faq; .ppt/.pptx → ppt; .xls/.xlsx/.csv → excel; .py/.js/.jsx/.ts/.tsx/.java/.go/.rs/.c/.h/.cpp/.hpp → code; all other extensions → other. wiki is assigned only by caller metadata because this repository has no Wiki-specific file extension or connector. An explicit supported source_type always takes precedence; unsupported values become other.

For .faq and code text extensions, the default file route uses the existing TxtReader unless a developer-configured reader override exists. This makes AST and FAQ strategies receive source text without requiring the optional Unstructured parser.

### Chunk strategy registry

The registry selects a strategy from normalized source_type. Strategies accept one Document and return a list of Documents. They preserve unrelated metadata and update canonical section/parent/chunk fields after splitting. The registry is replaceable by callers so custom source adapters can be added without changing VectorIndexing or implementing a second indexing flow.

| Source type | Strategy |
| --- | --- |
| wiki, markdown | Split on Markdown headings into natural sections. Maintain the full heading stack as section_path. Split only sections that exceed the configured chunk limit with the existing recursive/token splitter. |
| faq | Keep one parsed Question + Answer pair per retrieval unit. Support explicit question/answer metadata and line-based Q:/Question: followed by A:/Answer: text; answer lines continue until the next question marker. If any pair is incomplete or the input cannot be parsed, use the token fallback for the whole input instead of combining uncertain records. |
| code | For Python, use the standard-library AST and emit a class header/docstring unit, one unit per top-level function, and one unit per method. Method metadata includes its class name and its parent_id points to the class unit. Oversized symbols use the token fallback. AST parse failures and other languages use the token fallback. |
| pdf | Use section_path or heading metadata supplied by the selected parser. Preserve page metadata. When no reliable section structure is present, use the existing token strategy. |
| ppt | Preserve one semantic unit per parser-reported slide. The adapter uses slide_number or page_number boundaries from the selected reader; if a reader gives only a flat document, retain the existing token fallback rather than inventing slide boundaries. |
| excel | Treat the first worksheet row as column headers and emit each subsequent non-empty row as a unit with sheet name, one-based row number, column labels, and row values rendered as label/value pairs. Split an oversized row with the token fallback. |
| other | Use the existing TokenSplitter with current chunk size and overlap settings. |

Wiki input uses the same heading parser as Markdown when its content is Markdown-like; source_type remains wiki and virtual_path remains caller-owned. This is an adapter contract, not a Wiki integration.

### Ingestion integration

IndexPipeline keeps its current reader and storage lifecycle. It gains an optional chunk strategy. If one is configured, each text document is passed through the selected strategy; otherwise the current splitter path is retained. The default file-index route chooses a strategy from caller metadata and file extension, configures it with the existing chunk_size and chunk_overlap settings, then normalizes metadata on all resulting text, table, and image records before they are written to the docstore and vector store.

The Excel route will use a row-producing reader for new indexing while preserving the existing PandasExcelReader as a fallback for parse failures. The PPT route will request element-level parsing from the existing Unstructured reader and group only when parser metadata provides slide boundaries. These choices preserve the current optional parser dependency model and do not add a new mandatory package.

The optional ingestion metadata contract accepts source_type, virtual_path, document_name, entity, and caller-defined metadata. IndexPipeline.stream accepts a knowledge_metadata mapping for one file. The batch file index accepts knowledge_metadata_by_path, keyed by the original input path, and passes the matching mapping to each file pipeline. Caller values override inferred values; all remaining loader metadata is retained. Callers cannot override the indexing-owned identity fields file_id, document_id, or collection_name; IndexPipeline.stream rejects those keys before file lookup, storage, parsing, or indexing. Metadata supplied by trusted readers continues through normal parser-metadata normalization. When no logical path is provided, the normalized path is /document_name. Existing upload calls need no changes to keep working.

### Compatibility and failure behavior

- Existing Document and RetrievedDocument types, stored metadata, vector stores, docstores, file selectors, and citations remain valid.
- The default fixed-size splitter remains active for unknown source types, malformed structure, unsupported languages, missing slide boundaries, and oversized semantic units.
- Parser or AST failures fall back to the current token strategy and do not abort indexing solely because structure extraction failed.
- No storage migration is required. Old records without canonical fields continue through the existing global/file-scoped retrieval path.

## Acceptance Criteria

1. Metadata normalization produces all canonical keys and preserves original loader metadata and legacy keys.
2. An explicit virtual_path survives normalization; a missing one falls back to a slash-rooted document-name path without including the local absolute path.
3. Markdown heading levels create separate sections with the correct full heading path; oversized sections split without losing their path.
4. FAQ parsing keeps each Q+A pair separate and malformed input uses the token fallback.
5. Python AST chunking yields independently searchable class/function/method units with correct names; invalid Python falls back.
6. PDF section metadata and page labels survive chunking. PPT slide units are separated only when reader metadata exposes slide boundaries. Excel produces one unit per data row with sheet, row, and column metadata.
7. Unsupported source types use the existing TokenSplitter configuration.
8. A file-index integration fixture persists normalized metadata in the docstore and vector store, and the existing retrieval/citation call path can still read it.
9. A legacy Document with no knowledge metadata remains accepted and indexable.

## Validation Plan

Unit coverage will exercise path normalization, source-type inference, metadata preservation, Markdown headings and secondary splitting, FAQ units, Python AST units and parse fallback, structured PDF/PPT metadata behavior, Excel row units, and unknown-type token fallback. An integration fixture will index small in-memory files, verify that chunk metadata survives both storage writes, and verify that the existing file-scoped retrieval/citation path still accepts the resulting RetrievedDocument objects.

For the later evaluation workstream, this repository has no enterprise Wiki corpus or relevance judgments. Unless supplied separately, the offline evaluator will use synthetic fixtures and report only mechanics/fixture metrics; it will not claim production Recall or wrong-scope improvements.

## Risks and Mitigations

- Source parsers expose inconsistent structural metadata. Strategies use only reliable boundaries and fall back to TokenSplitter when the parser cannot establish them.
- The uploader flattens files into hashed storage, so filesystem layout is not a valid knowledge hierarchy. virtual_path is explicit logical metadata and defaults to document name.
- New canonical metadata will appear on reindexed/new chunks only. Existing chunks remain available without it, and later planning must treat absent scope metadata as a global-search case.
- Text extraction quality varies by parser configuration. Unit fixtures validate our adapters, while real-source quality requires representative user data.
