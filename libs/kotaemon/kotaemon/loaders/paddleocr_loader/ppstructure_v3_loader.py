"""PPStructureV3 document loader and result adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kotaemon.base import Document, Param
from kotaemon.loaders.base import BaseReader

from .adapter import PaddleOCRResult


@dataclass
class PPStructureV3Result(PaddleOCRResult):
    """Adapter for PPStructureV3 results.

    PPStructureV3 provides structured document parsing with:
    - Layout detection
    - Table recognition (HTML format)
    - Formula recognition
    - Chart/figure detection
    """

    text_labels: set[str] = field(
        default_factory=lambda: {
            "text",
            "paragraph_title",
            "doc_title",
            "abstract",
            "content",
        }
    )
    table_labels: set[str] = field(default_factory=lambda: {"table"})
    figure_labels: set[str] = field(
        default_factory=lambda: {"chart", "figure", "image"}
    )

    def to_documents(self) -> list[Document]:
        """Convert PPStructureV3 results to Documents."""
        texts: list[Document] = []
        tables: list[Document] = []
        figures: list[Document] = []

        for page_result in self.raw_result:
            result_dict = page_result.json
            page_index = result_dict.get("page_index")
            page_label = (page_index + 1) if page_index is not None else 1

            page_texts, page_tables, page_figures = self._parse_page(
                result_dict, page_label
            )
            texts.extend(page_texts)
            tables.extend(page_tables)
            figures.extend(page_figures)

        return texts + tables + figures

    def _parse_page(
        self,
        result_dict: dict,
        page_label: int,
    ) -> tuple[list[Document], list[Document], list[Document]]:
        """Parse a single page result."""
        parsing_list = result_dict.get("parsing_res_list", [])

        text_blocks: list[str] = []
        tables: list[Document] = []
        figures: list[Document] = []

        for block in parsing_list:
            label = block.get("block_label", "")
            content = block.get("block_content", "")

            if not content:
                continue

            if label in self.text_labels:
                text_blocks.append(content)

            elif label in self.table_labels:
                table_content = self._clean_table_html(content)
                tables.append(
                    Document(
                        text=table_content,
                        metadata={
                            "type": "table",
                            "page_label": page_label,
                            "table_origin": table_content,
                            "file_name": self.file_name,
                            "file_path": str(self.file_path),
                            **self.extra_info,
                        },
                    )
                )

            elif label in self.figure_labels:
                figures.append(
                    Document(
                        text=content,
                        metadata={
                            "type": "image",
                            "page_label": page_label,
                            "file_name": self.file_name,
                            "file_path": str(self.file_path),
                            **self.extra_info,
                        },
                    )
                )

        text_docs: list[Document] = []
        if text_blocks:
            text_docs.append(
                Document(
                    text="\n\n".join(text_blocks),
                    metadata={
                        "page_label": page_label,
                        "file_name": self.file_name,
                        "file_path": str(self.file_path),
                        **self.extra_info,
                    },
                )
            )

        return text_docs, tables, figures


class PPStructureV3Reader(BaseReader):
    """Document reader using PaddleOCR PPStructureV3.

    PPStructureV3 provides comprehensive document structure extraction with
    layout detection, table recognition, and formula recognition.

    Example:
        ```python
        from kotaemon.loaders import PPStructureV3Reader

        # GPU mode (default)
        reader = PPStructureV3Reader()
        documents = reader.load_data("path/to/document.pdf")

        # CPU mode
        reader = PPStructureV3Reader(device="cpu")
        ```

    Args:
        device: Device for inference - "gpu:0", "cpu", "npu:0", "xpu:0"
        use_doc_orientation_classify: Enable document orientation classification
        use_doc_unwarping: Enable document unwarping preprocessing
    """

    _dependencies = ["paddleocr"]

    device: str = Param(
        "gpu:0",
        help="Device for inference: gpu:0, cpu, npu:0, xpu:0",
    )

    supported_file_types: list[str] = Param(
        [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"],
        help="Supported file extensions",
    )

    layout_detection_model_name: str | None = Param(None)
    layout_detection_model_dir: str | None = Param(None)
    layout_threshold: float | None = Param(None)
    layout_nms: float | None = Param(None)
    layout_unclip_ratio: float | None = Param(None)
    layout_merge_bboxes_mode: str | None = Param(None)
    chart_recognition_model_name: str | None = Param(None)
    chart_recognition_model_dir: str | None = Param(None)
    chart_recognition_batch_size: int | None = Param(None)
    region_detection_model_name: str | None = Param(None)
    region_detection_model_dir: str | None = Param(None)
    doc_orientation_classify_model_name: str | None = Param(None)
    doc_orientation_classify_model_dir: str | None = Param(None)
    doc_unwarping_model_name: str | None = Param(None)
    doc_unwarping_model_dir: str | None = Param(None)
    text_detection_model_name: str | None = Param(None)
    text_detection_model_dir: str | None = Param(None)
    text_det_limit_side_len: int | None = Param(None)
    text_det_limit_type: str | None = Param(None)
    text_det_thresh: float | None = Param(None)
    text_det_box_thresh: float | None = Param(None)
    text_det_unclip_ratio: float | None = Param(None)
    textline_orientation_model_name: str | None = Param(None)
    textline_orientation_model_dir: str | None = Param(None)
    textline_orientation_batch_size: int | None = Param(None)
    text_recognition_model_name: str | None = Param(None)
    text_recognition_model_dir: str | None = Param(None)
    text_recognition_batch_size: int | None = Param(None)
    text_rec_score_thresh: float | None = Param(None)
    table_classification_model_name: str | None = Param(None)
    table_classification_model_dir: str | None = Param(None)
    wired_table_structure_recognition_model_name: str | None = Param(None)
    wired_table_structure_recognition_model_dir: str | None = Param(None)
    wireless_table_structure_recognition_model_name: str | None = Param(None)
    wireless_table_structure_recognition_model_dir: str | None = Param(None)
    wired_table_cells_detection_model_name: str | None = Param(None)
    wired_table_cells_detection_model_dir: str | None = Param(None)
    wireless_table_cells_detection_model_name: str | None = Param(None)
    wireless_table_cells_detection_model_dir: str | None = Param(None)
    table_orientation_classify_model_name: str | None = Param(None)
    table_orientation_classify_model_dir: str | None = Param(None)
    seal_text_detection_model_name: str | None = Param(None)
    seal_text_detection_model_dir: str | None = Param(None)
    seal_det_limit_side_len: int | None = Param(None)
    seal_det_limit_type: str | None = Param(None)
    seal_det_thresh: float | None = Param(None)
    seal_det_box_thresh: float | None = Param(None)
    seal_det_unclip_ratio: float | None = Param(None)
    seal_text_recognition_model_name: str | None = Param(None)
    seal_text_recognition_model_dir: str | None = Param(None)
    seal_text_recognition_batch_size: int | None = Param(None)
    seal_rec_score_thresh: float | None = Param(None)
    formula_recognition_model_name: str | None = Param(None)
    formula_recognition_model_dir: str | None = Param(None)
    formula_recognition_batch_size: int | None = Param(None)
    use_doc_orientation_classify: bool | None = Param(None)
    use_doc_unwarping: bool | None = Param(None)
    use_textline_orientation: bool | None = Param(None)
    use_seal_recognition: bool | None = Param(None)
    use_table_recognition: bool | None = Param(None)
    use_formula_recognition: bool | None = Param(None)
    use_chart_recognition: bool | None = Param(None)
    use_region_detection: bool | None = Param(None)
    format_block_content: bool | None = Param(None)
    markdown_ignore_labels: list[str] | None = Param(None)
    lang: str | None = Param(None)
    ocr_version: str | None = Param(None)

    @Param.auto(cache=True)
    def pipeline_(self):
        """Lazy-load the PPStructureV3 pipeline."""
        try:
            from paddleocr import PPStructureV3
        except ImportError:
            raise ImportError(
                "Please install paddleocr: '\"pip install paddleocr[all]\"'"
            )

        kwargs = {
            "device": self.device,
            "layout_detection_model_name": self.layout_detection_model_name,
            "layout_detection_model_dir": self.layout_detection_model_dir,
            "layout_threshold": self.layout_threshold,
            "layout_nms": self.layout_nms,
            "layout_unclip_ratio": self.layout_unclip_ratio,
            "layout_merge_bboxes_mode": self.layout_merge_bboxes_mode,
            "chart_recognition_model_name": self.chart_recognition_model_name,
            "chart_recognition_model_dir": self.chart_recognition_model_dir,
            "chart_recognition_batch_size": self.chart_recognition_batch_size,
            "region_detection_model_name": self.region_detection_model_name,
            "region_detection_model_dir": self.region_detection_model_dir,
            "doc_orientation_classify_model_name": (
                self.doc_orientation_classify_model_name
            ),
            "doc_orientation_classify_model_dir": (
                self.doc_orientation_classify_model_dir
            ),
            "doc_unwarping_model_name": self.doc_unwarping_model_name,
            "doc_unwarping_model_dir": self.doc_unwarping_model_dir,
            "text_detection_model_name": self.text_detection_model_name,
            "text_detection_model_dir": self.text_detection_model_dir,
            "text_det_limit_side_len": self.text_det_limit_side_len,
            "text_det_limit_type": self.text_det_limit_type,
            "text_det_thresh": self.text_det_thresh,
            "text_det_box_thresh": self.text_det_box_thresh,
            "text_det_unclip_ratio": self.text_det_unclip_ratio,
            "textline_orientation_model_name": (self.textline_orientation_model_name),
            "textline_orientation_model_dir": (self.textline_orientation_model_dir),
            "textline_orientation_batch_size": (self.textline_orientation_batch_size),
            "text_recognition_model_name": self.text_recognition_model_name,
            "text_recognition_model_dir": self.text_recognition_model_dir,
            "text_recognition_batch_size": self.text_recognition_batch_size,
            "text_rec_score_thresh": self.text_rec_score_thresh,
            "table_classification_model_name": (self.table_classification_model_name),
            "table_classification_model_dir": (self.table_classification_model_dir),
            "wired_table_structure_recognition_model_name": (
                self.wired_table_structure_recognition_model_name
            ),
            "wired_table_structure_recognition_model_dir": (
                self.wired_table_structure_recognition_model_dir
            ),
            "wireless_table_structure_recognition_model_name": (
                self.wireless_table_structure_recognition_model_name
            ),
            "wireless_table_structure_recognition_model_dir": (
                self.wireless_table_structure_recognition_model_dir
            ),
            "wired_table_cells_detection_model_name": (
                self.wired_table_cells_detection_model_name
            ),
            "wired_table_cells_detection_model_dir": (
                self.wired_table_cells_detection_model_dir
            ),
            "wireless_table_cells_detection_model_name": (
                self.wireless_table_cells_detection_model_name
            ),
            "wireless_table_cells_detection_model_dir": (
                self.wireless_table_cells_detection_model_dir
            ),
            "table_orientation_classify_model_name": (
                self.table_orientation_classify_model_name
            ),
            "table_orientation_classify_model_dir": (
                self.table_orientation_classify_model_dir
            ),
            "seal_text_detection_model_name": (self.seal_text_detection_model_name),
            "seal_text_detection_model_dir": self.seal_text_detection_model_dir,
            "seal_det_limit_side_len": self.seal_det_limit_side_len,
            "seal_det_limit_type": self.seal_det_limit_type,
            "seal_det_thresh": self.seal_det_thresh,
            "seal_det_box_thresh": self.seal_det_box_thresh,
            "seal_det_unclip_ratio": self.seal_det_unclip_ratio,
            "seal_text_recognition_model_name": (self.seal_text_recognition_model_name),
            "seal_text_recognition_model_dir": (self.seal_text_recognition_model_dir),
            "seal_text_recognition_batch_size": (self.seal_text_recognition_batch_size),
            "seal_rec_score_thresh": self.seal_rec_score_thresh,
            "formula_recognition_model_name": (self.formula_recognition_model_name),
            "formula_recognition_model_dir": (self.formula_recognition_model_dir),
            "formula_recognition_batch_size": (self.formula_recognition_batch_size),
            "use_doc_orientation_classify": self.use_doc_orientation_classify,
            "use_doc_unwarping": self.use_doc_unwarping,
            "use_textline_orientation": self.use_textline_orientation,
            "use_seal_recognition": self.use_seal_recognition,
            "use_table_recognition": self.use_table_recognition,
            "use_formula_recognition": self.use_formula_recognition,
            "use_chart_recognition": self.use_chart_recognition,
            "use_region_detection": self.use_region_detection,
            "format_block_content": self.format_block_content,
            "markdown_ignore_labels": self.markdown_ignore_labels,
            "lang": self.lang,
            "ocr_version": self.ocr_version,
        }
        return PPStructureV3(**kwargs)

    def run(
        self,
        file_path: str | Path,
        extra_info: dict | None = None,
        **kwargs,
    ) -> list[Document]:
        """Run the loader on a file."""
        return self.load_data(file_path, extra_info, **kwargs)

    def load_data(
        self,
        file_path: str | Path,
        extra_info: dict | None = None,
        **kwargs,
    ) -> list[Document]:
        """Extract document structure using PPStructureV3.

        Args:
            file_path: Path to the input file (PDF or image)
            extra_info: Additional metadata to include in documents

        Returns:
            List of Document objects containing text, tables, and figures
        """
        file_path = Path(file_path)

        if file_path.suffix.lower() not in self.supported_file_types:
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.supported_file_types}"
            )

        raw_result = self.pipeline_.predict(str(file_path))

        result = PPStructureV3Result(
            raw_result=raw_result,
            file_path=file_path,
            extra_info=extra_info or {},
        )

        return result.to_documents()
