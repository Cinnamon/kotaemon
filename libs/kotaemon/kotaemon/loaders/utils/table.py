import csv
from io import StringIO
from typing import List, Optional, Tuple

from .box import get_rect_iou


def check_col_conflicts(
    col_a: List[str], col_b: List[str], thres: float = 0.15
) -> bool:
    """Check if 2 columns A and B has non-empty content in the same row
    (to be used with merge_cols)

    Args:
        col_a: column A (list of str)
        col_b: column B (list of str)
        thres: percentage of overlapping allowed
    Returns:
        if number of overlapping greater than threshold
    """
    num_rows = len([cell for cell in col_a if cell])
    assert len(col_a) == len(col_b)
    conflict_count = 0
    for cell_a, cell_b in zip(col_a, col_b):
        if cell_a and cell_b:
            conflict_count += 1
    return conflict_count > num_rows * thres


def merge_cols(col_a: List[str], col_b: List[str]) -> List[str]:
    """Merge column A and B if they do not have conflict rows

    Args:
        col_a: column A (list of str)
        col_b: column B (list of str)
    Returns:
        merged column
    """
    for r_id in range(len(col_a)):
        if col_b[r_id]:
            col_a[r_id] = col_a[r_id] + " " + col_b[r_id]
    return col_a


def add_index_col(csv_rows: List[List[str]]) -> List[List[str]]:
    """Add index column as the first column of the table csv_rows

    Args:
        csv_rows: input table
    Returns:
        output table with index column
    """
    new_csv_rows = [["row id"] + [""] * len(csv_rows[0])]
    for r_id, row in enumerate(csv_rows):
        new_csv_rows.append([str(r_id + 1)] + row)
    return new_csv_rows


def compress_csv(csv_rows: List[List[str]]) -> List[List[str]]:
    """Compress table csv_rows by merging sparse columns (merge_cols)

    Args:
        csv_rows: input table
    Returns:
        output: compressed table
    """
    csv_cols = [[r[c_id] for r in csv_rows] for c_id in range(len(csv_rows[0]))]
    to_remove_col_ids = []
    last_c_id = 0
    for c_id in range(1, len(csv_cols)):
        if not check_col_conflicts(csv_cols[last_c_id], csv_cols[c_id]):
            to_remove_col_ids.append(c_id)
            csv_cols[last_c_id] = merge_cols(csv_cols[last_c_id], csv_cols[c_id])
        else:
            last_c_id = c_id

    csv_cols = [r for c_id, r in enumerate(csv_cols) if c_id not in to_remove_col_ids]
    csv_rows = [[c[r_id] for c in csv_cols] for r_id in range(len(csv_cols[0]))]
    return csv_rows


def get_table_from_ocr(ocr_list: List[dict], table_list: List[dict]):
    """Get list of text lines belong to table regions specified by table_list

    Args:
        ocr_list: list of OCR output in Casia format (Flax)
        table_list: list of table output in Casia format (Flax)

    Returns:
        _type_: _description_
    """
    table_texts = []
    for table in table_list:
        if table["type"] != "table":
            continue
        cur_table_texts = []
        for ocr in ocr_list:
            _iou = get_rect_iou(table["location"], ocr["location"], iou_type=1)
            if _iou > 0.8:
                cur_table_texts.append(ocr["text"])
        table_texts.append(cur_table_texts)

    return table_texts


def make_markdown_table(array: List[List[str]]) -> str:
    """Convert table rows in list format to markdown string

    Args:
        Python list with rows of table as lists
        First element as header.
        Example Input:
                [["Name", "Age", "Height"],
                ["Jake", 20, 5'10],
                ["Mary", 21, 5'7]]
    Returns:
        String to put into a .md file
    """
    array = compress_csv(array)
    array = add_index_col(array)
    markdown = "\n" + str("| ")

    for e in array[0]:
        to_add = " " + str(e) + str(" |")
        markdown += to_add
    markdown += "\n"

    markdown += "| "
    for i in range(len(array[0])):
        markdown += str("--- | ")
    markdown += "\n"

    for entry in array[1:]:
        markdown += str("| ")
        for e in entry:
            to_add = str(e) + str(" | ")
            markdown += to_add
        markdown += "\n"

    return markdown + "\n"


