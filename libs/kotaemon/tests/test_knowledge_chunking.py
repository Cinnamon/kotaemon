import pytest

from kotaemon.base import Document
from kotaemon.indices.knowledge.chunking import get_chunk_strategy
from kotaemon.indices.splitters import TokenSplitter


def test_python_symbols_keep_methods_linked_to_class_and_source_metadata():
    document = Document(
        text='import os\n\nclass Coupon:\n    """Coupon rules."""\n    rate = 1\n\n'
        "    @staticmethod\n    def apply():\n        return True\n\n"
        "async def calculate():\n    return 1\n",
        metadata={"source_type": "code", "file_name": "coupon.py", "file_id": "f1"},
        excluded_llm_metadata_keys=["file_id"],
    )
    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)
    class_chunk = next(
        c
        for c in chunks
        if c.metadata.get("class_name") == "Coupon"
        and not c.metadata.get("function_name")
    )
    method_chunk = next(c for c in chunks if c.metadata.get("function_name") == "apply")
    assert "Coupon rules." in class_chunk.text
    assert "rate = 1" in class_chunk.text
    assert "def apply" not in class_chunk.text
    assert "@staticmethod" in method_chunk.text
    assert method_chunk.metadata["parent_id"] == class_chunk.doc_id
    assert method_chunk.metadata["class_name"] == "Coupon"
    assert method_chunk.metadata["language"] == "python"
    assert any(c.metadata.get("function_name") == "calculate" for c in chunks)
    assert any("import os" in c.text for c in chunks)
    assert all(c.metadata["document_id"] == "f1" for c in chunks)
    assert all(c.metadata["chunk_id"] == c.doc_id for c in chunks)
    assert all(c.excluded_llm_metadata_keys == ["file_id"] for c in chunks)


@pytest.mark.parametrize(
    "text, name",
    [
        ("def broken(:\n    pass", "broken.py"),
        ("value = 1", "constants.py"),
        ("function calculate() { return 1; }", "calculate.ts"),
    ],
)
def test_code_fallback_keeps_unparsed_or_symbol_free_text(text, name):
    document = Document(text=text, metadata={"source_type": "code", "file_name": name})
    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)
    assert [c.text for c in chunks] == [text]


def test_oversized_python_symbol_keeps_symbol_metadata():
    document = Document(
        text="def calculate():\n" + "    value = 1\n" * 100,
        metadata={"source_type": "code", "file_name": "long.py"},
    )
    chunks = get_chunk_strategy(
        "code", TokenSplitter(chunk_size=12, chunk_overlap=0)
    ).split(document)
    assert len(chunks) > 1
    assert all(c.metadata["function_name"] == "calculate" for c in chunks)
    assert len({c.metadata["parent_id"] for c in chunks}) == 1


def test_python_inline_class_keeps_declaration():
    document = Document(
        text="class Coupon: pass",
        metadata={"source_type": "code", "file_name": "coupon.py"},
    )
    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)
    assert "class Coupon:" in chunks[0].text
    assert "pass" in chunks[0].text


def test_python_preserves_comments_outside_ast_symbol_spans():
    document = Document(
        text="# business rule\nclass Coupon:\n    # method policy\n"
        "    def apply(self):\n        return True\n\n# trailing rule\n",
        metadata={"source_type": "code", "file_name": "coupon.py"},
    )
    chunks = get_chunk_strategy("code", TokenSplitter(chunk_size=100)).split(document)
    for comment in ("# business rule", "# method policy", "# trailing rule"):
        assert any(comment in chunk.text for chunk in chunks)


def test_pdf_heading_metadata_and_page_survive_secondary_splitting():
    document = Document(
        text="calibration " * 50,
        metadata={"source_type": "pdf", "heading": "Setup", "page_label": 4},
    )
    chunks = get_chunk_strategy(
        "pdf", TokenSplitter(chunk_size=8, chunk_overlap=0)
    ).split(document)
    assert len(chunks) > 1
    assert all(c.metadata["section_path"] == ["Setup"] for c in chunks)
    assert all(c.metadata["page_label"] == 4 for c in chunks)
    flat = Document(text="flat PDF", metadata={"source_type": "pdf"})
    assert [
        c.text
        for c in get_chunk_strategy("pdf", TokenSplitter(chunk_size=100)).split(flat)
    ] == [flat.text]


def test_ppt_and_excel_strategy_preserve_semantic_boundaries():
    slide = Document(
        text="title\nbody",
        metadata={
            "source_type": "ppt",
            "slide_number": 2,
            "slide_title": "Architecture",
            "file_name": "overview.pptx",
        },
    )
    chunks = get_chunk_strategy("ppt", TokenSplitter(chunk_size=100)).split(slide)
    assert chunks[0].metadata["section_path"] == ["Architecture"]
    assert chunks[0].metadata["presentation"] == "overview.pptx"
    row = Document(
        text="person: Zhang San",
        metadata={"source_type": "excel", "sheet_name": "Week 1", "row_number": 2},
    )
    chunks = get_chunk_strategy("excel", TokenSplitter(chunk_size=100)).split(row)
    assert chunks[0].metadata["section_path"] == ["Week 1", "Row 2"]


