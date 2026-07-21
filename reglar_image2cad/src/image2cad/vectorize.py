"""
Cell 9 من النوت بوك: تحويل قناع ثنائي لمسار متجهي حقيقي (خطوط + منحنيات Bezier)
باستخدام Potrace (نسخة `potracer` البايثون الخالصة)، وتحويل المسار ده لقائمة نقاط
(polyline) قابلة للتصدير كـ DXF.
"""
from __future__ import annotations

import numpy as np
import potrace

from .config import VectorizeConfig


def mask_to_potrace_path(mask_np: np.ndarray, cfg: VectorizeConfig):
    """
    يحوّل قناع ثنائي (binary mask) إلى مسار متجهي (potrace.Path).

    ⚠️ ملحوظة مهمة عن مكتبة potracer (v0.0.4):
    الكونستركتور بتاع Bitmap بيعمل invert() تلقائيًا جوه __init__ بعد الـ threshold،
    فلازم نبعت الصورة بصيغة uint8 (0-255) مع عكس القيم (الحبر = 0، الخلفية = 255)
    عشان الـ invert() الداخلي يرجعها صح (الحبر = foreground فعليًا). لو اتبعتلها
    مصفوفة 0/1 عادية هتتعامل الصورة كلها كـ foreground واحد وهيطلع كونتور واحد بس.
    """
    mask_2d = mask_np[0] if mask_np.ndim == 3 else mask_np

    binary_u8 = np.where(mask_2d > 0, 0, 255).astype(np.uint8)

    bmp = potrace.Bitmap(binary_u8)
    return bmp.trace(
        turdsize=cfg.turdsize,
        turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
        alphamax=cfg.alphamax,
        opticurve=cfg.opticurve,
        opttolerance=cfg.opttolerance,
    )


def _pt(p) -> tuple[float, float]:
    """يحوّل أي كائن نقطة (Point بتاع potracer، أو tuple/list عادي) لصيغة (x, y)."""
    if hasattr(p, "x") and hasattr(p, "y"):
        return (float(p.x), float(p.y))
    return (float(p[0]), float(p[1]))


def cubic_bezier_points(p0, c1, c2, p1, steps: int = 12) -> list[tuple[float, float]]:
    p0, c1, c2, p1 = _pt(p0), _pt(c1), _pt(c2), _pt(p1)
    ts = np.linspace(0.0, 1.0, steps)
    pts = []
    for t in ts:
        x = ((1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * c1[0]
             + 3 * (1 - t) * t ** 2 * c2[0] + t ** 3 * p1[0])
        y = ((1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * c1[1]
             + 3 * (1 - t) * t ** 2 * c2[1] + t ** 3 * p1[1])
        pts.append((x, y))
    return pts


def curve_to_polyline(curve, bezier_steps: int = 12) -> list[tuple[float, float]]:
    """يحوّل كونتور واحد (Curve) لقائمة نقاط، بيفرد segments الزوايا والمنحنيات."""
    pts = [_pt(curve.start_point)]
    for seg in curve:
        if seg.is_corner:
            pts.append(_pt(seg.c))
            pts.append(_pt(seg.end_point))
        else:
            start = pts[-1]
            flat = cubic_bezier_points(start, seg.c1, seg.c2, seg.end_point, bezier_steps)
            pts.extend(flat[1:])
    return pts
