"""
Rectangular bin-packing nesting for 2D DXF parts with Stock Inventory,
Thickness Matching, Production Priority, and Transactional Sheet Management.
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
import ezdxf
from ezdxf import bbox as dxf_bbox
from rectpack import newPacker
from rectpack.maxrects import MaxRectsBssf

from shapely.geometry import Polygon, MultiPolygon, box
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

PRIORITY_LEVEL_MAP = {
    "HIGH": 0,
    "NORMAL": 1,
    "LOW": 2
}


def dxf_to_polygon(path: str) -> Polygon:
    """Extract 2D outer boundary polygon from a DXF file using ezdxf path flattening."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()

        polys = []
        for entity in msp:
            try:
                p = ezdxf.path.make_path(entity)
                vertices = list(p.flattening(distance=0.1))
                if len(vertices) >= 3:
                    pts = [(v.x, v.y) for v in vertices]
                    poly = Polygon(pts)
                    if poly.is_valid and poly.area > 0.001:
                        polys.append(poly)
            except Exception:
                pass

        if polys:
            union_poly = unary_union(polys)
            if union_poly.is_valid:
                if isinstance(union_poly, MultiPolygon):
                    union_poly = max(union_poly.geoms, key=lambda g: g.area)
                return union_poly
    except Exception:
        pass

    w, h, min_x, min_y = part_bbox(path)
    return box(min_x, min_y, min_x + w, min_y + h)


class StockSheet:
    def __init__(
        self,
        width: float,
        height: float,
        thickness: float = 1.0,
        material: str = "Default",
        name: str = "",
        available_quantity: int = 1,
        unlimited_quantity: bool = False,
        sheet_id: Optional[str] = None
    ):
        self.id = sheet_id or str(uuid.uuid4())[:8]
        self.name = name or f"{material} ({width:.0f}x{height:.0f}x{thickness:.1f}mm)"
        self.material = material or "Default"
        self.width = float(width)
        self.height = float(height)
        self.thickness = float(thickness)
        self.available_quantity = max(0, int(available_quantity))
        self.unlimited_quantity = bool(unlimited_quantity)
        self.used_quantity = 0

    @property
    def remaining_quantity(self) -> int:
        if self.unlimited_quantity:
            return 999999
        return max(0, self.available_quantity - self.used_quantity)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "material": self.material,
            "width": self.width,
            "height": self.height,
            "thickness": self.thickness,
            "available_quantity": self.available_quantity,
            "unlimited_quantity": self.unlimited_quantity,
            "used_quantity": self.used_quantity,
            "remaining_quantity": self.remaining_quantity,
        }


class NestablePart:
    def __init__(
        self,
        path: str,
        quantity: int = 1,
        thickness: float = 1.0,
        priority: str = "Normal",
        priority_order: int = 100,
        name: str = "",
        part_id: Optional[str] = None
    ):
        self.id = part_id or str(uuid.uuid4())[:8]
        self.path = str(path)
        self.name = name or os.path.basename(self.path)
        self.quantity = max(1, int(quantity))
        self.thickness = float(thickness)
        self.priority = priority.strip().title() if isinstance(priority, str) else "Normal"
        if self.priority not in ("High", "Normal", "Low"):
            self.priority = "Normal"
        self.priority_order = int(priority_order)
        self.placed_quantity = 0

        # Dimensions filled during bbox / polygon calculation
        self.width = 0.0
        self.height = 0.0
        self.min_x = 0.0
        self.min_y = 0.0
        self.max_x = 0.0
        self.max_y = 0.0
        self.polygon: Optional[Polygon] = None

    @property
    def unplaced_quantity(self) -> int:
        return max(0, self.quantity - self.placed_quantity)

    @property
    def area(self) -> float:
        if self.polygon is not None and self.polygon.is_valid:
            return self.polygon.area
        return self.width * self.height

    @property
    def max_dimension(self) -> float:
        return max(self.width, self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "quantity": self.quantity,
            "placed_quantity": self.placed_quantity,
            "unplaced_quantity": self.unplaced_quantity,
            "thickness": self.thickness,
            "priority": self.priority,
            "priority_order": self.priority_order,
            "width": self.width,
            "height": self.height,
        }


