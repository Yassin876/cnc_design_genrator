"""
DXF Editor and Parser Module for Anti Design.
Parses DXF files into structured JSON entity hierarchies and applies parametric edits.
"""
import json
import math
import shutil
import ezdxf
import numpy as np


# ── Helpers ──────────────────────────────────────────────────────────────────

def _entity_bbox(pts: list[tuple]) -> dict:
    if not pts:
        return {"w": 0, "h": 0, "cx": 0, "cy": 0}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    return {
        "w": round(w, 4),
        "h": round(h, 4),
        "cx": round(cx, 4),
        "cy": round(cy, 4),
    }


def _is_circle(pts: list[tuple], bbox: dict, tol: float = 0.15) -> bool:
    """True when the polyline is a close approximation of a circle."""
    if len(pts) < 8:
        return False
    diam = (bbox["w"] + bbox["h"]) / 2
    if diam < 0.01:
        return False
    asymmetry = abs(bbox["w"] - bbox["h"]) / diam
    return asymmetry < tol


def _circle_diameter(pts: list[tuple], bbox: dict) -> float:
    return round((bbox["w"] + bbox["h"]) / 2, 4)


def _make_circle_pts(cx: float, cy: float, r: float, n: int = 64) -> list[tuple]:
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]


# ── DXF -> JSON Serializer ───────────────────────────────────────────────────

def dxf_to_json(dxf_path: str) -> dict:
    """
    Parse a DXF file and return a compact JSON-serializable dict of layers and geometric entities.
    """
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    entities_out = []
    for idx, ent in enumerate(msp):
        if ent.dxftype() != "LWPOLYLINE":
            record = {
                "id": idx,
                "layer": ent.dxf.layer,
                "type": ent.dxftype(),
            }
            if ent.dxftype() == "LINE":
                record["points"] = [
                    [float(ent.dxf.start[0]), float(ent.dxf.start[1])],
                    [float(ent.dxf.end[0]), float(ent.dxf.end[1])],
                ]
            elif ent.dxftype() == "CIRCLE":
                record["center"] = [float(ent.dxf.center[0]), float(ent.dxf.center[1])]
                record["radius"] = float(ent.dxf.radius)
            elif ent.dxftype() == "DIMENSION":
                dim_type = ent.dxf.get("dimtype", 0) & 0x07
                if dim_type == 1 and ent.dxf.hasattr("defpoint") and ent.dxf.hasattr("defpoint2"):
                    p1 = ent.dxf.defpoint
                    p2 = ent.dxf.defpoint2
                    record["p1"] = [float(p1[0]), float(p1[1])]
                    record["p2"] = [float(p2[0]), float(p2[1])]
                elif dim_type == 4 and ent.dxf.hasattr("defpoint"):
                    center = ent.dxf.defpoint
                    record["center"] = [float(center[0]), float(center[1])]
                    record["radius"] = float(ent.dxf.get("actual_measurement", 0.0))
                record["text"] = ent.dxf.get("text", "") or str(round(float(ent.dxf.get("actual_measurement", 0.0)), 3))
            entities_out.append(record)
            continue

        pts = list(ent.get_points())
        bbox = _entity_bbox(pts)
        closed = bool(ent.closed)

        # Shape classification
        if closed and _is_circle(pts, bbox):
            shape = "circle"
        elif closed and bbox["w"] > 0 and bbox["h"] > 0:
            ratio = bbox["w"] / bbox["h"]
            if 0.8 < ratio < 1.25:
                shape = "rect_or_square"
            elif ratio > 1.5 or ratio < 0.67:
                shape = "oval_slot"
            else:
                shape = "complex_closed"
        elif not closed:
            if bbox["h"] < 2:
                shape = "h_line"
            elif bbox["w"] < 2:
                shape = "v_line"
            else:
                shape = "open_complex"
        else:
            shape = "complex"

        record = {
            "id": idx,
            "layer": ent.dxf.layer,
            "type": "LWPOLYLINE",
            "closed": closed,
            "n_pts": len(pts),
            "points": [[float(point[0]), float(point[1])] for point in pts],
            "bbox": bbox,
            "shape": shape,
        }
        if shape == "circle":
            record["diameter"] = _circle_diameter(pts, bbox)

        entities_out.append(record)

    layers = [layer.dxf.name for layer in doc.layers]
    return {"layers": layers, "entities": entities_out}


# ── Edit Applicator ──────────────────────────────────────────────────────────

def apply_edits(dxf_path: str, edits: dict, output_path: str) -> None:
    """
    Apply structured edits (circle resizing, layer changes, deletions) and save to output_path.
    """
    shutil.copy(dxf_path, output_path)
    doc = ezdxf.readfile(output_path)
    msp = doc.modelspace()
    entities = list(msp)

    delete_ids = set(edits.get("delete", []))
    resize_map = {r["id"]: r["diameter"] for r in edits.get("resize_circles", [])}
    layer_map = {s["id"]: s["layer"] for s in edits.get("set_layer", [])}

    for idx, ent in enumerate(entities):
        # Delete check
        if idx in delete_ids:
            msp.delete_entity(ent)
            continue

        # Resize circle
        if idx in resize_map and ent.dxftype() == "CIRCLE":
            ent.dxf.radius = resize_map[idx] / 2
        elif idx in resize_map and ent.dxftype() == "LWPOLYLINE":
            pts = list(ent.get_points())
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            cx = (max(xs) + min(xs)) / 2
            cy = (max(ys) + min(ys)) / 2
            r = resize_map[idx] / 2
            new_pts = _make_circle_pts(cx, cy, r, n=64)
            ent.set_points(new_pts)
            ent.closed = True

        # Change layer
        if idx in layer_map:
            ent.dxf.layer = layer_map[idx]

    doc.save()
