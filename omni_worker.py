import sys, os, json
sys.path.insert(0, 'D:/Nodequest/OmniParser')
os.chdir('D:/Nodequest/OmniParser')

import unittest.mock as mock
sys.modules['paddleocr'] = mock.MagicMock()

from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img
from PIL import Image
import torch


def main():
    img_path = sys.argv[1]
    target = sys.argv[2]
    screenshot = Image.open(img_path)
    w, h = screenshot.size

    yolo_model = get_yolo_model(model_path='D:/Nodequest/OmniParser/weights/icon_detect/model.pt')
    caption_processor = get_caption_model_processor(
        model_name='florence2',
        model_name_or_path='D:/Nodequest/OmniParser/weights/icon_caption_florence'
    )

    box_overlay_ratio = w / 3200
    draw_bbox_config = {
        'text_scale': 0.8 * box_overlay_ratio,
        'text_thickness': max(int(2 * box_overlay_ratio), 1),
        'text_padding': max(int(3 * box_overlay_ratio), 1),
        'thickness': max(int(3 * box_overlay_ratio), 1),
    }

    ocr_result, _ = check_ocr_box(
        screenshot, display_img=False, output_bb_format='xyxy',
        goal_filtering=None,
        easyocr_args={'paragraph': False, 'text_threshold': 0.9},
        use_paddleocr=False
    )
    text, ocr_bbox = ocr_result

    _, label_coordinates, parsed_content = get_som_labeled_img(
        screenshot, yolo_model, BOX_TRESHOLD=0.05,
        output_coord_in_ratio=True, ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_bbox_config,
        caption_model_processor=caption_processor,
        ocr_text=text, iou_threshold=0.1, imgsz=640
    )

    target_lower = target.lower()
    best_match = None
    best_score = 0

    for i, element in enumerate(parsed_content):
        if isinstance(element, dict):
            element_text = element.get('content', '').lower()
        else:
            element_text = str(element).lower()
        words = [ww for ww in target_lower.split() if len(ww) > 2]
        if not words:
            continue
        score = sum(1 for ww in words if ww in element_text) / len(words)
        if score > best_score:
            best_score = score
            best_match = i

    if best_match is not None and best_score > 0.3:
        coords_keys = list(label_coordinates.keys())
        key = coords_keys[best_match]
        coords = label_coordinates[key]
        x = float(coords[0]) * w
        y = float(coords[1]) * h
        print(json.dumps({'found': True, 'x': x, 'y': y, 'score': best_score}))
    else:
        print(json.dumps({'found': False}))


main()
