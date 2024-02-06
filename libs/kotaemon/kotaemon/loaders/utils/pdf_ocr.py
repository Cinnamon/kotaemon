from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Union

from .box import (
    bbox_to_points,
    box_area,
    box_h,
    box_w,
    get_rect_iou,
    points_to_bbox,
    scale_box,
    scale_points,
    sort_funsd_reading_order,
    union_points,
)
from .table import table_cells_to_markdown

IOU_THRES = 0.5
PADDING_THRES = 1.1


def read_pdf_unstructured(input_path: Union[Path, str]):
    """Convert PDF from specified path to list of text items with
    location information

    Args:
        input_path: path to input file

    Returns:
        Dict page_number: list of text boxes
    """
    try:
        from unstructured.partition.auto import partition
    except ImportError as e:
        raise ImportError(
            "Please install unstructured PDF reader `pip install unstructured[pdf]`: "
            f"{e}"
        )

    page_items = defaultdict(list)
    items = partition(input_path)
    for item in items:
        page_number = item.metadata.page_number
        bbox = points_to_bbox(item.metadata.coordinates.points)
        coord_system = item.metadata.coordinates.system
        max_w, max_h = coord_system.width, coord_system.height
        page_items[page_number - 1].append(
            {
                "text": item.text,
                "box": bbox,
                "location": bbox_to_points(bbox),
                "page_shape": (max_w, max_h),
            }
        )

    return page_items


def merge_ocr_and_pdf_texts(
    ocr_list: List[dict], pdf_text_list: List[dict], debug_info=None
):
    """Merge PDF and OCR text using IOU overlapping location
    Args:
        ocr_list: List of OCR items {"text", "box", "location"}
        pdf_text_list: List of PDF items {"text", "box", "location"}

    Returns:
        Combined list of PDF text and non-overlap OCR text
    """
    not_matched_ocr = []

    # check for debug info
    if debug_info is not None:
        cv2, debug_im = debug_info

    for ocr_item in ocr_list:
        matched = False
        for pdf_item in pdf_text_list:
            if (
                get_rect_iou(ocr_item["location"], pdf_item["location"], iou_type=1)
                > IOU_THRES
            ):
                matched = True
                break

        color = (255, 0, 0)
        if not matched:
            ocr_item["matched"] = False
            not_matched_ocr.append(ocr_item)
            color = (0, 255, 255)

        if debug_info is not None:
            cv2.rectangle(
                debug_im,
                ocr_item["location"][0],
                ocr_item["location"][2],
                color=color,
                thickness=1,
            )

    if debug_info is not None:
        for pdf_item in pdf_text_list:
            cv2.rectangle(
                debug_im,
                pdf_item["location"][0],
                pdf_item["location"][2],
                color=(0, 255, 0),
                thickness=2,
            )

    return pdf_text_list + not_matched_ocr


