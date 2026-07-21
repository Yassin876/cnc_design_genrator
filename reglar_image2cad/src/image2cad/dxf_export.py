"""
Cell 11 من النوت بوك: تجميع خطوات Potrace tracing + kerf compensation + بناء
ملف DXF فعلي (LWPOLYLINE أو SPLINE) بمقاسات حقيقية بالمليمتر.
"""
from __future__ import annotations

import logging

import ezdxf
import numpy as np

from .config import KerfConfig, MachineConfig, VectorizeConfig
from .kerf import apply_kerf_compensation
from .vectorize import curve_to_polyline, mask_to_potrace_path

log = logging.getLogger(__name__)


def build_dxf_from_potrace(
    mask_np: np.ndarray,
    machine: MachineConfig,
    vectorize_cfg: VectorizeConfig,
    kerf_cfg: KerfConfig,
    output_path: str = "output_cnc.dxf",
    entity_type: str = "lwpolyline",  # "lwpolyline" أو "spline"
):
    log.info("=" * 55)
    log.info("    CNC DXF Pipeline — Potrace Mode")
    log.info("=" * 55)

    mask_2d = mask_np[0] if mask_np.ndim == 3 else mask_np

    # STEP 1 — Potrace Vectorization
    log.info("Step 1 — Potrace tracing ...")
    path = mask_to_potrace_path(mask_2d, vectorize_cfg)
    curves = list(path)
    if len(curves) == 0:
        log.warning("Potrace متلاقاش أي كونتور في القناع ده.")
        return None
    log.info("عدد الكونتورات (Curves): %d", len(curves))

    polylines_px = [
        np.array(curve_to_polyline(c, vectorize_cfg.bezier_steps)) for c in curves
    ]
    all_pts = np.vstack(polylines_px)

    x_min, y_min = all_pts[:, 0].min(), all_pts[:, 1].min()
    x_max, y_max = all_pts[:, 0].max(), all_pts[:, 1].max()
    w_b = max(x_max - x_min, 1)
    h_b = max(y_max - y_min, 1)

    scale = min(machine.part_width_mm / w_b, machine.part_height_mm / h_b)
    margin = machine.margin_mm

    log.info("Scale        : %.5f mm/px", scale)
    log.info("Part size    : %.1f x %.1f mm", w_b * scale, h_b * scale)
    log.info("Tool diameter: %s mm", machine.tool_diameter_mm)
    log.info("عدد الكونتورات: %d", len(polylines_px))

    # STEP 2 — (اختياري) تعويض قطر الأداة (Kerf)
    if kerf_cfg.apply_kerf:
        log.info("Step 2 — Kerf compensation ...")
        polylines_px = [
            apply_kerf_compensation(
                pl, machine.tool_diameter_mm, scale, is_internal=kerf_cfg.is_internal
            )
            for pl in polylines_px
        ]

    # STEP 3 — بناء ملف الـ DXF
    log.info("Step 3 — Building DXF ...")
    doc = ezdxf.new(dxfversion="R2010")
    doc.units = ezdxf.units.MM
    if "CUT" not in doc.layers:
        doc.layers.add(name="CUT", color=1)
    msp = doc.modelspace()

    def px_to_mm(pt):
        x_mm = (pt[0] - x_min) * scale + margin
        y_mm = (y_max - pt[1]) * scale + margin  # نعكس محور y (نظام الصورة معكوس رأسيًا)
        return (x_mm, y_mm)

    for pl in polylines_px:
        pts_mm = [px_to_mm(p) for p in pl]
        if len(pts_mm) < 2:
            continue
        if entity_type == "spline":
            msp.add_spline(fit_points=pts_mm, dxfattribs={"layer": "CUT"})
        else:
            msp.add_lwpolyline(pts_mm, close=True, dxfattribs={"layer": "CUT"})

    doc.saveas(output_path)
    log.info("تم حفظ الملف: %s", output_path)
    return doc
