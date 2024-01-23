from typing import List, Tuple


def bbox_to_points(box: List[int]):
    """Convert bounding box to list of points"""
    x1, y1, x2, y2 = box
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def points_to_bbox(points: List[Tuple[int, int]]):
    """Convert list of points to bounding box"""
    all_x = [p[0] for p in points]
    all_y = [p[1] for p in points]
    return [min(all_x), min(all_y), max(all_x), max(all_y)]


def scale_points(points: List[Tuple[int, int]], scale_factor: float = 1.0):
    """Scale points by a scale factor"""
    return [(int(pos[0] * scale_factor), int(pos[1] * scale_factor)) for pos in points]


def union_points(points: List[Tuple[int, int]]):
    """Return union bounding box of list of points"""
    all_x = [p[0] for p in points]
    all_y = [p[1] for p in points]
    bbox = (min(all_x), min(all_y), max(all_x), max(all_y))
    return bbox


def scale_box(box: List[int], scale_factor: float = 1.0):
    """Scale box by a scale factor"""
    return [int(pos * scale_factor) for pos in box]


def box_h(box: List[int]):
    "Return box height"
    return box[3] - box[1]


def box_w(box: List[int]):
    "Return box width"
    return box[2] - box[0]


def box_area(box: List[int]):
    "Return box area"
    x1, y1, x2, y2 = box
    return (x2 - x1) * (y2 - y1)


def get_rect_iou(gt_box: List[tuple], pd_box: List[tuple], iou_type=0) -> int:
    """Intersection over union on layout rectangle

    Args:
        gt_box: List[tuple]
            A list contains bounding box coordinates of ground truth
        pd_box: List[tuple]
            A list contains bounding box coordinates of prediction
        iou_type: int
            0: intersection / union, normal IOU
            1: intersection / min(areas), useful when boxes are under/over-segmented

        Input format: [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        Annotation for each element in bbox:
        (x1, y1)        (x2, y1)
            +-------+
            |       |
            |       |
            +-------+
        (x1, y2)        (x2, y2)

    Returns:
        Intersection over union value
    """

    assert iou_type in [0, 1], "Only support 0: origin iou, 1: intersection / min(area)"

    # determine the (x, y)-coordinates of the intersection rectangle
    # gt_box: [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    # pd_box: [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
    x_left = max(gt_box[0][0], pd_box[0][0])
    y_top = max(gt_box[0][1], pd_box[0][1])
    x_right = min(gt_box[2][0], pd_box[2][0])
    y_bottom = min(gt_box[2][1], pd_box[2][1])

    # compute the area of intersection rectangle
    interArea = max(0, x_right - x_left) * max(0, y_bottom - y_top)

    # compute the area of both the prediction and ground-truth
    # rectangles
    gt_area = (gt_box[2][0] - gt_box[0][0]) * (gt_box[2][1] - gt_box[0][1])
    pd_area = (pd_box[2][0] - pd_box[0][0]) * (pd_box[2][1] - pd_box[0][1])

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the intersection area
    if iou_type == 0:
        iou = interArea / float(gt_area + pd_area - interArea)
    elif iou_type == 1:
        iou = interArea / max(min(gt_area, pd_area), 1)

    # return the intersection over union value
    return iou


def sort_funsd_reading_order(lines: List[dict], box_key_name: str = "box"):
    """Sort cell list to create the right reading order using their locations

    Args:
        lines: list of cells to sort

    Returns:
        a list of cell lists in the right reading order that contain
        no key or start with a key and contain no other key
    """
    sorted_list = []

    if len(lines) == 0:
        return lines

    while len(lines) > 1:
        topleft_line = lines[0]
        for line in lines[1:]:
            topleft_line_pos = topleft_line[box_key_name]
            topleft_line_center_y = (topleft_line_pos[1] + topleft_line_pos[3]) / 2
            x1, y1, x2, y2 = line[box_key_name]
            box_center_x = (x1 + x2) / 2
            box_center_y = (y1 + y2) / 2
            cell_h = y2 - y1
            if box_center_y <= topleft_line_center_y - cell_h / 2:
                topleft_line = line
                continue
            if (
                box_center_x < topleft_line_pos[2]
                and box_center_y < topleft_line_pos[3]
            ):
                topleft_line = line
                continue
        sorted_list.append(topleft_line)
        lines.remove(topleft_line)

    sorted_list.append(lines[0])

    return sorted_list
