import base64
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import List, Optional

from kotaemon.base import Document, Param

from .azureai_document_intelligence_loader import crop_image
from .base import BaseReader
from .utils.adobe import generate_single_figure_caption, make_markdown_table


class DoclingReader(BaseReader):
    """Using Docling to extract document structure and content"""

    _dependencies = ["docling"]

    vlm_endpoint: str = Param(
        help=(
            "Default VLM endpoint for figure captioning. "
            "If not provided, will not caption the figures"
        )
    )

    max_figure_to_caption: int = Param(
        100,
        help=(
            "The maximum number of figures to caption. "
            "The rest will be indexed without captions."
        ),
    )

    figure_friendly_filetypes: list[str] = Param(
        [".pdf", ".jpeg", ".jpg", ".png", ".bmp", ".tiff", ".heif", ".tif"],
        help=(
            "File types that we can reliably open and extract figures. "
            "For files like .docx or .html, the visual layout may be different "
            "when viewed from different tools, hence we cannot use Azure DI location "
            "to extract figures."
        ),
    )

    @Param.auto(cache=True)
    def converter_(self):
        try:
            from docling.document_converter import DocumentConverter
        except ImportError:
            raise ImportError("Please install docling: 'pip install docling'")

        return DocumentConverter()

    def run(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        return self.load_data(file_path, extra_info, **kwargs)

    def load_data(
        self, file_path: str | Path, extra_info: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """Extract the input file, allowing multi-modal extraction"""

        metadata = extra_info or {}

        result = self.converter_.convert(file_path)
        result_dict = result.document.export_to_dict()

        file_path = Path(file_path)
        file_name = file_path.name

        # extract the figures
        figures = []
        gen_caption_count = 0
        for figure_obj in result_dict.get("pictures", []):
            if not self.vlm_endpoint:
                continue
            if file_path.suffix.lower() not in self.figure_friendly_filetypes:
                continue

            # retrieve extractive captions provided by docling
            caption_refs = [caption["$ref"] for caption in figure_obj["captions"]]
            extractive_captions = []
            for caption_ref in caption_refs:
                text_id = caption_ref.split("/")[-1]
                try:
                    caption_text = result_dict["texts"][int(text_id)]["text"]
                    extractive_captions.append(caption_text)
                except (ValueError, TypeError, IndexError) as e:
                    print(e)
                    continue

            # read & crop image
            page_number = figure_obj["prov"][0]["page_no"]

            try:
                page_number_text = str(page_number)
                page_width = result_dict["pages"][page_number_text]["size"]["width"]
                page_height = result_dict["pages"][page_number_text]["size"]["height"]

                bbox_obj = figure_obj["prov"][0]["bbox"]
                bbox: list[float] = [
                    bbox_obj["l"],
                    bbox_obj["t"],
                    bbox_obj["r"],
                    bbox_obj["b"],
                ]
                if bbox_obj["coord_origin"] == "BOTTOMLEFT":
                    bbox = self._convert_bbox_bl_tl(bbox, page_width, page_height)

                img = crop_image(file_path, bbox, page_number - 1)
            except KeyError as e:
                print(e, list(result_dict["pages"].keys()))
                continue

            # convert img to base64
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG")
            img_base64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")
            img_base64 = f"data:image/png;base64,{img_base64}"

            # generate the generative caption
            if gen_caption_count >= self.max_figure_to_caption:
                gen_caption = ""
            else:
                gen_caption_count += 1
                gen_caption = generate_single_figure_caption(
                    figure=img_base64, vlm_endpoint=self.vlm_endpoint
                )

            # join the extractive and generative captions
            caption = "\n".join(extractive_captions + [gen_caption])

            # store the image into document
            figure_metadata = {
                "image_origin": img_base64,
                "type": "image",
                "page_label": page_number,
                "file_name": file_name,
                "file_path": file_path,
            }
            figure_metadata.update(metadata)

            figures.append(
                Document(
                    text=caption,
                    metadata=figure_metadata,
                )
            )

        # extract the tables
        tables = []
        for table_obj in result_dict.get("tables", []):
            # convert the tables into markdown format
            markdown_table = self._parse_table(table_obj)
            caption_refs = [caption["$ref"] for caption in table_obj["captions"]]

            extractive_captions = []
            for caption_ref in caption_refs:
                text_id = caption_ref.split("/")[-1]
                try:
                    caption_text = result_dict["texts"][int(text_id)]["text"]
                    extractive_captions.append(caption_text)
                except (ValueError, TypeError, IndexError) as e:
                    print(e)
                    continue
            # join the extractive and generative captions
            caption = "\n".join(extractive_captions)
            markdown_table = f"{caption}\n{markdown_table}"

            page_number = table_obj["prov"][0].get("page_no", 1)

            table_metadata = {
                "type": "table",
                "page_label": page_number,
                "table_origin": markdown_table,
                "file_name": file_name,
                "file_path": file_path,
            }
            table_metadata.update(metadata)

            tables.append(
                Document(
                    text=markdown_table,
                    metadata=table_metadata,
                )
            )

        # join plain text elements
        texts = []
        page_number_to_text = defaultdict(list)

        for text_obj in result_dict["texts"]:
            page_number = text_obj["prov"][0].get("page_no", 1)
            page_number_to_text[page_number].append(text_obj["text"])

        for page_number, txts in page_number_to_text.items():
            texts.append(
                Document(
                    text="\n".join(txts),
                    metadata={
                        "page_label": page_number,
                        "file_name": file_name,
                        "file_path": file_path,
                        **metadata,
                    },
                )
            )

        return texts + tables + figures

    def _convert_bbox_bl_tl(
        self, bbox: list[float], page_width: int, page_height: int
    ) -> list[float]:
        """Convert bbox from bottom-left to top-left"""
        x0, y0, x1, y1 = bbox
        return [
            x0 / page_width,
            (page_height - y1) / page_height,
            x1 / page_width,
            (page_height - y0) / page_height,
        ]

    def _parse_table(self, table_obj: dict) -> str:
        """Convert docling table object to markdown table"""
        table_as_list: List[List[str]] = []
        grid = table_obj["data"]["grid"]
        for row in grid:
            table_as_list.append([])
            for cell in row:
                table_as_list[-1].append(cell["text"])

        return make_markdown_table(table_as_list)