def merge_table_cell_and_ocr(
    table_list: List[dict], ocr_list: List[dict], pdf_list: List[dict], debug_info=None
):
    """Merge table items with OCR text using IOU overlapping location
    Args:
        table_list: List of table items
            "type": ("table", "cell", "text"), "text", "box", "location"}
        ocr_list: List of OCR items {"text", "box", "location"}
        pdf_list: List of PDF items {"text", "box", "location"}

    Returns:
        all_table_cells: List of tables, each of table is represented
            by list of cells with combined text from OCR
        not_matched_items: List of PDF text which is not overlapped by table region
    """
    # check for debug info
    if debug_info is not None:
        cv2, debug_im = debug_info

    cell_list = [item for item in table_list if item["type"] == "cell"]
    table_list = [item for item in table_list if item["type"] == "table"]

    # sort table by area
    table_list = sorted(table_list, key=lambda item: box_area(item["bbox"]))

    all_tables = []
    matched_pdf_ids = []
    matched_cell_ids = []

    for table in table_list:
        if debug_info is not None:
            cv2.rectangle(
                debug_im,
                table["location"][0],
                table["location"][2],
                color=[0, 0, 255],
                thickness=5,
            )

        cur_table_cells = []
        for cell_id, cell in enumerate(cell_list):
            if cell_id in matched_cell_ids:
                continue

            if get_rect_iou(
                table["location"], cell["location"], iou_type=1
            ) > IOU_THRES and box_area(table["bbox"]) > box_area(cell["bbox"]):
                color = [128, 0, 128]
                # cell matched to table
                for item_list, item_type in [(pdf_list, "pdf"), (ocr_list, "ocr")]:
                    cell["ocr"] = []
                    for item_id, item in enumerate(item_list):
                        if item_type == "pdf" and item_id in matched_pdf_ids:
                            continue
                        if (
                            get_rect_iou(item["location"], cell["location"], iou_type=1)
                            > IOU_THRES
                        ):
                            cell["ocr"].append(item)
                            if item_type == "pdf":
                                matched_pdf_ids.append(item_id)

                    if len(cell["ocr"]) > 0:
                        # check if union of matched ocr does
                        # not extend over cell boundary,
                        # if True, continue to use OCR_list to match
                        all_box_points_in_cell = []
                        for item in cell["ocr"]:
                            all_box_points_in_cell.extend(item["location"])
                        union_box = union_points(all_box_points_in_cell)
                        cell_okay = (
                            box_h(union_box) <= box_h(cell["bbox"]) * PADDING_THRES
                            and box_w(union_box) <= box_w(cell["bbox"]) * PADDING_THRES
                        )
                    else:
                        cell_okay = False

                    if cell_okay:
                        if item_type == "pdf":
                            color = [255, 0, 255]
                        break

                if debug_info is not None:
                    cv2.rectangle(
                        debug_im,
                        cell["location"][0],
                        cell["location"][2],
                        color=color,
                        thickness=3,
                    )

                matched_cell_ids.append(cell_id)
                cur_table_cells.append(cell)

        all_tables.append(cur_table_cells)

    not_matched_items = [
        item for _id, item in enumerate(pdf_list) if _id not in matched_pdf_ids
    ]
    if debug_info is not None:
        for item in not_matched_items:
            cv2.rectangle(
                debug_im,
                item["location"][0],
                item["location"][2],
                color=[128, 128, 128],
                thickness=3,
            )

    return all_tables, not_matched_items


def parse_ocr_output(
    ocr_page_items: List[dict],
    pdf_page_items: Dict[int, List[dict]],
    artifact_path: Optional[str] = None,
    debug_path: Optional[str] = None,
):
    """Main function to combine OCR output and PDF text to
    form list of table / non-table regions
    Args:
        ocr_page_items: List of OCR items by page
        pdf_page_items: Dict of PDF texts (page number as key)
        debug_path: If specified, use OpenCV to plot debug image and save to debug_path
    """
    all_tables = []
    all_texts = []

    for page_id, page in enumerate(ocr_page_items):
        ocr_list = page["json"]["ocr"]
        table_list = page["json"]["table"]
        page_shape = page["image_shape"]
        pdf_item_list = pdf_page_items[page_id]

        # create bbox additional information
        for item in ocr_list:
            item["box"] = points_to_bbox(item["location"])

        # re-scale pdf items according to new image size
        for item in pdf_item_list:
            scale_factor = page_shape[0] / item["page_shape"][0]
            item["box"] = scale_box(item["box"], scale_factor=scale_factor)
            item["location"] = scale_points(item["location"], scale_factor=scale_factor)

        # if using debug mode, openCV must be installed
        if debug_path and artifact_path is not None:
            try:
                import cv2
            except ImportError:
                raise ImportError(
                    "Please install openCV first to use OCRReader debug mode"
                )
            image_path = Path(artifact_path) / page["image"]
            image = cv2.imread(str(image_path))
            debug_info = (cv2, image)
        else:
            debug_info = None

        new_pdf_list = merge_ocr_and_pdf_texts(
            ocr_list, pdf_item_list, debug_info=debug_info
        )

        # sort by reading order
        ocr_list = sort_funsd_reading_order(ocr_list)
        new_pdf_list = sort_funsd_reading_order(new_pdf_list)

        all_table_cells, non_table_text_list = merge_table_cell_and_ocr(
            table_list, ocr_list, new_pdf_list, debug_info=debug_info
        )

        table_texts = [table_cells_to_markdown(cells) for cells in all_table_cells]
        all_tables.extend([(page_id, text) for text in table_texts])
        all_texts.append(
            (page_id, " ".join(item["text"] for item in non_table_text_list))
        )

        # export debug image to debug_path
        if debug_path:
            cv2.imwrite(str(Path(debug_path) / "page_{}.png".format(page_id)), image)

    return all_tables, all_texts
