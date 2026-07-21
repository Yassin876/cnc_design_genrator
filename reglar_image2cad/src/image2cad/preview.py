"""
Cell 14 من النوت بوك: عرض ملف DXF كصورة PNG للمراجعة السريعة بدون فتح CAD.
"""
from __future__ import annotations

import logging

import ezdxf
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

log = logging.getLogger(__name__)


def render_dxf_preview(dxf_path: str, output_png: str) -> None:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    fig, ax = plt.subplots(figsize=(10, 10))
    ctx = RenderContext(doc)
    backend = MatplotlibBackend(ax)
    Frontend(ctx, backend).draw_layout(msp)

    ax.set_aspect("equal")
    plt.savefig(output_png, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    log.info("Preview saved: %s", output_png)
