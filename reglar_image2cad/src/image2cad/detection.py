"""
Cell 2 من النوت بوك: تحديد صندوق تقريبي (bounding box) حوالين الجسم في الصورة
باستخدام CLIP بطريقة sliding-window، عشان نستخدمه بعدين كـ box prompt لـ SAM3.
"""
from __future__ import annotations

import logging
import time

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from .config import DetectionConfig

log = logging.getLogger(__name__)


def detect_object_box(image: Image.Image, cfg: DetectionConfig) -> list[float]:
    """يرجع [x1, y1, x2, y2] تقريبي حوالين أكتر منطقة بتشبه أحد الـ prompts."""
    start_time = time.perf_counter()
    model = CLIPModel.from_pretrained(cfg.clip_model_name)
    processor = CLIPProcessor.from_pretrained(cfg.clip_model_name)

    W, H = image.size
    boxes: list[list[int]] = []
    scores: list[float] = []

    for y in range(0, H - cfg.patch_size, cfg.stride):
        for x in range(0, W - cfg.patch_size, cfg.stride):
            patch = image.crop((x, y, x + cfg.patch_size, y + cfg.patch_size))

            inputs = processor(
                text=cfg.prompts, images=patch, return_tensors="pt", padding=True
            )
            with torch.no_grad():
                outputs = model(**inputs)
                probs = outputs.logits_per_image.softmax(dim=1)

            score = probs[0][0].item()  # أول label
            if score > cfg.score_threshold:
                boxes.append([x, y, x + cfg.patch_size, y + cfg.patch_size])
                scores.append(score)

    if not boxes:
        raise RuntimeError(
            "No object detected — جرّب تقلل score_threshold أو تغيّر الـ prompts في config.py"
        )

    x1 = min(b[0] for b in boxes)
    y1 = min(b[1] for b in boxes)
    x2 = max(b[2] for b in boxes)
    y2 = max(b[3] for b in boxes)

    final_box = [x1, y1, x2, y2]
    elapsed = time.perf_counter() - start_time
    print(f"[TIMING] CLIP box generation took {elapsed:.2f} seconds")
    log.info("[TIMING] CLIP box generation took %.2f seconds", elapsed)
    log.info("Final box: %s (من %d patch متطابق)", final_box, len(boxes))
    return final_box
