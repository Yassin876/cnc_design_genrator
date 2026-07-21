"""
Cells 6-7 من النوت بوك: حساب bounding box حقيقي من قناع SAM، وبناء صورة ثنائية
(ink/background) من الصورة الأصلية جوه الـ bbox ده — عشان نحافظ على التفاصيل
الداخلية (الفتحات/الحلقات) اللي قناع SAM بيدمجها في شكل مليان من غير holes.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

from .config import MaskConfig


def bbox_from_mask(mask_np: np.ndarray, pad_px: int = 10) -> list[int]:
    """يحسب bounding box حقيقي من قناع SAM (أدق من صندوق الـ CLIP)."""
    mask_2d = mask_np[0] if mask_np.ndim == 3 else mask_np
    mask_u8 = (mask_2d > 0).astype(np.uint8) * 255
    x, y, w, h = cv2.boundingRect(mask_u8)
    H, W = mask_2d.shape[:2]
    x1 = max(x - pad_px, 0)
    y1 = max(y - pad_px, 0)
    x2 = min(x + w + pad_px, W)
    y2 = min(y + h + pad_px, H)
    return [x1, y1, x2, y2]


def build_trace_source_from_image(
    image: Image.Image, bbox: list[float] | None, cfg: MaskConfig
) -> np.ndarray:
    """
    يبني مصفوفة ثنائية للتتبع من الصورة الأصلية (مش من قناع SAM)، عشان يحافظ
    على كل التفاصيل الداخلية اللي قناع SAM المليان بيفقدها.
    """
    gray = np.array(image.convert("L"))

    if bbox is not None:
        x1, y1, x2, y2 = [int(v) for v in bbox]
        crop = gray[y1:y2, x1:x2]
    else:
        crop = gray

    if cfg.use_otsu:
        _, ink = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        _, ink = cv2.threshold(crop, cfg.manual_thresh, 255, cv2.THRESH_BINARY_INV)

    return ink  # ink = 255 حيث فيه خط، و0 في الخلفية