def test_markdown_chunks_keep_heading_paths():
    document = Document(
        text="# Interns\n\nintro\n\n## Zhang San\n\nBuilt a RAG API.",
        metadata={"source_type": "markdown", "file_name": "interns.md"},
    )

    chunks = get_chunk_strategy("markdown", TokenSplitter(chunk_size=100)).split(
        document
    )

    assert [chunk.metadata["section_path"] for chunk in chunks] == [
        ["Interns"],
        ["Interns", "Zhang San"],
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
    nested_chunks = get_chunk_strategy("markdown", TokenSplitter(chunk_size=100)).split(
        nested
    )
    assert nested_chunks[-1].metadata["section_path"] == [
        "Handbook",
        "API",
        "Ownership",
    ]

    plain = Document(text="plain text", metadata={"source_type": "markdown"})
    plain_chunks = get_chunk_strategy("markdown", TokenSplitter(chunk_size=100)).split(
        plain
    )
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
    explicit_chunks = get_chunk_strategy("faq", TokenSplitter(chunk_size=100)).split(
        explicit
    )
    assert len(explicit_chunks) == 1
    assert "Owner?" in explicit_chunks[0].text
    assert "Zhang San" in explicit_chunks[0].text

    multiline = Document(
        text="Q: How?\nA: First line\nsecond line",
        metadata={"source_type": "faq"},
    )
    multiline_chunks = get_chunk_strategy("faq", TokenSplitter(chunk_size=100)).split(
        multiline
    )
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


def test_markdown_preserves_preamble_and_ignores_headings_in_fenced_code():
    document = Document(
        text="Preamble\n\n# API\n\n```python\n# comment\n```\n\nDetails",
        metadata={"source_type": "markdown", "file_id": "source-1"},
    )
    chunks = get_chunk_strategy("markdown", TokenSplitter(chunk_size=100)).split(
        document
    )
    assert [chunk.metadata["section_path"] for chunk in chunks] == [[], ["API"]]
    assert chunks[0].text == "Preamble"
    assert "# comment" in chunks[1].text
    assert all(chunk.metadata["document_id"] == "source-1" for chunk in chunks)
    assert all(chunk.metadata["chunk_id"] == chunk.doc_id for chunk in chunks)
    assert document.metadata == {"source_type": "markdown", "file_id": "source-1"}


def test_oversized_faq_retains_one_semantic_parent_and_question_path():
    document = Document(
        text="Q: How?\nA: " + "detail " * 80,
        metadata={"source_type": "faq", "file_id": "source-1", "page_label": 2},
    )
    chunks = get_chunk_strategy(
        "faq", TokenSplitter(chunk_size=8, chunk_overlap=0)
    ).split(document)
    assert len(chunks) > 1
    assert len({chunk.metadata["parent_id"] for chunk in chunks}) == 1
    assert all(chunk.metadata["section_path"] == ["How?"] for chunk in chunks)
    assert all(chunk.metadata["page_label"] == 2 for chunk in chunks)
    assert all(chunk.metadata["document_id"] == "source-1" for chunk in chunks)


def test_partial_faq_uses_whole_document_fallback():
    document = Document(
        text="Q: Complete?\nA: Yes.\n\nQ: Missing?",
        metadata={"source_type": "faq"},
    )
    chunks = get_chunk_strategy("faq", TokenSplitter(chunk_size=100)).split(document)
    assert [chunk.text for chunk in chunks] == [document.text]


def test_custom_strategy_can_be_registered_for_multiple_source_types():
    from kotaemon.indices.knowledge.chunking import register_chunk_strategy

    class CustomStrategy:
        def __init__(self, token_splitter):
            self.token_splitter = token_splitter

        def split(self, document):
            return [document]

    register_chunk_strategy(["custom-a", "custom-b"], CustomStrategy)
    splitter = TokenSplitter(chunk_size=100)
    for source_type in ["custom-a", "custom-b"]:
        strategy = get_chunk_strategy(source_type, splitter)
        assert isinstance(strategy, CustomStrategy)
        assert strategy.token_splitter is splitter


@pytest.mark.parametrize(
    "source_type, prefix", [("markdown", "# API\n\n"), ("faq", "Q: Owner?\nA: ")]
)
@pytest.mark.parametrize("chunk_size", [8, 1000])
def test_semantic_chunks_preserve_metadata_exclusions(source_type, prefix, chunk_size):
    document = Document(
        text=prefix + "detail " * 80,
        metadata={
            "source_type": source_type,
            "private_embed": "secret",
            "private_llm": "hidden",
        },
        excluded_embed_metadata_keys=["private_embed"],
        excluded_llm_metadata_keys=["private_llm"],
    )
    chunks = get_chunk_strategy(
        source_type, TokenSplitter(chunk_size=chunk_size, chunk_overlap=0)
    ).split(document)
    assert len(chunks) > 1 if chunk_size == 8 else len(chunks) == 1
    assert all(
        chunk.excluded_embed_metadata_keys == ["private_embed"] for chunk in chunks
    )
    assert all(chunk.excluded_llm_metadata_keys == ["private_llm"] for chunk in chunks)
    assert document.excluded_embed_metadata_keys == ["private_embed"]
    assert document.excluded_llm_metadata_keys == ["private_llm"]
