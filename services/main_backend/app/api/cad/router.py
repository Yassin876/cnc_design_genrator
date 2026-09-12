from fastapi import APIRouter, HTTPException, Query, Body
import os
import trimesh
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.schemas import NestingRequest, StockSheetSchema
from app.core.database import DatabaseManager
from app.core.pipeline_manager import PipelineManager
from app.core.dxf_editor import dxf_to_json

router = APIRouter(prefix="/cad", tags=["CAD"])
db = DatabaseManager()
pipeline_mgr = PipelineManager(db)

class ParseDXFRequest(BaseModel):
    file_path: str

@router.get("/parse-dxf")
def parse_dxf_get(file_path: str = Query(...)):
    return parse_dxf_internal(file_path)

@router.post("/parse-dxf")
def parse_dxf_post(req: ParseDXFRequest):
    return parse_dxf_internal(req.file_path)

def parse_dxf_internal(file_path: str):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        # Fallback check in uploads or outputs
        if os.path.exists(os.path.join("outputs", file_path)):
            abs_path = os.path.abspath(os.path.join("outputs", file_path))
        elif os.path.exists(os.path.join("uploads", file_path)):
            abs_path = os.path.abspath(os.path.join("uploads", file_path))
        else:
            raise HTTPException(status_code=404, detail=f"DXF file not found: {file_path}")
    try:
        data = dxf_to_json(abs_path)
        return {"status": "SUCCESS", "file_path": abs_path, "entities": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse DXF: {str(e)}")

@router.get("/inspect-3d")
def inspect_3d_mesh(file_path: str = Query(...)):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        if os.path.exists(os.path.join("outputs", file_path)):
            abs_path = os.path.abspath(os.path.join("outputs", file_path))
        elif os.path.exists(os.path.join("uploads", file_path)):
            abs_path = os.path.abspath(os.path.join("uploads", file_path))
        else:
            raise HTTPException(status_code=404, detail=f"3D file not found: {file_path}")
    try:
        mesh = trimesh.load(abs_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
        
        bounds = mesh.bounds
        extents = mesh.extents
        center = mesh.centroid

        return {
            "file_name": os.path.basename(abs_path),
            "vertices_count": len(mesh.vertices),
            "faces_count": len(mesh.faces),
            "is_watertight": bool(mesh.is_watertight),
            "volume_mm3": float(mesh.volume) if mesh.is_watertight else 0.0,
            "surface_area_mm2": float(mesh.area),
            "bounding_box": {
                "min": bounds[0].tolist(),
                "max": bounds[1].tolist(),
                "dimensions": {
                    "width": float(extents[0]),
                    "height": float(extents[1]),
                    "depth": float(extents[2])
                },
                "center": center.tolist()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to inspect 3D mesh: {str(e)}")

@router.post("/nesting")
def run_nesting(req: NestingRequest):
    try:
        from app.core.nesting import StockSheet, NestablePart, nest_parts

        # Build stock sheets from request (new format) or fall back to legacy sheet_width/sheet_height
        if req.stock_sheets and len(req.stock_sheets) > 0:
            stock_sheets = [
                StockSheet(
                    sheet_id=s.id,
                    name=s.name or "",
                    material=s.material or "Default",
                    width=s.width,
                    height=s.height,
                    thickness=s.thickness,
                    available_quantity=s.available_quantity if s.available_quantity is not None else 10,
                    unlimited_quantity=s.unlimited_quantity if s.unlimited_quantity is not None else True,
                )
                for s in req.stock_sheets
            ]
        else:
            # Legacy single-sheet fallback
            stock_sheets = [
                StockSheet(
                    name="Stock Sheet 1",
                    material="Default",
                    width=req.sheet_width if req.sheet_width is not None else 1200.0,
                    height=req.sheet_height if req.sheet_height is not None else 600.0,
                    thickness=3.0,
                    available_quantity=10,
                    unlimited_quantity=True,
                )
            ]


        def resolve_part_path(raw_path: str) -> str:
            """Try to locate the DXF file from an absolute or relative path."""
            if os.path.isabs(raw_path) and os.path.isfile(raw_path):
                return raw_path
            # Try as-is (relative to cwd)
            if os.path.isfile(raw_path):
                return os.path.abspath(raw_path)
            # Try relative to uploads/
            up = os.path.join("uploads", raw_path)
            if os.path.isfile(up):
                return os.path.abspath(up)
            # Try relative to outputs/
            op = os.path.join("outputs", raw_path)
            if os.path.isfile(op):
                return os.path.abspath(op)
            # Try just the filename inside uploads/
            fname = os.path.basename(raw_path)
            for folder in ("uploads", "outputs"):
                candidate = os.path.join(folder, fname)
                if os.path.isfile(candidate):
                    return os.path.abspath(candidate)
            # Return original and let nest_parts raise the proper error
            return raw_path

        # Parse part paths or NestablePart dicts
        nestable_parts = []
        for item in req.part_paths:
            if isinstance(item, str):
                nestable_parts.append(NestablePart(path=resolve_part_path(item), quantity=1))
            elif isinstance(item, dict):
                nestable_parts.append(NestablePart(
                    path=resolve_part_path(item.get("path", "")),
                    quantity=item.get("quantity", 1),
                    thickness=item.get("thickness", 3.0),
                    priority=item.get("priority", "Normal"),
                    priority_order=item.get("priority_order", 100),
                    name=item.get("name", "")
                ))
            elif hasattr(item, "path"):
                nestable_parts.append(item)


        output_dir = os.path.abspath(os.path.join("uploads", "nesting_results"))
        os.makedirs(output_dir, exist_ok=True)

        result = nest_parts(
            parts=nestable_parts,
            stock_sheets=stock_sheets,
            spacing=req.spacing if req.spacing is not None else 5.0,
            allow_rotate=req.allow_rotate if req.allow_rotate is not None else True,
            nesting_mode=req.nesting_mode if req.nesting_mode else "Finish priority parts first",
            output_dir=output_dir,
        )

        for sheet in result.get("sheets", []):
            if "dxf_path" in sheet:
                sheet["dxf_path"] = os.path.abspath(sheet["dxf_path"])

        return result
    except Exception as e:
        import traceback
        print(f"Nesting execution failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Nesting execution failed: {str(e)}")

