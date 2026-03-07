"""PaddleOCRVL document loader and result adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from kotaemon.base import Document, Param
from kotaemon.loaders.base import BaseReader

from .adapter import PaddleOCRResult


@dataclass
class PaddleOCRVLResult(PaddleOCRResult):
    """Adapter for PaddleOCRVL results.

    PaddleOCRVL uses vision-language models for OCR with:
    - Layout detection with polygon points
    - Merged layout blocks
    - Better handling of complex layouts
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
        """Convert PaddleOCRVL results to Documents."""
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
        """Parse a single page result from PaddleOCRVL."""
        parsing_list = result_dict.get("parsing_res_list", [])

        text_blocks: list[str] = []
        tables: list[Document] = []
        figures: list[Document] = []

        for block in parsing_list:
            label = block.get("block_label", "")
            content = block.get("block_content", "")

            if not content:
                continue

            bbox = block.get("block_bbox")
            polygon = block.get("block_polygon_points")

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
                            "bbox": bbox,
                            "polygon": polygon,
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
                            "bbox": bbox,
                            "polygon": polygon,
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


class PaddleOCRVLReader(BaseReader):
    """Document reader using PaddleOCR Vision-Language model.

    PaddleOCRVL uses vision-language models for enhanced OCR with better
    understanding of complex document layouts.

    Example:
        ```python
        from kotaemon.loaders import PaddleOCRVLReader

        # GPU mode (default)
        reader = PaddleOCRVLReader()
        documents = reader.load_data("path/to/image.png")

        # CPU mode
        reader = PaddleOCRVLReader(device="cpu")
        ```

    Args:
        device: Device for inference - "gpu:0", "cpu", "npu:0", "xpu:0"
    """

    _dependencies = ["paddleocr"]

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
                "Please install paddleocr: 'pip install \"paddleocr[all]\"'"
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

        raw_result = self.pipeline_.predict(str(file_path))

        result = PaddleOCRVLResult(
            raw_result=raw_result,
            file_path=file_path,
            extra_info=extra_info or {},
        )

        return result.to_documents()
