import pandas as pd
import pytest

from kotaemon.base import Document
from kotaemon.loaders.excel_loader import ExcelRowReader
from kotaemon.loaders.pptx_loader import PptxReader, group_slide_documents


@pytest.mark.parametrize(
    "selection, expected", [(0, ["Week 1"]), ([0, 1], ["Week 1", "Week 2"])]
)
def test_excel_numeric_sheet_selection_records_real_tab_names(
    tmp_path, selection, expected
):
    file = tmp_path / "weekly.xlsx"
    with pd.ExcelWriter(file) as writer:
        for name in ("Week 1", "Week 2"):
            pd.DataFrame([{"work": name}]).to_excel(
                writer, index=False, sheet_name=name
            )
    documents = ExcelRowReader().load_data(file, sheet_name=selection)
    assert [document.metadata["sheet_name"] for document in documents] == expected


def test_excel_parse_fallback_receives_selected_sheet_and_reader_options(
    tmp_path, monkeypatch
):
    calls = []

    class Fallback:
        def load_data(self, file, extra_info=None, **kwargs):
            calls.append(kwargs)
            return [Document(text="legacy", metadata=extra_info or {})]

    def fail(*args, **kwargs):
        raise ValueError("bad spreadsheet")

    monkeypatch.setattr(pd, "read_excel", fail)
    documents = ExcelRowReader(fallback_reader=Fallback()).load_data(
        tmp_path / "broken.xlsx",
        sheet_name="Week 1",
        include_sheetname=True,
        extra_info={"file_id": "f1"},
    )
    assert calls == [{"sheet_name": "Week 1", "include_sheetname": True}]
    assert documents[0].metadata["file_id"] == "f1"


def test_excel_rows_keep_headers_sheet_names_and_original_row_numbers(tmp_path):
    file = tmp_path / "weekly.xlsx"
    with pd.ExcelWriter(file) as writer:
        pd.DataFrame(
            [
                {"person": "Zhang San", "work": "RAG"},
                {"person": None, "work": None},
                {"person": "Li Si", "work": "UI"},
            ]
        ).to_excel(writer, index=False, sheet_name="Week 1")
        pd.DataFrame([{"person": "Wang Wu", "work": "Tests"}]).to_excel(
            writer, index=False, sheet_name="Week 2"
        )
    documents = ExcelRowReader().load_data(file, extra_info={"file_id": "f1"})
    assert [d.metadata["row_number"] for d in documents] == [2, 4, 2]
    assert [d.metadata["sheet_name"] for d in documents] == [
        "Week 1",
        "Week 1",
        "Week 2",
    ]
    assert all(d.metadata["file_id"] == "f1" for d in documents)
    assert "person: Zhang San" in documents[0].text
    assert "work: RAG" in documents[0].text
    assert documents[0].metadata["file_name"] == "weekly.xlsx"


def test_csv_rows_and_parse_error_legacy_fallback(tmp_path, monkeypatch):
    file = tmp_path / "weekly.csv"
    file.write_text("person,work\nZhang San,RAG\nLi Si,UI\n", encoding="utf-8")
    documents = ExcelRowReader().load_data(file)
    assert len(documents) == 2
    assert documents[0].metadata["row_number"] == 2
    assert "work: RAG" in documents[0].text

    def fail(*args, **kwargs):
        raise ValueError("bad spreadsheet")

    monkeypatch.setattr(pd, "read_csv", fail)
    assert ExcelRowReader().load_data(file)[0].text == file.read_text()

    class Fallback:
        def load_data(self, file, extra_info=None, **kwargs):
            return [Document(text="legacy", metadata=extra_info or {})]

    monkeypatch.setattr(pd, "read_excel", fail)
    documents = ExcelRowReader(fallback_reader=Fallback()).load_data(
        tmp_path / "broken.xlsx", extra_info={"file_id": "f1"}
    )
    assert documents[0].text == "legacy"
    assert documents[0].metadata["file_id"] == "f1"


def test_excel_configured_skiprows_keeps_physical_row_numbers(tmp_path):
    file = tmp_path / "weekly.csv"
    file.write_text(
        "report\nperson,work\nZhang San,RAG\nignored,line\nLi Si,UI\n", encoding="utf-8"
    )
    documents = ExcelRowReader(pandas_config={"skiprows": [0, 3]}).load_data(file)
    assert [d.metadata["row_number"] for d in documents] == [3, 5]


def test_slide_grouping_and_missing_boundaries_preserve_all_text():
    docs = [
        Document(text="title", metadata={"page_number": 1}),
        Document(text="body", metadata={"page_number": 1}),
        Document(text="next", metadata={"slide_number": 2}),
    ]
    slides = group_slide_documents(docs)
    assert len(slides) == 2
    assert slides[0].metadata["slide_number"] == 1
    assert slides[0].metadata["slide_title"] == "title"
    assert slides[0].text == "title\n\nbody"
    for docs in (
        [Document(text="one"), Document(text="two")],
        [Document(text="one", metadata={"page_number": 1}), Document(text="two")],
    ):
        flat = group_slide_documents(docs)
        assert len(flat) == 1
        assert "one" in flat[0].text and "two" in flat[0].text
        assert "slide_number" not in flat[0].metadata
    assert group_slide_documents([]) == []


def test_ppt_reader_requests_parser_elements_and_groups_them(tmp_path):
    calls = []

    class Reader:
        def load_data(self, file, **kwargs):
            calls.append(kwargs)
            return [
                Document(text="title", metadata={"page_number": 1}),
                Document(text="body", metadata={"page_number": 1}),
            ]

    file = tmp_path / "demo.pptx"
    slides = PptxReader(reader=Reader()).load_data(file, extra_info={"file_id": "f1"})
    assert calls[0]["split_documents"] is True
    assert len(slides) == 1
    assert slides[0].metadata["presentation"] == "demo.pptx"
    assert slides[0].metadata["file_id"] == "f1"
