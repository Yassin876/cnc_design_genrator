"""
Kerf compensation module for ai_server_2d.
Offsets points by tool radius in pixels to compensate for CNC tool diameter.
"""
from __future__ import annotations

import numpy as np


def apply_kerf_compensation(
    path_pts: np.ndarray,
    tool_diameter_mm: float,
    scale_mm_px: float,
    is_internal: bool = True,
) -> np.ndarray:
    """Offset contour points by half tool diameter (converted to pixels)."""
    tool_radius_px = (tool_diameter_mm / 2.0) / scale_mm_px
    offset = -tool_radius_px if is_internal else +tool_radius_px

    pts = path_pts.astype(np.float64)
    cx, cy = pts[:, 0].mean(), pts[:, 1].mean()

    result = []
    for x, y in pts:
        dx, dy = x - cx, y - cy
        dist = np.hypot(dx, dy)
        if dist < 1e-9:
            result.append([x, y])
        else:
            result.append([x + offset * dx / dist, y + offset * dy / dist])
    return np.array(result, dtype=np.float64)
