"""
DXF Exporter module for ai_server_2d using Potrace.
Builds real-world metric DXF files (LWPOLYLINE or SPLINE) from Potrace vector contours.
"""
from __future__ import annotations

import logging
import ezdxf
import numpy as np

from app.vectorize import mask_to_potrace_path, curve_to_polyline
from app.kerf import apply_kerf_compensation

log = logging.getLogger(__name__)


def build_dxf_from_potrace(
    mask_np: np.ndarray,
    part_width_mm: float = 700.0,
    part_height_mm: float = 700.0,
    tool_diameter_mm: float = 5.0,
    apply_kerf: bool = True,
    is_internal: bool = True,
    margin_mm: float = 5.0,
    output_path: str = "output_cnc.dxf",
    entity_type: str = "lwpolyline",  # "lwpolyline" or "spline"
    bezier_steps: int = 12,
):
    mask_2d = mask_np[0] if mask_np.ndim == 3 else mask_np

    # 1. Potrace Vectorization
    path = mask_to_potrace_path(mask_2d)
    curves = list(path)
    if not curves:
        log.warning("Potrace found no contours in mask.")
        return None

    polylines_px = [
        np.array(curve_to_polyline(c, bezier_steps)) for c in curves
    ]
    all_pts = np.vstack(polylines_px)
    x_min, y_min = all_pts[:, 0].min(), all_pts[:, 1].min()
    x_max, y_max = all_pts[:, 0].max(), all_pts[:, 1].max()
    w_b = max(x_max - x_min, 1)
    h_b = max(y_max - y_min, 1)

    # 1.5 Filter Outer Image Frame Contour ONLY if it touches the image array boundary (0, 0, W, H)
    H, W = mask_2d.shape[:2]
    filtered_polylines = []
    for pl in polylines_px:
        pl_xmin, pl_ymin = pl[:, 0].min(), pl[:, 1].min()
        pl_xmax, pl_ymax = pl[:, 0].max(), pl[:, 1].max()
        
        # Only exclude if this contour touches the outermost image pixel frame
        is_image_border = (
            pl_xmin <= 2 and pl_ymin <= 2 and
            pl_xmax >= (W - 3) and pl_ymax >= (H - 3)
        )
        if is_image_border and len(polylines_px) > 1:
            log.info("Filtered out image border rectangle contour touching image frame (0,0,%d,%d)", W, H)
            continue
        filtered_polylines.append(pl)

    if filtered_polylines:
        polylines_px = filtered_polylines
        all_pts = np.vstack(polylines_px)
        x_min, y_min = all_pts[:, 0].min(), all_pts[:, 1].min()
        x_max, y_max = all_pts[:, 0].max(), all_pts[:, 1].max()
        w_b = max(x_max - x_min, 1)
        h_b = max(y_max - y_min, 1)

    scale = min(
        part_width_mm / w_b if part_width_mm > 0 else 1.0,
        part_height_mm / h_b if part_height_mm > 0 else 1.0,
    )

    # 2. Kerf Compensation (Optional)
    if apply_kerf and tool_diameter_mm > 0:
        polylines_px = [
            apply_kerf_compensation(pl, tool_diameter_mm, scale, is_internal)
            for pl in polylines_px
        ]

    # 3. DXF Document Generation (R2010 in MM)
    doc = ezdxf.new(dxfversion="R2010")
    doc.units = ezdxf.units.MM
    if "CUT" not in doc.layers:
        doc.layers.add(name="CUT", color=1)
    msp = doc.modelspace()

    def px_to_mm(pt):
        x_mm = (pt[0] - x_min) * scale + margin_mm
        y_mm = (y_max - pt[1]) * scale + margin_mm  # Invert Y for CAD coordinate space
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
    log.info("Saved DXF file via Potrace engine: %s", output_path)
    return doc
