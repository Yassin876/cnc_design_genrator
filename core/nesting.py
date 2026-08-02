"""
Rectangular bin-packing nesting for 2D DXF parts.
Uses rectpack (MaxRects) on bounding boxes, then writes a combined sheet DXF.
"""

import os
from pathlib import Path

import ezdxf
from ezdxf import bbox as dxf_bbox
from rectpack import newPacker
from rectpack.maxrects import MaxRectsBssf


def _normalize_parts(parts):
    """Expand parts into a flat list of (path, instance_id) entries."""
    expanded = []
    for entry in parts:
        if isinstance(entry, (tuple, list)) and len(entry) == 2:
            path, qty = entry
            qty = max(1, int(qty))
            for i in range(qty):
                expanded.append((str(path), i))
        else:
            expanded.append((str(entry), 0))
    return expanded


def _part_bbox(path):
    """Return (width, height, min_x, min_y) for a DXF file's modelspace."""
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    try:
        extents = dxf_bbox.extents(msp)
    except Exception:
        return 0.0, 0.0, 0.0, 0.0

    if extents.has_data:
        min_x, min_y = extents.extmin.x, extents.extmin.y
        max_x, max_y = extents.extmax.x, extents.extmax.y
    else:
        min_x = min_y = max_x = max_y = 0.0

    width = max(max_x - min_x, 0.01)
    height = max(max_y - min_y, 0.01)
    return width, height, min_x, min_y


def _ensure_block(doc, source_path, block_name):
    """Copy modelspace entities from source DXF into a block in doc."""
    if block_name in doc.blocks:
        return

    src = ezdxf.readfile(source_path)
    src_msp = src.modelspace()
    block = doc.blocks.new(name=block_name)

    for entity in src_msp:
        try:
            block.add_entity(entity.copy())
        except Exception:
            pass


def nest_parts(
    parts,
    sheet_width,
    sheet_height,
    spacing=5.0,
    allow_rotate=True,
    output_path="outputs/nested_sheet.dxf",
):
    """
    Pack DXF parts onto a single sheet.

    Args:
        parts: list of DXF paths, OR list of (path, qty) tuples
        sheet_width: sheet width in mm
        sheet_height: sheet height in mm
        spacing: gap between parts in mm
        allow_rotate: whether 90° rotation is allowed
        output_path: destination DXF path

    Returns:
        (output_path, placements, unplaced_count)
        placements = [{"part": path, "x": .., "y": .., "rotation": ..}, ...]
    """
    expanded = _normalize_parts(parts)
    if not expanded:
        raise ValueError("No parts provided for nesting")

    spacing = max(float(spacing), 0.0)
    sheet_width = float(sheet_width)
    sheet_height = float(sheet_height)

    part_info = []
    for idx, (path, _inst) in enumerate(expanded):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Part DXF not found: {path}")
        width, height, min_x, min_y = _part_bbox(path)
        max_x = min_x + width
        max_y = min_y + height
        pack_w = width + spacing
        pack_h = height + spacing
        part_info.append(
            {
                "path": path,
                "width": width,
                "height": height,
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y,
                "pack_w": pack_w,
                "pack_h": pack_h,
                "rid": idx,
            }
        )

    packer = newPacker(pack_algo=MaxRectsBssf, rotation=allow_rotate)
    packer.add_bin(sheet_width, sheet_height)
    for info in part_info:
        packer.add_rect(info["pack_w"], info["pack_h"], rid=info["rid"])

    packer.pack()
    packed = {rect[5]: rect for rect in packer.rect_list()}

    placements = []
    unplaced_count = 0
    out_doc = ezdxf.new("R2010")
    out_msp = out_doc.modelspace()
    block_cache = {}

    for info in part_info:
        rid = info["rid"]
        if rid not in packed:
            unplaced_count += 1
            continue

        _bin, px, py, pw, ph, _ = packed[rid]
        rotated = abs(pw - info["pack_w"]) > 0.01 or abs(ph - info["pack_h"]) > 0.01
        rotation = 90 if rotated else 0

        # Non-rotated: world corner = insert + (min_x, min_y)  → insert = pack_pos - min
        insert_x = px + spacing / 2.0 - info["min_x"]
        insert_y = py + spacing / 2.0 - info["min_y"]
        if rotated:
            # 90° CCW: world_x = insert_x - by,  world_y = insert_y + bx
            # leftmost  = insert_x - max_y  → insert_x = px + spacing/2 + max_y
            # bottommost = insert_y + min_x → insert_y = py + spacing/2 - min_x
            insert_x = px + spacing / 2.0 + info["max_y"]
            insert_y = py + spacing / 2.0 - info["min_x"]

        path = info["path"]
        block_name = block_cache.get(path)
        if block_name is None:
            block_name = f"PART_{len(block_cache)}"
            block_cache[path] = block_name
            _ensure_block(out_doc, path, block_name)

        out_msp.add_blockref(
            block_name,
            insert=(insert_x, insert_y),
            dxfattribs={"rotation": rotation},
        )

        placements.append(
            {
                "part": path,
                "x": insert_x,
                "y": insert_y,
                "rotation": rotation,
            }
        )

    # ── Draw sheet border ───────────────────────────────────────
    border_pts = [
        (0, 0),
        (sheet_width, 0),
        (sheet_width, sheet_height),
        (0, sheet_height),
        (0, 0),
    ]
    out_msp.add_lwpolyline(border_pts, dxfattribs={"layer": "SHEET_BORDER", "color": 3})

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    out_doc.saveas(output_path)
    return output_path, placements, unplaced_count


def sheet_utilization(placements, parts, sheet_width, sheet_height):
    """
    Rough % of sheet area occupied by part bounding boxes.
    """
    sheet_area = float(sheet_width) * float(sheet_height)
    if sheet_area <= 0:
        return 0.0

    bbox_cache = {}
    used = 0.0
    for placement in placements:
        path = placement["part"]
        if path not in bbox_cache:
            w, h, _, _ = _part_bbox(path)
            bbox_cache[path] = (w, h)
        w, h = bbox_cache[path]
        if placement.get("rotation", 0) in (90, 270):
            w, h = h, w
        used += w * h

    return min(100.0, (used / sheet_area) * 100.0)
