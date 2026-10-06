"""Whole-unit context formatting and citation-source contract tests."""

from __future__ import annotations

from types import SimpleNamespace

from kotaemon.base import Document, RetrievedDocument
from kotaemon.indices.qa.citation_qa import AnswerWithContextPipeline
from kotaemon.indices.qa.format_context import (
    EVIDENCE_MODE_CHATBOT,
    EVIDENCE_MODE_FIGURE,
    EVIDENCE_MODE_TABLE,
    EVIDENCE_MODE_TEXT,
    PrepareEvidencePipeline,
)
from kotaemon.indices.splitters import TokenSplitter


def make_doc(doc_id, text, **metadata):
    return RetrievedDocument(id_=doc_id, text=text, metadata=metadata)


def unpack(pipeline, docs):
    result = pipeline(docs)
    return result.content


def test_oversized_first_evidence_unit_is_skipped_and_later_small_unit_is_complete():
    huge = make_doc("huge", "oversized evidence " * 80, file_name="large.md")
    small = make_doc("small", "tiny complete evidence", file_name="small.md")
    pipeline = PrepareEvidencePipeline(max_context_length=160, token_counter=len)

    mode, evidence, images = unpack(pipeline, [huge, small])

    assert mode == EVIDENCE_MODE_TEXT
    assert "oversized evidence" not in evidence
    assert "tiny complete evidence" in evidence
    assert evidence.startswith("<br><b>")
    assert evidence.endswith("<br>")
    assert evidence.count("</b>") == 1
    assert images == []
    assert len(evidence) <= 160


def test_exact_formatted_unit_budget_boundary_is_inclusive():
    doc = make_doc("one", "one exact evidence unit", file_name="handbook.md")
    expected = "<br><b>Content from handbook.md: </b> one exact evidence unit \n<br>"
    pipeline = PrepareEvidencePipeline(
        max_context_length=len(expected), token_counter=len
    )

    mode, evidence, _ = unpack(pipeline, [doc])

    assert mode == EVIDENCE_MODE_TEXT
    assert evidence == expected
    assert len(evidence) == len(expected)


def test_full_escaped_header_counts_against_budget_and_preserves_body_newlines():
    doc = make_doc(
        "metadata",
        "Line one\nLine two <literal>",
        file_name='guide<draft>".md',
        virtual_path="/team/a&b",
        section_path=["Safety <Checks>", 'Injection "Review"'],
        page_label=8,
    )
    pipeline = PrepareEvidencePipeline(max_context_length=500, token_counter=len)

    _, evidence, _ = unpack(pipeline, [doc])

    assert "guide&lt;draft&gt;&quot;.md" in evidence
    assert "/team/a&amp;b" in evidence
    assert "Safety &lt;Checks&gt;" in evidence
    assert "Injection &quot;Review&quot;" in evidence
    assert "Page 8" in evidence
    assert "Line one\nLine two <literal>" in evidence
    assert len(evidence) <= 500


def test_non_substring_window_falls_back_to_source_text_for_citations():
    source = "The original source states the release is scheduled for Friday."
    doc = make_doc(
        "source",
        source,
        file_name="release.md",
        window="A fabricated answer says Monday.",
    )
    pipeline = PrepareEvidencePipeline(max_context_length=500, token_counter=len)

    _, evidence, _ = unpack(pipeline, [doc])
    quote = "release is scheduled for Friday"
    answer = Document(metadata={"citation": SimpleNamespace(evidences=[quote])})
    spans = AnswerWithContextPipeline.match_evidence_with_context(None, answer, [doc])

    assert source in evidence
    assert "fabricated answer" not in evidence
    assert spans[doc.doc_id]
    assert (
        source[spans[doc.doc_id][0]["start"] : spans[doc.doc_id][0]["end"]].lower()
        == quote.lower()
    )


def test_table_origin_must_be_a_substring_and_five_table_cap_remains():
    tables = [
        make_doc(
            f"table-{index}",
            f"Source evidence table number {index} has columns A and B.",
            file_name=f"table-{index}.xlsx",
            type="table",
            table_origin=(
                f"Source evidence table number {index}"
                if index < 5
                else "fabricated table body"
            ),
        )
        for index in range(6)
    ]
    pipeline = PrepareEvidencePipeline(max_context_length=10000, token_counter=len)

    mode, evidence, images = unpack(pipeline, tables)

    assert mode == EVIDENCE_MODE_TABLE
    assert "Source evidence table number 0" in evidence
    assert "fabricated table body" not in evidence
    assert "Source evidence table number 5" not in evidence
    assert images == []


def test_image_and_chatbot_modes_keep_only_included_image_references():
    image = make_doc(
        "image",
        "A diagram shows the deployment topology.",
        file_name="architecture<draft>.pdf",
        type="image",
        image_origin="image://included",
    )
    chatbot = make_doc(
        "chatbot",
        "User asks for a password reset.",
        file_name="support.csv",
        type="chatbot",
        window="User asks for a password reset.",
        page_label="row-12",
    )
    pipeline = PrepareEvidencePipeline(max_context_length=1000, token_counter=len)

    image_mode, image_evidence, image_refs = unpack(pipeline, [image])
    chatbot_mode, chatbot_evidence, chatbot_refs = unpack(pipeline, [chatbot])

    assert image_mode == EVIDENCE_MODE_FIGURE
    assert "alt='A diagram shows the deployment topology.'" in image_evidence
    assert "architecture&lt;draft&gt;.pdf" in image_evidence
    assert image_refs == ["image://included"]
    assert chatbot_mode == EVIDENCE_MODE_CHATBOT
    assert "User asks for a password reset." in chatbot_evidence
    assert "row-12" in chatbot_evidence
    assert chatbot_refs == []


def test_skipped_image_does_not_contribute_image_reference():
    huge_image = make_doc(
        "huge-image",
        "A long figure caption. " * 30,
        file_name="figure.pdf",
        type="image",
        image_origin="image://too-large",
    )
    small_text = make_doc("text", "small text fits", file_name="notes.md")
    pipeline = PrepareEvidencePipeline(max_context_length=130, token_counter=len)

    _, evidence, images = unpack(pipeline, [huge_image, small_text])

    assert "small text fits" in evidence
    assert "A long figure caption" not in evidence
    assert images == []


def test_legacy_trim_func_chunk_size_is_a_whole_unit_budget():
    splitter = TokenSplitter(
        chunk_size=120, chunk_overlap=0, tokenizer=lambda text: list(text)
    )
    doc = make_doc(
        "whole",
        "This source unit is longer than one hundred and twenty characters. " * 3,
    )
    pipeline = PrepareEvidencePipeline(max_context_length=1000, trim_func=splitter)

    _, evidence, _ = unpack(pipeline, [doc])

    assert evidence == ""


def test_included_chunk_ids_and_full_context_token_use_are_exposed_to_trace():
    first = make_doc("first", "one", file_name="first.md")
    too_large = make_doc("large", "x" * 200, file_name="large.md")
    trace = {}
    pipeline = PrepareEvidencePipeline(max_context_length=100, token_counter=len)

    _, evidence, _ = pipeline([first, too_large], trace=trace).content

    assert "one" in evidence
    assert trace["context_chunk_ids"] == ["first"]
    assert trace["context_tokens"] == len(evidence)
    assert trace["context_token_budget"] == 100
