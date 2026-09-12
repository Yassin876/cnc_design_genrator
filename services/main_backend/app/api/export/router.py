from fastapi import APIRouter, HTTPException
import os
import shutil
import trimesh
from app.schemas.schemas import ExportRequest

router = APIRouter(prefix="/export", tags=["Export"])

OUTPUT_DIR = os.path.abspath("outputs")
UPLOAD_DIR = os.path.abspath("uploads")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
@router.post("/export-cad")
def export_file(req: ExportRequest):
    input_path = req.input_file_path
    if not os.path.exists(input_path):
        if os.path.exists(os.path.join(OUTPUT_DIR, input_path)):
            input_path = os.path.join(OUTPUT_DIR, input_path)
        elif os.path.exists(os.path.join(UPLOAD_DIR, input_path)):
            input_path = os.path.join(UPLOAD_DIR, input_path)
        elif os.path.exists(os.path.join(OUTPUT_DIR, os.path.basename(input_path))):
            input_path = os.path.join(OUTPUT_DIR, os.path.basename(input_path))
        else:
            raise HTTPException(status_code=404, detail=f"Input file not found: {req.input_file_path}")
        
    ext = req.export_format.lower().strip(".")
    stem = os.path.splitext(os.path.basename(input_path))[0]
    out_filename = f"{stem}_exported.{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        input_ext = os.path.splitext(input_path)[1].lower().strip(".")
        if input_ext == ext:
            shutil.copy2(input_path, out_path)
        else:
            mesh = trimesh.load(input_path)
            if isinstance(mesh, trimesh.Scene):
                mesh = mesh.dump(concatenate=True)
            mesh.export(out_path)

        if req.dest_path:
            try:
                dest_dir = os.path.dirname(req.dest_path)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)
                shutil.copy2(out_path, req.dest_path)
                out_path = req.dest_path
            except Exception as copy_err:
                print(f"Warning: Could not copy export to dest_path ({copy_err}). Output remains at {out_path}")

        return {
            "status": "SUCCESS",
            "export_format": ext.upper(),
            "export_path": out_path,
            "filename": os.path.basename(out_path),
            "file_size_bytes": os.path.getsize(out_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
