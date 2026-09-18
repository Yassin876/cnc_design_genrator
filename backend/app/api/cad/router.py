from fastapi import APIRouter, HTTPException, Query, Body
import os
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from backend.app.schemas.schemas import NestingRequest, StockSheetSchema
from backend.app.core.database import DatabaseManager
from core.pipeline_manager import PipelineManager

from backend.app.core.dxf_editor import dxf_to_json, apply_edits


router = APIRouter(prefix="/cad", tags=["CAD"])
db = DatabaseManager()
pipeline_mgr = PipelineManager(db)

class ParseDXFRequest(BaseModel):
    file_path: str

class ParseDXFContentRequest(BaseModel):
    dxf_content: str

@router.get("/parse-dxf")
def parse_dxf_get(file_path: str = Query(...)):
    return parse_dxf_internal(file_path)

@router.post("/parse-dxf")
def parse_dxf_post(req: ParseDXFRequest):
    return parse_dxf_internal(req.file_path)

@router.post("/parse-dxf-content")
def parse_dxf_content(req: ParseDXFContentRequest):
    # DXF parsing using dxf_editor from main_backend
    try:
        # Save DXF content to a temporary file for parsing
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.dxf', delete=False) as f:
            f.write(req.dxf_content)
            temp_path = f.name
        
        try:
            data = dxf_to_json(temp_path)
            entities = data.get("entities", data) if isinstance(data, dict) else data
            return {"status": "SUCCESS", "entities": entities, "layers": data.get("layers", []) if isinstance(data, dict) else []}
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse DXF content: {str(e)}")

from backend.app.core.config import settings

