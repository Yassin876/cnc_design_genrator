import uuid
import os
import sys
import tempfile
import logging
import requests
from typing import Dict, Any, Optional

def _harden_stdio() -> None:
    """Hidden Windows processes can have a broken stdout; print() then raises Errno 22."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        try:
            if stream is not None:
                stream.write("")
                stream.flush()
        except OSError:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8", errors="replace"))

_harden_stdio()

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response, status, Header
from pydantic import BaseModel

from app.routing import route_and_generate
from app.flux_gen import FluxGenerator
log = logging.getLogger("ai_server_2d")

app = FastAPI(title="CAD Studio — 2D AI Server Microservice")
flux_gen = FluxGenerator()

jobs_db: Dict[str, Dict[str, Any]] = {}

class GenerationParams(BaseModel):
    material_thickness_mm: Optional[float] = None
    part_width_mm: Optional[float] = 0.0
    part_height_mm: Optional[float] = 0.0
    tool_diameter_mm: Optional[float] = 0.0

class ImageGenRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = None
    params: GenerationParams

class TextGenRequest(BaseModel):
    prompt: str
    params: GenerationParams

class Internal2DRequest(BaseModel):
    """Synchronous contract used by the main backend's 2D adapter."""
    prompt: Optional[str] = None
    image_path: Optional[str] = None
    params: dict = {}
    output_path: str

def _verify_internal_key(key: Optional[str]) -> None:
    expected = os.getenv("INTERNAL_API_KEY", "cad_studio_internal_secret_2026")
    if expected and key != expected:
        raise HTTPException(status_code=403, detail="Invalid internal API key")

async def _generate_internal(req: Internal2DRequest, internal_key: Optional[str]) -> dict:
    _verify_internal_key(internal_key)
    if not req.output_path:
        raise HTTPException(status_code=400, detail="output_path is required")
    if req.image_path:
        if not os.path.isfile(req.image_path):
            raise HTTPException(status_code=404, detail="Input image file not found")
        image_path = req.image_path
    else:
        if not req.prompt or not req.prompt.strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        generated = flux_gen.generate_image(req.prompt)
        temp_dir = tempfile.mkdtemp(prefix="txt2d_")
        image_path = os.path.join(temp_dir, "prompt.png")
        generated.save(image_path)
    try:
        output_path = await route_and_generate(image_path, req.output_path, req.prompt, req.params or {})
        return {
            "status": "completed",
            "message": "2D DXF generation completed",
            "output_file_path": output_path,
            "output_filename": os.path.basename(output_path),
        }
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        if "contour" in detail.lower() or "potrace" in detail.lower():
            raise HTTPException(
                status_code=422,
                detail=(
                    "Could not detect a clear CNC-ready shape in the image. "
                    "Upload a high-contrast silhouette and try again."
                ),
            ) from exc
        raise HTTPException(status_code=500, detail=f"2D generation failed: {exc}") from exc

@app.post("/api/2d/generate-from-prompt")
async def internal_text_to_2d(req: Internal2DRequest, x_internal_key: Optional[str] = Header(default=None)):
    return await _generate_internal(req, x_internal_key)

@app.post("/api/2d/generate-from-image")
async def internal_image_to_2d(req: Internal2DRequest, x_internal_key: Optional[str] = Header(default=None)):
    return await _generate_internal(req, x_internal_key)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ai_server_2d", "api_revision": "2d-contract-v2"}

async def run_image_gen_job(job_id: str, image_path: str, prompt: Optional[str], params: dict):
    jobs_db[job_id]["status"] = "processing"
    temp_dir = tempfile.mkdtemp(prefix=f"gen2d_{job_id}_")
    output_path = os.path.join(temp_dir, "output.dxf")
    
    try:
        res_dxf = await route_and_generate(image_path, output_path, prompt, params)
        jobs_db[job_id]["status"] = "completed"
        jobs_db[job_id]["result"] = {"dxf_path": res_dxf}
    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)

@app.post("/generate/image")
async def generate_from_image(req: ImageGenRequest, background_tasks: BackgroundTasks, response: Response):
    if req.params.material_thickness_mm is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "MISSING_MATERIAL_THICKNESS", "message": "material_thickness_mm is required"}
        )
        
    job_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp(prefix=f"dl_{job_id}_")
    
    # Download or copy image
    img_path = os.path.join(temp_dir, "input_img.png")
    if req.image_url.startswith("http://") or req.image_url.startswith("https://"):
        resp = requests.get(req.image_url, timeout=30)
        resp.raise_for_status()
        with open(img_path, "wb") as f:
            f.write(resp.content)
    elif os.path.exists(req.image_url):
        import shutil
        shutil.copy2(req.image_url, img_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image URL or local file path not found: {req.image_url}"
        )
        
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_image_gen_job, job_id, img_path, req.prompt, req.params.dict())
    return {"job_id": job_id, "status": "queued"}

@app.post("/generate/text")
async def generate_from_text(req: TextGenRequest, background_tasks: BackgroundTasks, response: Response):
    if req.params.material_thickness_mm is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "MISSING_MATERIAL_THICKNESS", "message": "material_thickness_mm is required"}
        )
        
    job_id = str(uuid.uuid4())
    temp_dir = tempfile.mkdtemp(prefix=f"txt_{job_id}_")
    
    # Generate image via Flux
    img = flux_gen.generate_image(req.prompt)
    img_path = os.path.join(temp_dir, "flux_gen.png")
    img.save(img_path)
    
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_image_gen_job, job_id, img_path, req.prompt, req.params.dict())
    return {"job_id": job_id, "status": "queued"}

@app.get("/generate/{job_id}")
def get_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]
