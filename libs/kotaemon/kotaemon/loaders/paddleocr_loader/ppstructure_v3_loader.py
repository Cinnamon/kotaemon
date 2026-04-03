from pathlib import Path

from kotaemon.base import Document, Param
from kotaemon.loaders.base import BaseReader

from .adapter import PaddleOCRResult


class PPStructureV3Reader(BaseReader):
    """Document structure extraction via PaddleOCR PPStructureV3.

    Layout detection, OCR pipeline, table/chart/formula/seal recognition.
    Model: https://huggingface.co/PaddlePaddle/PP-DocLayout-L
    """

    _dependencies = ["paddleocr[doc-parser]"]

    device: str = Param(
        "gpu:0",
        help="Device for inference: gpu:0, cpu, npu:0, xpu:0",
    )

    supported_file_types: list[str] = Param(
        [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"],
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
                "Please install paddleocr: 'pip install \"paddleocr[doc-parser]\"'"
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
            "textline_orientation_model_name": self.textline_orientation_model_name,
            "textline_orientation_model_dir": self.textline_orientation_model_dir,
            "textline_orientation_batch_size": self.textline_orientation_batch_size,
            "text_recognition_model_name": self.text_recognition_model_name,
            "text_recognition_model_dir": self.text_recognition_model_dir,
            "text_recognition_batch_size": self.text_recognition_batch_size,
            "text_rec_score_thresh": self.text_rec_score_thresh,
            "table_classification_model_name": self.table_classification_model_name,
            "table_classification_model_dir": self.table_classification_model_dir,
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
            "seal_text_detection_model_name": self.seal_text_detection_model_name,
            "seal_text_detection_model_dir": self.seal_text_detection_model_dir,
            "seal_det_limit_side_len": self.seal_det_limit_side_len,
            "seal_det_limit_type": self.seal_det_limit_type,
            "seal_det_thresh": self.seal_det_thresh,
            "seal_det_box_thresh": self.seal_det_box_thresh,
            "seal_det_unclip_ratio": self.seal_det_unclip_ratio,
            "seal_text_recognition_model_name": self.seal_text_recognition_model_name,
            "seal_text_recognition_model_dir": self.seal_text_recognition_model_dir,
            "seal_text_recognition_batch_size": self.seal_text_recognition_batch_size,
            "seal_rec_score_thresh": self.seal_rec_score_thresh,
            "formula_recognition_model_name": self.formula_recognition_model_name,
            "formula_recognition_model_dir": self.formula_recognition_model_dir,
            "formula_recognition_batch_size": self.formula_recognition_batch_size,
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
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
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

        return PaddleOCRResult(
            raw_result=raw_result,
            file_path=file_path,
            extra_info=extra_info or {},
        ).to_documents()
