"""
الأوركستريتور: بيشغّل كل مراحل النوت بوك بالترتيب (detection -> segmentation ->
mask -> vectorize -> kerf -> dxf -> preview) كدالة بايثون عادية بدل خلايا منفصلة.
"""
from __future__ import annotations

import logging

from PIL import Image

from .config import PipelineConfig
from .detection import detect_object_box
from .dxf_export import build_dxf_from_potrace
from .mask_utils import bbox_from_mask, build_trace_source_from_image
from .preview import render_dxf_preview
from .segmentation import load_sam3, segment_object

log = logging.getLogger(__name__)


def run(cfg: PipelineConfig, skip_preview: bool = False):
    image = Image.open(cfg.input_image).convert("RGB")
    log.info("Loaded image: %s (%dx%d)", cfg.input_image, *image.size)

    # 1) CLIP sliding-window box (cell 2)
    box = detect_object_box(image, cfg.detection)

    # 2) SAM3 segmentation (cells 3-5)
    sam_processor = load_sam3(cfg.segmentation)
    mask_np = segment_object(image, box, sam_processor, cfg.segmentation)

    # 3) bbox حقيقي من القناع + صورة ثنائية للتتبع (cells 6-7)
    real_box = bbox_from_mask(mask_np, pad_px=cfg.mask.bbox_pad_px)
    log.info("Bounding box المستخدم: %s", real_box)
    trace_source = build_trace_source_from_image(image, bbox=real_box, cfg=cfg.mask)

    # 4-6) Potrace vectorize -> kerf -> DXF (cells 9-11)
    cfg.output_dxf.parent.mkdir(parents=True, exist_ok=True)
    doc = build_dxf_from_potrace(
        mask_np=trace_source,
        machine=cfg.machine,
        vectorize_cfg=cfg.vectorize,
        kerf_cfg=cfg.kerf,
        output_path=str(cfg.output_dxf),
        entity_type=cfg.entity_type,
    )

    if doc is None:
        log.error("الـ pipeline فشل: مفيش كونتورات اتلاقت.")
        return None

    msp = doc.modelspace()
    log.info("DXF entities in modelspace: %d", len(list(msp)))

    # 7) preview (cell 14)
    if not skip_preview:
        cfg.output_preview.parent.mkdir(parents=True, exist_ok=True)
        render_dxf_preview(str(cfg.output_dxf), str(cfg.output_preview))

    return doc