def parse_csv_string_to_list(csv_str: str) -> List[List[str]]:
    """Convert CSV string to list of rows

    Args:
        csv_str: input CSV string

    Returns:
        Output table in list format
    """
    io = StringIO(csv_str)
    csv_reader = csv.reader(io, delimiter=",")
    rows = [row for row in csv_reader]
    return rows


def format_cell(cell: str, length_limit: Optional[int] = None) -> str:
    """Format cell content by remove redundant character and enforce length limit

    Args:
        cell: input cell text
        length_limit: limit of text length.

    Returns:
        new cell text
    """
    cell = cell.replace("\n", " ")
    if length_limit:
        cell = cell[:length_limit]
    return cell


def extract_tables_from_csv_string(
    csv_content: str, table_texts: List[List[str]]
) -> Tuple[List[str], str]:
    """Extract list of table from FullOCR output
    (csv_content) with the specified table_texts

    Args:
        csv_content: CSV output from FullOCR pipeline
        table_texts: list of table texts extracted
        from get_table_from_ocr()

    Returns:
        List of tables and non-text content
    """
    rows = parse_csv_string_to_list(csv_content)
    used_row_ids = []
    table_csv_list = []
    for table in table_texts:
        cur_rows = []
        for row_id, row in enumerate(rows):
            scores = [
                any(cell in cell_reference for cell in table)
                for cell_reference in row
                if cell_reference
            ]
            score = sum(scores) / len(scores)
            if score > 0.5 and row_id not in used_row_ids:
                used_row_ids.append(row_id)
                cur_rows.append([format_cell(cell) for cell in row])
        if cur_rows:
            table_csv_list.append(make_markdown_table(cur_rows))
        else:
            print("table not matched", table)

    non_table_rows = [
        row for row_id, row in enumerate(rows) if row_id not in used_row_ids
    ]
    non_table_text = "\n".join(
        " ".join(format_cell(cell) for cell in row) for row in non_table_rows
    )
    return table_csv_list, non_table_text


def strip_special_chars_markdown(text: str) -> str:
    """Strip special characters from input text in markdown table format"""
    return text.replace("|", "").replace(":---:", "").replace("---", "")


def parse_markdown_text_to_tables(text: str) -> Tuple[List[str], List[str]]:
    """Convert markdown text to list of non-table spans and table spans

    Args:
        text: input markdown text

    Returns:
        list of table spans and non-table spans
    """
    # init empty tables and texts list
    tables = []
    texts = []

    # split input by line break
    lines = text.split("\n")
    cur_table = []
    cur_text: List[str] = []
    for line in lines:
        line = line.strip()
        if line.startswith("|"):
            if len(cur_text) > 0:
                texts.append(cur_text)
                cur_text = []
            cur_table.append(line)
        else:
            # add new table to the list
            if len(cur_table) > 0:
                tables.append(cur_table)
                cur_table = []
            cur_text.append(line)

    table_texts = ["\n".join(table) for table in tables]
    non_table_texts = ["\n".join(text) for text in texts]
    return table_texts, non_table_texts


def table_cells_to_markdown(cells: List[dict]):
    """Convert list of cells with attached text to Markdown table"""

    if len(cells) == 0:
        return ""

    all_row_ids = []
    all_col_ids = []
    for cell in cells:
        all_row_ids.extend(cell["rows"])
        all_col_ids.extend(cell["columns"])

    num_rows, num_cols = max(all_row_ids) + 1, max(all_col_ids) + 1
    table_rows = [["" for c in range(num_cols)] for r in range(num_rows)]

    # start filling in the grid
    for cell in cells:
        cell_text = " ".join(item["text"] for item in cell["ocr"])
        start_row_id, end_row_id = cell["rows"]
        start_col_id, end_col_id = cell["columns"]
        span_cell = end_row_id != start_row_id or end_col_id != start_col_id

        # do not repeat long text in span cell to prevent context length issue
        if span_cell and len(cell_text.replace(" ", "")) < 20 and start_row_id > 0:
            for row in range(start_row_id, end_row_id + 1):
                for col in range(start_col_id, end_col_id + 1):
                    table_rows[row][col] += cell_text + " "
        else:
            table_rows[start_row_id][start_col_id] += cell_text + " "

    return make_markdown_table(table_rows)