def parse_dxf_internal(file_path: str):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        # Fallback check in storage outputs or uploads
        if os.path.exists(os.path.join(settings.OUTPUT_DIR, file_path)):
            abs_path = os.path.abspath(os.path.join(settings.OUTPUT_DIR, file_path))
        elif os.path.exists(os.path.join(settings.UPLOAD_DIR, file_path)):
            abs_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, file_path))
        elif os.path.exists(os.path.join("storage", "outputs", file_path)):
            abs_path = os.path.abspath(os.path.join("storage", "outputs", file_path))
        elif os.path.exists(os.path.join("storage", "uploads", file_path)):
            abs_path = os.path.abspath(os.path.join("storage", "uploads", file_path))
        else:
            raise HTTPException(status_code=404, detail=f"DXF file not found: {file_path}")
    try:
        # DXF parsing using dxf_editor from main_backend
        data = dxf_to_json(abs_path)
        entities = data.get("entities", data) if isinstance(data, dict) else data
        return {"status": "SUCCESS", "file_path": abs_path, "entities": entities, "layers": data.get("layers", []) if isinstance(data, dict) else []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse DXF: {str(e)}")

@router.get("/inspect-3d")
def inspect_3d_mesh(file_path: str = Query(...)):
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        if os.path.exists(os.path.join(settings.OUTPUT_DIR, file_path)):
            abs_path = os.path.abspath(os.path.join(settings.OUTPUT_DIR, file_path))
        elif os.path.exists(os.path.join(settings.UPLOAD_DIR, file_path)):
            abs_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, file_path))
        elif os.path.exists(os.path.join("storage", "outputs", file_path)):
            abs_path = os.path.abspath(os.path.join("storage", "outputs", file_path))
        elif os.path.exists(os.path.join("storage", "uploads", file_path)):
            abs_path = os.path.abspath(os.path.join("storage", "uploads", file_path))
        else:
            print(f"[inspect-3d] ERROR: 3D file not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"3D file not found: {file_path}")
    try:
        import trimesh
        mesh = trimesh.load(abs_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        bounds = mesh.bounds
        extents = mesh.extents
        center = mesh.centroid

        print(f"[inspect-3d] INFO: Successfully inspected {os.path.basename(abs_path)} - {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")

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
        print(f"[inspect-3d] ERROR: Failed to inspect 3D mesh: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to inspect 3D mesh: {str(e)}")

import uuid

def _execute_nesting(req: NestingRequest) -> Dict[str, Any]:
    from core.nesting import StockSheet, NestablePart, nest_parts

    sheet_thickness = req.sheet_thickness if req.sheet_thickness is not None else 18.0
    stock_sheets = [
        StockSheet(
            name="Stock Sheet 1",
            material="Default",
            width=req.sheet_width if req.sheet_width is not None else 1200.0,
            height=req.sheet_height if req.sheet_height is not None else 600.0,
            thickness=sheet_thickness,
            available_quantity=10,
            unlimited_quantity=True,
        )
    ]

    def resolve_part_path(raw_path: str) -> str:
        if not raw_path:
            return raw_path
        if os.path.isabs(raw_path) and os.path.isfile(raw_path):
            return raw_path
        if os.path.isfile(raw_path):
            return os.path.abspath(raw_path)
        
        # Get project root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        
        # Try multiple locations strictly inside storage
        folders = [
            os.path.join(project_root, "storage", "uploads"),
            os.path.join(project_root, "storage", "outputs"),
        ]


        
        for folder in folders:
            candidate = os.path.join(folder, raw_path)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
            fname = os.path.basename(raw_path)
            by_name = os.path.join(folder, fname)
            if os.path.isfile(by_name):
                return os.path.abspath(by_name)
        
        # Return original if not found
        return raw_path

    nestable_parts = []
    for item in req.part_paths:
        if isinstance(item, str):
            if ("SECTION" in item and "ENTITIES" in item) or item.startswith("0\nSECTION"):
                temp_dir = os.path.abspath(os.path.join("storage", "temp"))
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f"in_memory_{uuid.uuid4().hex[:8]}.dxf")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(item)
                nestable_parts.append(NestablePart(path=temp_file, quantity=1, thickness=sheet_thickness))
            else:
                nestable_parts.append(
                    NestablePart(path=resolve_part_path(item), quantity=1, thickness=sheet_thickness)
                )
        elif isinstance(item, dict):
            part_thickness = item.get("thickness")
            if part_thickness is None:
                part_thickness = sheet_thickness

            raw_path = item.get("path", "")
            dxf_content = item.get("dxf_content") or item.get("content")
            if (not raw_path or not os.path.isfile(raw_path)) and dxf_content:
                temp_dir = os.path.abspath(os.path.join("storage", "temp"))
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f"in_memory_{uuid.uuid4().hex[:8]}.dxf")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(dxf_content)
                part_path = temp_file
            else:
                part_path = resolve_part_path(raw_path)

            nestable_parts.append(
                NestablePart(
                    path=part_path,
                    quantity=item.get("quantity", 1),
                    thickness=part_thickness,
                    priority=item.get("priority", "Normal"),
                    priority_order=item.get("priority_order", 100),
                    name=item.get("name", ""),
                )
            )

    if not nestable_parts:
        raise ValueError("No valid parts provided for nesting.")

    output_dir = os.path.abspath(os.path.join("storage", "outputs", "nesting_results"))
    os.makedirs(output_dir, exist_ok=True)

    result = nest_parts(
        parts=nestable_parts,
        stock_sheets=stock_sheets,
        spacing=req.spacing if req.spacing is not None else 5.0,
        allow_rotate=req.allow_rotate if req.allow_rotate is not None else True,
        nesting_mode="Finish priority parts first",
        output_dir=output_dir,
    )

    for sheet in result.get("sheets", []):
        if "dxf_path" in sheet:
            sheet["dxf_path"] = os.path.abspath(sheet["dxf_path"])
            sheet.setdefault("sheet_name", sheet.get("stock_sheet_name") or f"Sheet {sheet.get('sheet_number', 1)}")
            sheet.setdefault("sheet_index", sheet.get("sheet_number", 1))
            sheet.setdefault("parts_count", len(sheet.get("placed_parts") or []))

    return result


@router.post("/nesting")
def run_nesting(req: NestingRequest):
    try:
        return _execute_nesting(req)
    except Exception as e:
        import traceback

        print(f"Nesting execution failed: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Nesting execution failed: {str(e)}")


@router.post("/nesting/optimize")
async def optimize_nesting(req: NestingRequest):
    """Local nesting optimization; forwards to nesting worker when USE_NESTING_WORKER=1."""
    use_worker = os.getenv("USE_NESTING_WORKER", "").strip() in ("1", "true", "yes")
    if use_worker:
        import httpx
        from backend.app.core.config import settings

        worker_url = settings.NESTING_WORKER_URL.rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                health = await client.get(f"{worker_url}/health")
                health.raise_for_status()
                nest_resp = await client.post(
                    f"{worker_url}/nest",
                    json={
                        "part_files_urls": req.part_paths,
                        "stock_sheets": [
                            {
                                "width": req.sheet_width or 1200.0,
                                "height": req.sheet_height or 600.0,
                                "thickness": 3.0,
                            }
                        ],
                        "spacing": req.spacing or 5.0,
                        "allow_rotate": req.allow_rotate if req.allow_rotate is not None else True,
                    },
                )
                nest_resp.raise_for_status()
                return nest_resp.json()
        except Exception as worker_err:
            print(f"[nesting/optimize] Worker forward failed, falling back to local: {worker_err}")

    try:
        return _execute_nesting(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Nesting optimization failed: {str(e)}")

