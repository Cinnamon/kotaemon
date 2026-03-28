from pathlib import Path

from kotaemon.base import Document, Param
from kotaemon.loaders.base import BaseReader

from .adapter import PaddleOCRResult


class PaddleOCRVLReader(BaseReader):
    """Multilingual document parsing via PaddleOCR-VL-1.5 (0.9B VLM).

    Handles text, tables, formulas, charts, seal recognition, and text spotting.
    Robust to skew, warping, scanning, lighting, and screen photography.
    Supports cross-page table merging and paragraph heading recognition.
    Model: https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.5
    """

    _dependencies = ["paddleocr[doc-parser]"]

    device: str = Param(
        "gpu:0",
        help="Device for inference: gpu:0, cpu, npu:0, xpu:0",
    )

    supported_file_types: list[str] = Param(
        [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
        help="Supported file extensions",
    )

    pipeline_version: str | None = Param("v1.5")
    layout_detection_model_name: str | None = Param(None)
    layout_detection_model_dir: str | None = Param(None)
    layout_threshold: float | None = Param(None)
    layout_nms: float | None = Param(None)
    layout_unclip_ratio: float | None = Param(None)
    layout_merge_bboxes_mode: str | None = Param(None)
    vl_rec_model_name: str | None = Param(None)
    vl_rec_model_dir: str | None = Param(None)
    vl_rec_backend: str | None = Param(None)
    vl_rec_server_url: str | None = Param(None)
    vl_rec_max_concurrency: int | None = Param(None)
    vl_rec_api_model_name: str | None = Param(None)
    vl_rec_api_key: str | None = Param(None)
    doc_orientation_classify_model_name: str | None = Param(None)
    doc_orientation_classify_model_dir: str | None = Param(None)
    doc_unwarping_model_name: str | None = Param(None)
    doc_unwarping_model_dir: str | None = Param(None)
    use_doc_orientation_classify: bool | None = Param(None)
    use_doc_unwarping: bool | None = Param(None)
    use_layout_detection: bool | None = Param(None)
    use_chart_recognition: bool | None = Param(None)
    use_seal_recognition: bool | None = Param(None)
    use_ocr_for_image_block: bool | None = Param(None)
    format_block_content: bool | None = Param(None)
    merge_layout_blocks: bool | None = Param(None)
    markdown_ignore_labels: list[str] | None = Param(None)
    use_queues: bool | None = Param(None)

    @Param.auto(cache=True)
    def pipeline_(self):
        """Lazy-load the PaddleOCRVL pipeline."""
        try:
            from paddleocr import PaddleOCRVL
        except ImportError:
            raise ImportError(
                "Please install paddleocr: 'pip install \"paddleocr[doc-parser]\"'"
            )

        kwargs = {
            "device": self.device,
            "pipeline_version": self.pipeline_version,
            "layout_detection_model_name": self.layout_detection_model_name,
            "layout_detection_model_dir": self.layout_detection_model_dir,
            "layout_threshold": self.layout_threshold,
            "layout_nms": self.layout_nms,
            "layout_unclip_ratio": self.layout_unclip_ratio,
            "layout_merge_bboxes_mode": self.layout_merge_bboxes_mode,
            "vl_rec_model_name": self.vl_rec_model_name,
            "vl_rec_model_dir": self.vl_rec_model_dir,
            "vl_rec_backend": self.vl_rec_backend,
            "vl_rec_server_url": self.vl_rec_server_url,
            "vl_rec_max_concurrency": self.vl_rec_max_concurrency,
            "vl_rec_api_model_name": self.vl_rec_api_model_name,
            "vl_rec_api_key": self.vl_rec_api_key,
            "doc_orientation_classify_model_name": (
                self.doc_orientation_classify_model_name
            ),
            "doc_orientation_classify_model_dir": (
                self.doc_orientation_classify_model_dir
            ),
            "doc_unwarping_model_name": self.doc_unwarping_model_name,
            "doc_unwarping_model_dir": self.doc_unwarping_model_dir,
            "use_doc_orientation_classify": self.use_doc_orientation_classify,
            "use_doc_unwarping": self.use_doc_unwarping,
            "use_layout_detection": self.use_layout_detection,
            "use_chart_recognition": self.use_chart_recognition,
            "use_seal_recognition": self.use_seal_recognition,
            "use_ocr_for_image_block": self.use_ocr_for_image_block,
            "format_block_content": self.format_block_content,
            "merge_layout_blocks": self.merge_layout_blocks,
            "markdown_ignore_labels": self.markdown_ignore_labels,
            "use_queues": self.use_queues,
        }
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return PaddleOCRVL(**kwargs)

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
        """Extract document structure using PaddleOCRVL.

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

        # Force dynamic graph mode to avoid int(Tensor) in static mode (paddlex)
        import paddle

        paddle.disable_static()

        raw_result = self.pipeline_.predict(str(file_path))

        return PaddleOCRResult(
            raw_result=raw_result,
            file_path=file_path,
            extra_info=extra_info or {},
        ).to_documents()
