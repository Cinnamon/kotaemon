import base64
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from fsspec import AbstractFileSystem
from llama_index.readers.file import PDFReader
from PIL import Image

from kotaemon.base import Document


def get_page_thumbnails(
    file_path: Path, pages: list[int], dpi: int = 80
) -> List[Image.Image]:
    """Get image thumbnails of the pages in the PDF file.

    Args:
        file_path (Path): path to the image file
        page_number (list[int]): list of page numbers to extract

    Returns:
        list[Image.Image]: list of page thumbnails
    """

    img: Image.Image
    suffix = file_path.suffix.lower()
    assert suffix == ".pdf", "This function only supports PDF files."
    try:
        import fitz
    except ImportError:
        raise ImportError("Please install PyMuPDF: 'pip install PyMuPDF'")

    doc = fitz.open(file_path)

    output_imgs = []
    for page_number in pages:
        page = doc.load_page(page_number)
        pm = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
        output_imgs.append(convert_image_to_base64(img))

    return output_imgs


def convert_image_to_base64(img: Image.Image) -> str:
    # convert the image into base64
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
    img_base64 = f"data:image/png;base64,{img_base64}"

    return img_base64


class PDFThumbnailReader(PDFReader):
    """PDF parser with thumbnail for each page."""

    def __init__(self) -> None:
        """
        Initialize PDFReader.
        """
        super().__init__(return_full_document=False)

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Parse file."""
        documents = super().load_data(file, extra_info, fs)

        page_numbers_int = []
        filtered_docs = []
        for doc in documents:
            if "page_label" in doc.metadata:
                page_num_str = doc.metadata["page_label"]
                try:
                    p_num = int(page_num_str) - 1
                    page_numbers_int.append(p_num)
                    filtered_docs.append(doc)
                except ValueError:
                    continue

        documents = filtered_docs
        page_numbers = list(set(page_numbers_int))
        print("Page numbers:", len(page_numbers))
        page_thumbnails = get_page_thumbnails(file, page_numbers)

        documents.extend(
            [
                Document(
                    text="Page thumbnail",
                    metadata={
                        "image_origin": page_thumbnail,
                        "type": "thumbnail",
                        "page_label": str(page_number + 1),
                        **(extra_info if extra_info is not None else {}),
                    },
                )
                for (page_thumbnail, page_number) in zip(page_thumbnails, page_numbers)
            ]
        )

        return documents
