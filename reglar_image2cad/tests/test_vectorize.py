"""
اختبار بسيط: نتأكد إن مربع أبيض بسيط بيتحول لكونتور واحد بأربع زوايا تقريبًا.
شغّل بـ: pytest tests/
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from image2cad.config import VectorizeConfig  # noqa: E402
from image2cad.vectorize import mask_to_potrace_path, curve_to_polyline  # noqa: E402


def test_square_traces_to_single_contour():
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255  # مربع أبيض في النص

    cfg = VectorizeConfig(alphamax=0.0)  # 0 = زوايا حادة بس، من غير تنعيم
    path = mask_to_potrace_path(mask, cfg)
    curves = list(path)

    assert len(curves) == 1
    pts = curve_to_polyline(curves[0], cfg.bezier_steps)
    assert len(pts) >= 4
