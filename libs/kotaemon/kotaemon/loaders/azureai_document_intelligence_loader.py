import base64
import os
from io import BytesIO
from pathlib import Path
from typing import Optional

import fitz
from PIL import Image

from kotaemon.base import Document, Param

from .base import BaseReader
from .utils.adobe import generate_single_figure_caption


def crop_image(file_path: Path, bbox: list[float], page_number: int = 0) -> Image.Image:
    """Crop the image based on the bounding box

    Args:
        file_path (Path): path to the image file
        bbox (list[float]): bounding box of the image (in percentage [x0, y0, x1, y1])
        page_number (int, optional): page number of the image. Defaults to 0.

    Returns:
        Image.Image: cropped image
    """
    left, upper, right, lower = bbox

    img: Image.Image
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        doc = fitz.open(file_path)
        page = doc.load_page(page_number)
        pm = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
    elif suffix in [".tif", ".tiff"]:
        img = Image.open(file_path)
        img.seek(page_number)
    else:
        img = Image.open(file_path)

    return img.crop(
        (
            int(left * img.width),
            int(upper * img.height),
            int(right * img.width),
            int(lower * img.height),
        )
    )


class AzureAIDocumentIntelligenceLoader(BaseReader):
    """Utilize Azure AI Document Intelligence to parse document

    As of April 24, the supported file formats are: pdf, jpeg/jpg, png, bmp, tiff,
    heif, docx, xlsx, pptx and html.
    """

    _dependencies = ["azure-ai-documentintelligence", "PyMuPDF", "Pillow"]

    endpoint: str = Param(
        os.environ.get("AZUREAI_DOCUMENT_INTELLIGENT_ENDPOINT", None),
        help="Endpoint of Azure AI Document Intelligence",
    )
    credential: str = Param(
        os.environ.get("AZUREAI_DOCUMENT_INTELLIGENT_CREDENTIAL", None),
        help="Credential of Azure AI Document Intelligence",
    )
    model: str = Param(
        "prebuilt-layout",
        help=(
            "Model to use for document analysis. Default is prebuilt-layout. "
            "As of April 24, you can view the supported models [here]"
            "(https://learn.microsoft.com/en-us/azure/ai-services/"
            "document-intelligence/concept-model-overview?view=doc-intel-4.0.0"
            "#model-analysis-features)"
        ),
    )
    output_content_format: str = Param(
        "markdown",
        help="Output content format. Can be 'markdown' or 'text'.Default is markdown",
    )
    vlm_endpoint: str = Param(
        help=(
            "Default VLM endpoint for figure captioning. If not provided, will not "
            "caption the figures"
        )
    )
    figure_friendly_filetypes: list[str] = Param(
        [".pdf", ".jpeg", ".jpg", ".png", ".bmp", ".tiff", ".heif", ".tif"],
        help=(
            "File types that we can reliably open and extract figures. "
            "For files like .docx or .html, the visual layout may be different "
            "when viewed from different tools, hence we cannot use Azure DI "
            "location to extract figures."
        ),
    )

    @Param.auto(depends_on=["endpoint", "credential"])
    def client_(self):
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError:
            raise ImportError("Please install azure-ai-documentintelligence")

        return DocumentIntelligenceClient(
            self.endpoint, AzureKeyCredential(self.credential)
        )

    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        return self.load_data(Path(file_path), extra_info=extra_info, **kwargs)

    def load_data(
        self, file_path: Path, extra_info: Optional[dict] = None, **kwargs
    ) -> list[Document]:
        """Extract the input file, allowing multi-modal extraction"""
        metadata = extra_info or {}
        with open(file_path, "rb") as fi:
            poller = self.client_.begin_analyze_document(
                self.model,
                analyze_request=fi,
                content_type="application/octet-stream",
                output_content_format=self.output_content_format,
            )
            result = poller.result()

        # the total text content of the document in `output_content_format` format
        text_content = result.content
        removed_spans: list[dict] = []

        # extract the figures
        figures = []
        for figure_desc in result.get("figures", []):
            if not self.vlm_endpoint:
                continue
            if file_path.suffix.lower() not in self.figure_friendly_filetypes:
                continue

            # read & crop the image
            page_number = figure_desc["boundingRegions"][0]["pageNumber"]
            page_width = result.pages[page_number - 1]["width"]
            page_height = result.pages[page_number - 1]["height"]
            bbox = [
                figure_desc["boundingRegions"][0]["polygon"][0] / page_width,
                figure_desc["boundingRegions"][0]["polygon"][1] / page_height,
                figure_desc["boundingRegions"][0]["polygon"][4] / page_width,
                figure_desc["boundingRegions"][0]["polygon"][5] / page_height,
            ]
            img = crop_image(file_path, bbox, page_number - 1)

            # convert the image into base64
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG")
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            img_base64 = f"data:image/png;base64,{img_base64}"

            # caption the image
            caption = generate_single_figure_caption(
                figure=img_base64, vlm_endpoint=self.vlm_endpoint
            )

            # store the image into document
            figure_metadata = {
                "image_origin": img_base64,
                "type": "image",
                "page_label": page_number,
            }
            figure_metadata.update(metadata)

            figures.append(
                Document(
                    text=caption,
                    metadata=figure_metadata,
                )
            )
            removed_spans += figure_desc["spans"]

        # extract the tables
        tables = []
        for table_desc in result.get("tables", []):
            # convert the tables into markdown format
            table_metadata = {
                "type": "table",
                "page_label": table_desc["boundingRegions"][0],
            }
            table_metadata.update(metadata)

            # store the tables into document
            offset = table_desc["spans"][0]["offset"]
            length = table_desc["spans"][0]["length"]
            tables.append(
                Document(
                    text=text_content[offset : offset + length],
                    metadata=table_metadata,
                )
            )
            removed_spans += table_desc["spans"]

        removed_spans = sorted(removed_spans, key=lambda x: x["offset"], reverse=True)
        for span in removed_spans:
            text_content = (
                text_content[: span["offset"]]
                + text_content[span["offset"] + span["length"] :]
            )

        return [Document(content=text_content, metadata=metadata)] + figures + tables