def part_bbox(path: str) -> Tuple[float, float, float, float]:
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


def _copy_entities_to_msp(
    out_msp,
    source_path: str,
    offset_x: float,
    offset_y: float,
    rotation_deg: float,
    part: "NestablePart",
):
    """
    Directly copy all modelspace entities from source DXF into out_msp,
    applying the given XY translation and rotation around the part origin.
    Avoids block references entirely for maximum DXF viewer compatibility.
    """
    import math
    from ezdxf.math import Matrix44

    src = ezdxf.readfile(source_path)
    src_msp = src.modelspace()

    # Build transform: first translate so part origin is at (0,0), rotate, then translate to placement
    angle_rad = math.radians(rotation_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Normalise to origin: shift by -min_x, -min_y
    shift_x = -part.min_x
    shift_y = -part.min_y

    # Final translation after rotation
    tx = offset_x
    ty = offset_y

    def transform_pt(px, py):
        # 1. shift so local origin is at (0,0)
        nx = px + shift_x
        ny = py + shift_y
        # 2. rotate
        rx = cos_a * nx - sin_a * ny
        ry = sin_a * nx + cos_a * ny
        # 3. translate to placement
        return (rx + tx, ry + ty)

    for entity in src_msp:
        try:
            etype = entity.dxftype()
            if etype == "LINE":
                s = entity.dxf.start
                e = entity.dxf.end
                ns = transform_pt(s.x, s.y)
                ne = transform_pt(e.x, e.y)
                out_msp.add_line(ns, ne, dxfattribs={"layer": entity.dxf.get("layer", "0")})

            elif etype in ("LWPOLYLINE", "POLYLINE"):
                if etype == "LWPOLYLINE":
                    pts_raw = entity.get_points(format="xy")
                    pts = [transform_pt(p[0], p[1]) for p in pts_raw]
                    closed = entity.closed
                else:
                    pts = [transform_pt(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    closed = bool(entity.dxf.flags & 1)
                if len(pts) >= 2:
                    out_msp.add_lwpolyline(
                        pts,
                        close=closed,
                        dxfattribs={"layer": entity.dxf.get("layer", "0")},
                    )

            elif etype == "CIRCLE":
                c = entity.dxf.center
                nc = transform_pt(c.x, c.y)
                out_msp.add_circle(
                    nc,
                    radius=entity.dxf.radius,
                    dxfattribs={"layer": entity.dxf.get("layer", "0")},
                )

            elif etype == "ARC":
                c = entity.dxf.center
                nc = transform_pt(c.x, c.y)
                out_msp.add_arc(
                    nc,
                    radius=entity.dxf.radius,
                    start_angle=entity.dxf.start_angle + rotation_deg,
                    end_angle=entity.dxf.end_angle + rotation_deg,
                    dxfattribs={"layer": entity.dxf.get("layer", "0")},
                )

            elif etype == "ELLIPSE":
                c = entity.dxf.center
                nc = transform_pt(c.x, c.y)
                ma = entity.dxf.major_axis
                # rotate major axis
                rma_x = cos_a * ma.x - sin_a * ma.y
                rma_y = sin_a * ma.x + cos_a * ma.y
                out_msp.add_ellipse(
                    nc,
                    major_axis=(rma_x, rma_y),
                    ratio=entity.dxf.ratio,
                    start_param=entity.dxf.start_param,
                    end_param=entity.dxf.end_param,
                    dxfattribs={"layer": entity.dxf.get("layer", "0")},
                )

            elif etype == "SPLINE":
                raw_cpts = entity.control_points
                cpts = [transform_pt(p[0], p[1]) for p in raw_cpts]
                spline = out_msp.add_spline(
                    dxfattribs={"layer": entity.dxf.get("layer", "0")}
                )
                spline.control_points = cpts
                spline.knots = entity.knots
                spline.degree = entity.dxf.degree
                try:
                    spline.weights = entity.weights
                except Exception:
                    pass

        except Exception:
            pass


def sheet_utilization(placements: List[Dict[str, Any]], sheet_width: float, sheet_height: float) -> float:
    """
    Calculate utilization percentage = (total placed part bounding area / usable sheet area) * 100.
    """
    sheet_area = float(sheet_width) * float(sheet_height)
    if sheet_area <= 0:
        return 0.0

    used_area = 0.0
    for p in placements:
        w = p.get("width", 0.0)
        h = p.get("height", 0.0)
        used_area += w * h

    return min(100.0, max(0.0, (used_area / sheet_area) * 100.0))


def _try_pack_parts_on_sheet(
    sheet_width: float,
    sheet_height: float,
    part_instances: List[Tuple[NestablePart, int]],
    spacing: float,
    allow_rotate: bool,
) -> Optional[List[Dict[str, Any]]]:
    """
    Attempt to pack all part_instances onto a single sheet of given dimensions using
    True Shape Irregular Nesting (Shapely Polygon Geometry & Spacing Buffer).
    """
    sheet_poly = box(0, 0, sheet_width, sheet_height)
    half_spacing = spacing / 2.0

    placed_items: List[Tuple[Polygon, Polygon]] = []
    placements: List[Dict[str, Any]] = []

    rot_angles = [0, 90, 180, 270] if allow_rotate else [0]

    for part, _inst in part_instances:
        best_candidate = None
        min_score = float('inf')

        part_poly_base = getattr(part, 'polygon', None)
        if part_poly_base is None or not isinstance(part_poly_base, Polygon):
            part_poly_base = dxf_to_polygon(part.path)

        for angle in rot_angles:
            if angle == 0:
                rot_p = part_poly_base
            else:
                rot_p = rotate(part_poly_base, angle=angle, origin=(0, 0))

            bmin_x, bmin_y, bmax_x, bmax_y = rot_p.bounds
            rot_p = translate(rot_p, xoff=-bmin_x, yoff=-bmin_y)
            pw = bmax_x - bmin_x
            ph = bmax_y - bmin_y

            if pw + spacing > sheet_width or ph + spacing > sheet_height:
                continue

            rot_buf = rot_p.buffer(half_spacing)

            # Generate candidate placement points (tx, ty)
            cand_pts = set()
            cand_pts.add((half_spacing, half_spacing))

            for _p_poly, p_buf in placed_items:
                b_minx, b_miny, b_maxx, b_maxy = p_buf.bounds
                cand_pts.add((round(b_maxx + half_spacing, 2), round(half_spacing, 2)))
                cand_pts.add((round(half_spacing, 2), round(b_maxy + half_spacing, 2)))
                cand_pts.add((round(b_maxx + half_spacing, 2), round(b_miny + half_spacing, 2)))
                cand_pts.add((round(b_minx + half_spacing, 2), round(b_maxy + half_spacing, 2)))
                cand_pts.add((round(b_maxx + half_spacing, 2), round(b_maxy + half_spacing, 2)))

            # Grid step scan along bottom-left region
            step_x = max(20.0, pw / 3.0)
            step_y = max(20.0, ph / 3.0)

            gx = half_spacing
            while gx <= sheet_width - pw - half_spacing:
                gy = half_spacing
                while gy <= sheet_height - ph - half_spacing:
                    cand_pts.add((round(gx, 2), round(gy, 2)))
                    gy += step_y
                gx += step_x

            # Evaluate candidate points
            for tx, ty in cand_pts:
                if tx + pw + half_spacing > sheet_width or ty + ph + half_spacing > sheet_height:
                    continue

                score = ty * 10000.0 + tx
                if score >= min_score:
                    continue

                test_poly = translate(rot_p, xoff=tx, yoff=ty)
                test_buf = translate(rot_buf, xoff=tx, yoff=ty)

                if not sheet_poly.contains(test_poly):
                    continue

                overlap = False
                for _placed_p, placed_buf in placed_items:
                    if test_buf.intersects(placed_buf):
                        overlap = True
                        break

                if not overlap:
                    min_score = score
                    insert_x = tx - part.min_x
                    insert_y = ty - part.min_y
                    if angle == 90:
                        insert_x = tx + part.max_y
                        insert_y = ty - part.min_x
                    elif angle == 180:
                        insert_x = tx + part.max_x
                        insert_y = ty + part.max_y
                    elif angle == 270:
                        insert_x = tx - part.min_y
                        insert_y = ty + part.max_x

                    best_candidate = (test_poly, test_buf, {
                        "part": part.path,
                        "part_name": part.name,
                        "part_id": part.id,
                        "x": insert_x,
                        "y": insert_y,
                        "width": part.width,
                        "height": part.height,
                        "rotation": angle,
                        "priority": part.priority,
                        "priority_order": part.priority_order,
                    })

        if best_candidate is None:
            return None

        placed_items.append((best_candidate[0], best_candidate[1]))
        placements.append(best_candidate[2])

    return placements


def nest_parts(
    parts: List[Any],
    stock_sheets: List[Any],
    spacing: float = 5.0,
    allow_rotate: bool = True,
    nesting_mode: str = "Finish priority parts first",
    continue_on_incomplete: bool = True,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transactional Bin Packing Nesting for DXF Parts onto Stock Sheets.
    
    Returns structured NestResult dictionary.
    """
    # ── 1. Normalize Inputs into NestablePart and StockSheet objects ──────────
    normalized_sheets: List[StockSheet] = []
    if isinstance(stock_sheets, (list, tuple)):
        for s in stock_sheets:
            if isinstance(s, StockSheet):
                normalized_sheets.append(s)
            elif isinstance(s, dict):
                normalized_sheets.append(StockSheet(
                    width=s.get("width", 1200),
                    height=s.get("height", 600),
                    thickness=s.get("thickness", 1.0),
                    material=s.get("material", "Default"),
                    name=s.get("name", ""),
                    available_quantity=s.get("available_quantity", 1),
                    unlimited_quantity=s.get("unlimited_quantity", False),
                    sheet_id=s.get("id"),
                ))
    elif isinstance(stock_sheets, (int, float)): # Legacy format (sheet_width, sheet_height)
        # sheet_width provided as first arg, check if legacy positional args passed
        pass

    # Fallback to single sheet if no sheets provided
    if not normalized_sheets:
        raise ValueError("At least one valid stock sheet must be specified.")

    normalized_parts: List[NestablePart] = []
    for idx, p in enumerate(parts):
        if isinstance(p, NestablePart):
            normalized_parts.append(p)
        elif isinstance(p, dict):
            normalized_parts.append(NestablePart(
                path=p.get("path") or p.get("file_name", ""),
                quantity=p.get("quantity", 1),
                thickness=p.get("thickness", 1.0),
                priority=p.get("priority", "Normal"),
                priority_order=p.get("priority_order", 100),
                name=p.get("name") or p.get("file_name", ""),
                part_id=p.get("id"),
            ))
        elif isinstance(p, (tuple, list)) and len(p) >= 2:
            path, qty = p[0], p[1]
            normalized_parts.append(NestablePart(path=path, quantity=qty))
        elif isinstance(p, str):
            normalized_parts.append(NestablePart(path=p, quantity=1))

    if not normalized_parts:
        raise ValueError("No valid parts provided for nesting.")

    # Populate dimensions and Shapely polygon for all parts
    for part in normalized_parts:
        if not os.path.isfile(part.path):
            raise FileNotFoundError(f"DXF part file not found: {part.path}")
        w, h, min_x, min_y = part_bbox(part.path)
        part.width = w
        part.height = h
        part.min_x = min_x
        part.min_y = min_y
        part.max_x = min_x + w
        part.max_y = min_y + h
        part.polygon = dxf_to_polygon(part.path)

    spacing = max(0.0, float(spacing))

    # Output Directory Setup
    if not output_dir:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = os.path.join("outputs", "nesting_results", timestamp)
    os.makedirs(output_dir, exist_ok=True)

    unplaced_report: List[Dict[str, Any]] = []

    # ── 2. Thickness Compatibility Check ──────────────────────────────────────
    # Group parts by compatible sheet thickness
    thickness_groups: Dict[float, List[NestablePart]] = {}
    
    for part in normalized_parts:
        # Find if any stock sheet matches part thickness
        matching_sheets = [
            s for s in normalized_sheets
            if abs(part.thickness - s.thickness) < 0.001
        ]
        if not matching_sheets:
            # Report immediately as unplaced due to thickness mismatch
            unplaced_report.append({
                "part_id": part.id,
                "part_name": part.name,
                "path": part.path,
                "required_quantity": part.quantity,
                "placed_quantity": 0,
                "unplaced_quantity": part.quantity,
                "thickness": part.thickness,
                "priority": part.priority,
                "priority_order": part.priority_order,
                "reason": "No stock sheet with compatible thickness.",
            })
            continue

        # Check if part is larger than ALL compatible sheets
        fits_any = any(
            (part.width + spacing <= s.width and part.height + spacing <= s.height) or
            (allow_rotate and part.height + spacing <= s.width and part.width + spacing <= s.height)
            for s in matching_sheets
        )
        if not fits_any:
            unplaced_report.append({
                "part_id": part.id,
                "part_name": part.name,
                "path": part.path,
                "required_quantity": part.quantity,
                "placed_quantity": 0,
                "unplaced_quantity": part.quantity,
                "thickness": part.thickness,
                "priority": part.priority,
                "priority_order": part.priority_order,
                "reason": "The part is larger than every compatible stock sheet.",
            })
            continue

        # Group by nominal matched thickness
        nominal_t = round(part.thickness, 3)
        thickness_groups.setdefault(nominal_t, []).append(part)

    # ── 3. Nesting Execution per Thickness Group ──────────────────────────────
    generated_sheets: List[Dict[str, Any]] = []

    # Sort thickness groups by the highest priority part in each group
    sorted_thickness_items = sorted(
        thickness_groups.items(),
        key=lambda item: min(p.priority_order for p in item[1])
    )

    for t_val, group_parts in sorted_thickness_items:
        # Compatible stock sheets for this thickness
        compat_stock = [
            s for s in normalized_sheets
            if abs(t_val - s.thickness) < 0.001
        ]

        # Sorting: Primary sort key requirement:
        # 1. priority_order ascending
        # 2. priority level: High (0) before Normal (1) before Low (2)
        # 3. part area descending
        # 4. largest dimension descending
        # 5. original list index tie breaker
        def part_sort_key(item_with_idx):
            idx, p = item_with_idx
            p_level = PRIORITY_LEVEL_MAP.get(p.priority.upper(), 1)
            return (p.priority_order, p_level, -p.area, -p.max_dimension, idx)

        indexed_parts = list(enumerate(group_parts))
        if nesting_mode == "Finish priority parts first":
            indexed_parts.sort(key=part_sort_key)
        else: # Optimize material usage mode
            indexed_parts.sort(key=lambda x: (x[1].priority_order, -x[1].area, -x[1].max_dimension, x[0]))

        sorted_parts = [p for _, p in indexed_parts]

        # Expand part instances: list of (part, instance_idx)
        instances_to_place = []
        for part in sorted_parts:
            for inst in range(part.quantity):
                instances_to_place.append((part, inst))

        # Active sheets created for this thickness
        open_sheets: List[Dict[str, Any]] = []

        current_priority_order = None
        group_incomplete = False

        for part, inst_idx in instances_to_place:
            if group_incomplete and not continue_on_incomplete:
                break

            if current_priority_order is None or part.priority_order != current_priority_order:
                current_priority_order = part.priority_order

            placed_instance = False

            # 1. Try to place on an existing open sheet of matching thickness
            for s_inst in open_sheets:
                candidate_instances = s_inst["instances"] + [(part, inst_idx)]
                placements = _try_pack_parts_on_sheet(
                    sheet_width=s_inst["stock_sheet"].width,
                    sheet_height=s_inst["stock_sheet"].height,
                    part_instances=candidate_instances,
                    spacing=spacing,
                    allow_rotate=allow_rotate,
                )
                if placements is not None:
                    s_inst["instances"] = candidate_instances
                    s_inst["placements"] = placements
                    part.placed_quantity += 1
                    placed_instance = True
                    if part.priority_order != s_inst["priority_order"]:
                        s_inst["has_mixed"] = True
                    break

            if placed_instance:
                continue

            # 2. Open a new stock sheet if available
            usable_sheets = [
                s for s in compat_stock
                if s.remaining_quantity > 0
            ]
            # Prefer sheets sorted by area
            usable_sheets.sort(key=lambda s: s.width * s.height)

            for chosen_sheet in usable_sheets:
                placements = _try_pack_parts_on_sheet(
                    sheet_width=chosen_sheet.width,
                    sheet_height=chosen_sheet.height,
                    part_instances=[(part, inst_idx)],
                    spacing=spacing,
                    allow_rotate=allow_rotate,
                )
                if placements is not None:
                    chosen_sheet.used_quantity += 1
                    s_inst = {
                        "stock_sheet": chosen_sheet,
                        "instances": [(part, inst_idx)],
                        "placements": placements,
                        "priority_order": part.priority_order,
                        "priority_level": part.priority,
                        "has_mixed": False,
                    }
                    open_sheets.append(s_inst)
                    part.placed_quantity += 1
                    placed_instance = True
                    break

            if not placed_instance:
                group_incomplete = True

        # Process unplaced counts for parts in this group
        for part in sorted_parts:
            unplaced = part.unplaced_quantity
            if unplaced > 0 and not any(r["part_id"] == part.id for r in unplaced_report):
                compat_stock_avail = [s for s in compat_stock if s.remaining_quantity > 0]
                if not compat_stock_avail:
                    reason = "All compatible stock sheets have been exhausted."
                else:
                    reason = "Available stock quantity exhausted or part cannot fit within remaining sheet areas."

                unplaced_report.append({
                    "part_id": part.id,
                    "part_name": part.name,
                    "path": part.path,
                    "required_quantity": part.quantity,
                    "placed_quantity": part.placed_quantity,
                    "unplaced_quantity": unplaced,
                    "thickness": part.thickness,
                    "priority": part.priority,
                    "priority_order": part.priority_order,
                    "reason": reason,
                })

        # Save generated sheets for this thickness group (Filter out empty sheets)
        for s_inst in open_sheets:
            placements = s_inst["placements"]
            if not placements:
                continue

            sheet = s_inst["stock_sheet"]
            util_pct = sheet_utilization(placements, sheet.width, sheet.height)
            waste_pct = round(100.0 - util_pct, 2)
            util_pct = round(util_pct, 2)

            generated_sheets.append({
                "stock_sheet": sheet,
                "placements": placements,
                "utilization": util_pct,
                "waste": waste_pct,
                "priority_order": s_inst["priority_order"],
                "priority_level": s_inst["priority_level"],
                "has_mixed": s_inst["has_mixed"],
            })

    # Order generated sheets by production priority (highest priority work first)
    generated_sheets.sort(key=lambda s: (s["priority_order"], PRIORITY_LEVEL_MAP.get(str(s["priority_level"]).upper(), 1), s["stock_sheet"].thickness))

    # Save output DXF files
    committed_sheet_files = []
    block_cache = {}

    for idx, g_sheet in enumerate(generated_sheets, start=1):
        sheet = g_sheet["stock_sheet"]
        placements = g_sheet["placements"]

        dxf_filename = f"nested_sheet_{idx:03d}.dxf"
        output_dxf_path = os.path.join(output_dir, dxf_filename)

        out_doc = ezdxf.new("R2010")
        out_msp = out_doc.modelspace()

        for p in placements:
            # Find the matching NestablePart object to pass to entity copy helper
            matching_part = next(
                (np for np in normalized_parts if str(np.path) == str(p["part"])),
                None
            )
            if matching_part is None:
                # Build a minimal stub if not found
                class _PartStub:
                    min_x = 0.0; min_y = 0.0
                matching_part = _PartStub()

            _copy_entities_to_msp(
                out_msp=out_msp,
                source_path=p["part"],
                offset_x=p["x"],
                offset_y=p["y"],
                rotation_deg=p["rotation"],
                part=matching_part,
            )

        # Draw sheet border
        border_pts = [
            (0, 0),
            (sheet.width, 0),
            (sheet.width, sheet.height),
            (0, sheet.height),
            (0, 0),
        ]
        out_msp.add_lwpolyline(border_pts, dxfattribs={"layer": "SHEET_BORDER", "color": 3})

        out_doc.saveas(output_dxf_path)
        g_sheet["sheet_number"] = idx
        g_sheet["dxf_path"] = output_dxf_path
        g_sheet["dxf_filename"] = dxf_filename
        committed_sheet_files.append(output_dxf_path)

    # ── 4. Calculate Comprehensive Summary ───────────────────────────────────
    total_required = sum(p.quantity for p in normalized_parts)
    total_placed = sum(p.placed_quantity for p in normalized_parts)
    total_unplaced = sum(r["unplaced_quantity"] for r in unplaced_report)

    # Stock usage summary
    stock_usage = []
    for s in normalized_sheets:
        s_used_sheets = [g for g in generated_sheets if g["stock_sheet"].id == s.id]
        if s_used_sheets:
            avg_util = round(sum(g["utilization"] for g in s_used_sheets) / len(s_used_sheets), 2)
            avg_waste = round(100.0 - avg_util, 2)
        else:
            avg_util = 0.0
            avg_waste = 0.0

        stock_usage.append({
            "stock_id": s.id,
            "name": s.name,
            "material": s.material,
            "width": s.width,
            "height": s.height,
            "thickness": s.thickness,
            "available_quantity": s.available_quantity,
            "unlimited_quantity": s.unlimited_quantity,
            "used_quantity": s.used_quantity,
            "remaining_quantity": s.remaining_quantity,
            "average_utilization": avg_util,
            "average_waste": avg_waste,
        })

    # Priority completion breakdown by Priority Order
    priority_groups_dict: Dict[int, Dict[str, Any]] = {}
    for p in normalized_parts:
        po = p.priority_order
        if po not in priority_groups_dict:
            priority_groups_dict[po] = {
                "priority_order": po,
                "required": 0,
                "placed": 0,
                "unplaced": 0,
                "status": "Incomplete",
            }
        priority_groups_dict[po]["required"] += p.quantity
        priority_groups_dict[po]["placed"] += p.placed_quantity

    for r in unplaced_report:
        po = r["priority_order"]
        if po in priority_groups_dict:
            priority_groups_dict[po]["unplaced"] += r["unplaced_quantity"]

    priority_completion = []
    completed_groups = 0
    incomplete_groups = 0

    for po in sorted(priority_groups_dict.keys()):
        g = priority_groups_dict[po]
        if g["placed"] == g["required"]:
            g["status"] = "Complete"
            completed_groups += 1
        else:
            g["status"] = "Incomplete"
            incomplete_groups += 1
        priority_completion.append(g)

    # Production-ready sheets list
    production_ready_sheets = [
        {
            "sheet_number": g["sheet_number"],
            "dxf_filename": g["dxf_filename"],
            "priority_order": g["priority_order"],
            "priority_level": g["priority_level"],
            "utilization": g["utilization"],
        }
        for g in generated_sheets
    ]

    total_sheets_used = len(generated_sheets)
    if generated_sheets:
        total_utilization = round(sum(g["utilization"] for g in generated_sheets) / total_sheets_used, 2)
        total_waste = round(100.0 - total_utilization, 2)
    else:
        total_utilization = 0.0
        total_waste = 0.0

    summary_result = {
        "output_dir": output_dir,
        "total_parts_required": total_required,
        "total_parts_placed": total_placed,
        "total_parts_unplaced": total_unplaced,
        "total_sheets_used": total_sheets_used,
        "total_utilization": total_utilization,
        "total_waste": total_waste,
        "completed_priority_groups": completed_groups,
        "incomplete_priority_groups": incomplete_groups,
        "priority_completion": priority_completion,
        "production_ready_sheets": production_ready_sheets,
        "stock_usage": stock_usage,
        "unplaced_parts": unplaced_report,
        "sheets": [
            {
                "sheet_number": g["sheet_number"],
                "dxf_path": g["dxf_path"],
                "dxf_filename": g["dxf_filename"],
                "stock_sheet_id": g["stock_sheet"].id,
                "stock_sheet_name": g["stock_sheet"].name,
                "material": g["stock_sheet"].material,
                "width": g["stock_sheet"].width,
                "height": g["stock_sheet"].height,
                "thickness": g["stock_sheet"].thickness,
                "utilization": g["utilization"],
                "waste": g["waste"],
                "priority_order": g["priority_order"],
                "priority_level": g["priority_level"],
                "has_mixed_priority": g["has_mixed"],
                "placed_parts": g["placements"],
            }
            for g in generated_sheets
        ],
    }

    # Save machine-readable summary JSON
    json_path = os.path.join(output_dir, "nesting_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_result, f, indent=2)

    return summary_result
