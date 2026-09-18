from fastapi import APIRouter, HTTPException
import os
import shutil
from backend.app.schemas.schemas import ExportRequest
from backend.app.core.config import settings
from core.paths import (
    STORAGE_DIR as CORE_STORAGE_DIR,
    OUTPUT_DIR as CORE_OUTPUT_DIR,
    UPLOAD_DIR as CORE_UPLOAD_DIR,
)

router = APIRouter(prefix="/export", tags=["Export"])

STORAGE_DIR = os.path.abspath(str(CORE_STORAGE_DIR))
OUTPUT_DIR = os.path.abspath(str(CORE_OUTPUT_DIR))
UPLOAD_DIR = os.path.abspath(str(CORE_UPLOAD_DIR))

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)


def is_safe_storage_path(target_path: str, base_dir: str = STORAGE_DIR) -> bool:
    """Verifies that target_path is strictly within base_dir using path commonality."""
    try:
        abs_target = os.path.abspath(target_path)
        abs_base = os.path.abspath(base_dir)
        return os.path.commonpath([abs_target, abs_base]) == abs_base
    except (ValueError, OSError):
        return False



@router.post("")
@router.post("/export-cad")
def export_file(req: ExportRequest):
    clean_in = req.input_file_path.lstrip("/\\")
    candidates = [
        os.path.abspath(os.path.join(OUTPUT_DIR, clean_in)),
        os.path.abspath(os.path.join(UPLOAD_DIR, clean_in)),
        os.path.abspath(os.path.join(OUTPUT_DIR, os.path.basename(req.input_file_path))),
        os.path.abspath(os.path.join(UPLOAD_DIR, os.path.basename(req.input_file_path))),
    ]
    if os.path.isabs(req.input_file_path):
        candidates.insert(0, os.path.abspath(req.input_file_path))

    input_path = None
    for p in candidates:
        if is_safe_storage_path(p) and os.path.exists(p) and os.path.isfile(p):
            input_path = p
            break

    if not input_path:
        raise HTTPException(status_code=404, detail=f"Input file not found in authorized storage: {req.input_file_path}")
        
    ext = req.export_format.lower().strip(".")
    stem = os.path.splitext(os.path.basename(input_path))[0]
    out_filename = f"{stem}_exported.{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        input_ext = os.path.splitext(input_path)[1].lower().strip(".")
        if input_ext == ext:
            shutil.copy2(input_path, out_path)
        else:
            import trimesh
            mesh = trimesh.load(input_path)
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)
            mesh.export(out_path)

        if req.dest_path:
            dest_abs = os.path.abspath(req.dest_path)
            if not is_safe_storage_path(dest_abs):
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: dest_path must reside within authorized storage directory."
                )
            dest_dir = os.path.dirname(dest_abs)
            if dest_dir:
                os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(out_path, dest_abs)
            out_path = dest_abs


        return {
            "status": "SUCCESS",
            "export_format": ext.upper(),
            "export_path": out_path,
            "filename": os.path.basename(out_path),
            "file_size_bytes": os.path.getsize(out_path)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

