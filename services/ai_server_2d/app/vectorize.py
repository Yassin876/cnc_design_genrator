"""
Vectorization module for ai_server_2d using Potrace.
Converts binary masks into vector paths with Cubic Bézier curve interpolation.
"""
from __future__ import annotations

import numpy as np
import potrace


def mask_to_potrace_path(
    mask_np: np.ndarray,
    turdsize: int = 2,
    alphamax: float = 1.0,
    opticurve: bool = True,
    opttolerance: float = 0.2,
):
    """
    Converts binary mask (numpy array) to Potrace vector path.
    Note: potracer Bitmap automatically inverts internally, so ink must be 0 and background 255.
    """
    mask_2d = mask_np[0] if mask_np.ndim == 3 else mask_np
    binary_u8 = np.where(mask_2d > 0, 0, 255).astype(np.uint8)

    bmp = potrace.Bitmap(binary_u8)
    return bmp.trace(
        turdsize=turdsize,
        turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
        alphamax=alphamax,
        opticurve=opticurve,
        opttolerance=opttolerance,
    )


def _pt(p) -> tuple[float, float]:
    if hasattr(p, "x") and hasattr(p, "y"):
        return (float(p.x), float(p.y))
    return (float(p[0]), float(p[1]))


def cubic_bezier_points(p0, c1, c2, p1, steps: int = 12) -> list[tuple[float, float]]:
    p0, c1, c2, p1 = _pt(p0), _pt(c1), _pt(c2), _pt(p1)
    pts = []
    for t in np.linspace(0.0, 1.0, steps):
        x = (
            (1 - t) ** 3 * p0[0]
            + 3 * (1 - t) ** 2 * t * c1[0]
            + 3 * (1 - t) * t ** 2 * c2[0]
            + t ** 3 * p1[0]
        )
        y = (
            (1 - t) ** 3 * p0[1]
            + 3 * (1 - t) ** 2 * t * c1[1]
            + 3 * (1 - t) * t ** 2 * c2[1]
            + t ** 3 * p1[1]
        )
        pts.append((x, y))
    return pts


def curve_to_polyline(curve, bezier_steps: int = 12) -> list[tuple[float, float]]:
    pts = [_pt(curve.start_point)]
    for seg in curve:
        if seg.is_corner:
            pts.append(_pt(seg.c))
            pts.append(_pt(seg.end_point))
        else:
            start = pts[-1]
            flat = cubic_bezier_points(
                start, seg.c1, seg.c2, seg.end_point, bezier_steps
            )
            pts.extend(flat[1:])
    return pts
