"""Unit tests for PaddleOCR loaders and result adapters."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pytest

from kotaemon.base import Document
from kotaemon.loaders.paddleocr_loader.adapter import PaddleOCRResult

from .conftest import skip_when_paddleocr_not_installed

if TYPE_CHECKING:
    from pytest_mock.plugin import MockerFixture


def _make_page_result(inner_dict: dict) -> MagicMock:
    """Build a mock page result with .json['res'] as used by the adapter."""
    page = MagicMock()
    page.json = {"res": inner_dict}
    return page


class TestPaddleOCRResultAdapter:
    """Tests for base adapter and _clean_table_html."""

    def test_clean_table_html_strips_wrapper(self) -> None:
        """_clean_table_html removes <html><body> wrapper."""
        raw = [_make_page_result({"page_index": 0, "parsing_res_list": []})]
        path = Path("/tmp/doc.pdf")
        result = PaddleOCRResult(raw_result=raw, file_path=path, extra_info={})
        out = result._clean_table_html("<html><body><table>x</table></body></html>")
        assert out.strip() == "<table>x</table>"

    def test_file_name_property(self) -> None:
        """file_name returns the path name."""
        raw = [_make_page_result({"page_index": 0, "parsing_res_list": []})]
        result = PaddleOCRResult(
            raw_result=raw,
            file_path=Path("/some/dir/doc.pdf"),
            extra_info={},
        )
        assert result.file_name == "doc.pdf"


class TestPaddleOCRResult:
    """Tests for PaddleOCRResult.to_documents()."""

    def test_to_documents_text_and_table(self) -> None:
        """to_documents returns text and table docs from parsing_res_list."""
        raw = [
            _make_page_result(
                {
                    "page_index": 0,
                    "parsing_res_list": [
                        {"block_label": "paragraph_title", "block_content": "Title"},
                        {"block_label": "text", "block_content": "Body text."},
                        {
                            "block_label": "table",
                            "block_content": "<html><body><table><tr><td>A</td></tr>"
                            "</table></body></html>",
                        },
                    ],
                }
            )
        ]
        result = PaddleOCRResult(
            raw_result=raw,
            file_path=Path("doc.pdf"),
            extra_info={"source": "test"},
        )
        docs = result.to_documents()

        text_docs = [d for d in docs if d.metadata.get("type") != "table"]
        table_docs = [d for d in docs if d.metadata.get("type") == "table"]

        assert len(text_docs) == 1
        assert "Title" in text_docs[0].text and "Body text." in text_docs[0].text
        assert text_docs[0].metadata.get("source") == "test"

        assert len(table_docs) == 1
        assert "A" in table_docs[0].text
        assert table_docs[0].metadata["table_origin"]
        assert table_docs[0].metadata["page_label"] == 1

    def test_to_documents_skips_empty_content(self) -> None:
        """Blocks with empty block_content are skipped."""
        raw = [
            _make_page_result(
                {
                    "page_index": 0,
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": ""},
                        {"block_label": "paragraph_title", "block_content": "Only"},
                    ],
                }
            )
        ]
        result = PaddleOCRResult(raw_result=raw, file_path=Path("x.pdf"), extra_info={})
        docs = result.to_documents()
        assert len(docs) == 1
        assert docs[0].text.strip() == "Only"


class TestPPStructureV3Reader:
    """Tests for PPStructureV3Reader."""

    def test_unsupported_file_type_raises(self) -> None:
        """load_data raises ValueError for unsupported extension."""
        from kotaemon.loaders import PPStructureV3Reader

        reader = PPStructureV3Reader()
        with pytest.raises(ValueError, match="Unsupported file type"):
            reader.load_data(Path("/tmp/file.xyz"))

    @skip_when_paddleocr_not_installed
    def test_supported_file_types_attribute(self) -> None:
        """Reader has expected supported_file_types."""
        from kotaemon.loaders import PPStructureV3Reader

        reader = PPStructureV3Reader()
        assert ".pdf" in reader.supported_file_types
        assert ".png" in reader.supported_file_types

    def test_load_data_returns_documents_with_mocked_pipeline(
        self, mocker: MockerFixture
    ) -> None:
        """load_data returns list of Documents when pipeline is mocked."""
        from kotaemon.loaders.paddleocr_loader.ppstructure_v3_loader import (
            PPStructureV3Reader,
        )

        mock_raw = [
            _make_page_result(
                {
                    "page_index": 0,
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": "Hello"},
                    ],
                }
            )
        ]
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = mock_raw

        mocker.patch.object(
            PPStructureV3Reader,
            "pipeline_",
            new_callable=PropertyMock,
            return_value=mock_pipeline,
        )
        reader = PPStructureV3Reader()

        docs = reader.load_data(Path("/tmp/doc.pdf"), extra_info={})

        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)
        mock_pipeline.predict.assert_called_once_with("/tmp/doc.pdf")


class TestPaddleOCRVLReader:
    """Tests for PaddleOCRVLReader."""

    def test_unsupported_file_type_raises(self) -> None:
        """load_data raises ValueError for unsupported extension."""
        from kotaemon.loaders import PaddleOCRVLReader

        reader = PaddleOCRVLReader()
        with pytest.raises(ValueError, match="Unsupported file type"):
            reader.load_data(Path("/tmp/file.xyz"))

    @skip_when_paddleocr_not_installed
    def test_supported_file_types_attribute(self) -> None:
        """Reader has expected supported_file_types."""
        from kotaemon.loaders import PaddleOCRVLReader

        reader = PaddleOCRVLReader()
        assert ".pdf" in reader.supported_file_types
        assert ".png" in reader.supported_file_types

    def test_run_returns_same_as_load_data_with_mocked_pipeline(
        self, mocker: MockerFixture
    ) -> None:
        """run() returns the same documents as load_data for same input."""
        from kotaemon.loaders import PaddleOCRVLReader

        mock_raw = [
            _make_page_result(
                {
                    "page_index": 0,
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": "VL text"},
                    ],
                }
            )
        ]
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = mock_raw

        mocker.patch.object(
            PaddleOCRVLReader,
            "pipeline_",
            new_callable=PropertyMock,
            return_value=mock_pipeline,
        )
        reader = PaddleOCRVLReader()
        path = Path("/tmp/img.png")

        load_docs = reader.load_data(path)
        run_docs = reader.run(path)

        assert len(load_docs) == len(run_docs)
        for a, b in zip(load_docs, run_docs):
            assert a.text == b.text
            assert a.metadata == b.metadata
        assert len(run_docs) >= 1

    def test_load_data_returns_documents_with_mocked_pipeline(
        self, mocker: MockerFixture
    ) -> None:
        """load_data returns list of Documents when pipeline is mocked."""
        from kotaemon.loaders import PaddleOCRVLReader

        mock_raw = [
            _make_page_result(
                {
                    "page_index": 0,
                    "parsing_res_list": [
                        {"block_label": "text", "block_content": "VL text"},
                    ],
                }
            )
        ]
        mock_pipeline = MagicMock()
        mock_pipeline.predict.return_value = mock_raw

        mocker.patch.object(
            PaddleOCRVLReader,
            "pipeline_",
            new_callable=PropertyMock,
            return_value=mock_pipeline,
        )
        reader = PaddleOCRVLReader()

        docs = reader.load_data(Path("/tmp/img.png"))

        assert len(docs) >= 1
        assert all(isinstance(d, Document) for d in docs)
        mock_pipeline.predict.assert_called_once_with("/tmp/img.png")
