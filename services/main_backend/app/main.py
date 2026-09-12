import os
import uuid
import logging
import httpx
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Header, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.schemas.orchestrator_schemas import (
    ImageGenRequestSchema,
    TextGenRequestSchema,
    EditRequestSchema,
    NestRequestSchema,
    JobStatusResponseSchema
)

# Import sub-routers from merged desktop_app backend modules
from app.api.auth.router import router as auth_router
from app.api.projects.router import router as projects_router
from app.api.generation.router import router as generation_router
from app.api.editing.router import router as editing_router
from app.api.cad.router import router as cad_router
from app.api.files.router import router as files_router
from app.api.validation.router import router as validation_router
from app.api.export.router import router as export_router

from app.db.session import engine
from app.db.base import Base
import app.models  # Ensure models are registered with Base

app = FastAPI(title="CAD Studio — Main Backend Orchestrator")

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# Enable CORS for desktop app & web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api/v1 to match frontend API calls
API_V1 = "/api/v1"
app.include_router(auth_router,       prefix=API_V1, tags=["Auth"])
app.include_router(projects_router,   prefix=API_V1, tags=["Projects"])
app.include_router(files_router,      prefix=API_V1, tags=["Files"])
app.include_router(cad_router,        prefix=API_V1, tags=["CAD"])
app.include_router(generation_router, prefix=API_V1, tags=["Generation"])
app.include_router(editing_router,    prefix=API_V1, tags=["Editing"])
app.include_router(validation_router, prefix=API_V1, tags=["Validation"])
app.include_router(export_router,     prefix=API_V1, tags=["Export"])

AI_SERVER_2D_URL = os.getenv("AI_SERVER_2D_URL", "http://localhost:8001")
EDIT_SERVER_URL = os.getenv("EDIT_SERVER_URL", "http://localhost:8002")
NESTING_WORKER_URL = os.getenv("NESTING_WORKER_URL", "http://localhost:8003")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "internal-secret-key")

# In-memory mapping of Gateway job_id to target service job_id
jobs_db: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "main_backend", "auth_enabled": True}

@app.post("/api/2d/generate-from-image")
async def generate_from_image(req: ImageGenRequestSchema):
    if req.params is None or req.params.material_thickness_mm is None:
        if req.params is None:
            from app.schemas.orchestrator_schemas import GenerationParamsSchema
            req.params = GenerationParamsSchema(material_thickness_mm=18.0)
        else:
            req.params.material_thickness_mm = 18.0
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"X-Internal-Key": INTERNAL_API_KEY}
        resp = await client.post(f"{AI_SERVER_2D_URL}/generate/image", json=req.dict(), headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.json())
        
        target_data = resp.json()
        target_job_id = target_data["job_id"]
        
        gateway_job_id = str(uuid.uuid4())
        jobs_db[gateway_job_id] = {
            "target_service": "ai_server_2d",
            "target_job_id": target_job_id,
            "type": "generate_image"
        }
        
        return {"job_id": gateway_job_id, "status": "queued"}

@app.post("/api/2d/generate-from-prompt")
async def generate_from_prompt(req: TextGenRequestSchema):
    if req.params is None or req.params.material_thickness_mm is None:
        if req.params is None:
            from app.schemas.orchestrator_schemas import GenerationParamsSchema
            req.params = GenerationParamsSchema(material_thickness_mm=18.0)
        else:
            req.params.material_thickness_mm = 18.0
        
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"X-Internal-Key": INTERNAL_API_KEY}
        resp = await client.post(f"{AI_SERVER_2D_URL}/generate/text", json=req.dict(), headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.json())
        
        target_data = resp.json()
        target_job_id = target_data["job_id"]
        
        gateway_job_id = str(uuid.uuid4())
        jobs_db[gateway_job_id] = {
            "target_service": "ai_server_2d",
            "target_job_id": target_job_id,
            "type": "generate_text"
        }
        
        return {"job_id": gateway_job_id, "status": "queued"}

@app.post("/api/2d/edit-dxf")
async def edit_dxf(req: EditRequestSchema):
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"X-Internal-Key": INTERNAL_API_KEY}
        resp = await client.post(f"{EDIT_SERVER_URL}/edit", json=req.dict(), headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.json())
        
        target_data = resp.json()
        target_job_id = target_data["job_id"]
        
        gateway_job_id = str(uuid.uuid4())
        jobs_db[gateway_job_id] = {
            "target_service": "edit_server",
            "target_job_id": target_job_id,
            "type": "edit_dxf"
        }
        
        return {"job_id": gateway_job_id, "status": "queued"}

@app.post("/api/2d/nest")
async def nest_dxf(req: NestRequestSchema):
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"X-Internal-Key": INTERNAL_API_KEY}
        resp = await client.post(f"{NESTING_WORKER_URL}/nest", json=req.dict(), headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.json())
        
        target_data = resp.json()
        target_job_id = target_data["job_id"]
        
        gateway_job_id = str(uuid.uuid4())
        jobs_db[gateway_job_id] = {
            "target_service": "nesting_worker",
            "target_job_id": target_job_id,
            "type": "nest"
        }
        
        return {"job_id": gateway_job_id, "status": "queued"}

@app.get("/api/jobs/{job_id}", response_model=JobStatusResponseSchema)
async def get_job_status(job_id: str):
    if job_id not in jobs_db:
        # 1. Try querying target AI Server 2D directly using job_id
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"{AI_SERVER_2D_URL}/generate/{job_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    res = data.get("result")
                    return {
                        "job_id": job_id,
                        "status": data.get("status", "unknown"),
                        "stage": data.get("stage"),
                        "result_url": res.get("dxf_path") if isinstance(res, dict) else str(res or ""),
                        "error": data.get("error")
                    }
            except Exception:
                pass

        # 2. Try querying DatabaseManager
        from app.core.database import DatabaseManager
        db_mgr = DatabaseManager()
        db_job = db_mgr.get_job(job_id)
        if db_job:
            return {
                "job_id": job_id,
                "status": db_job.get("status", "unknown").lower(),
                "stage": db_job.get("stage_name"),
                "result_url": db_job.get("output_file_path"),
                "error": None
            }
        raise HTTPException(status_code=404, detail="Job not found")
    
    mapping = jobs_db[job_id]
    target_service = mapping["target_service"]
    target_job_id = mapping["target_job_id"]
    
    if target_service == "ai_server_2d":
        target_url = f"{AI_SERVER_2D_URL}/generate/{target_job_id}"
    elif target_service == "edit_server":
        target_url = f"{EDIT_SERVER_URL}/edit/{target_job_id}"
    elif target_service == "nesting_worker":
        target_url = f"{NESTING_WORKER_URL}/nest/{target_job_id}"
    else:
        raise HTTPException(status_code=500, detail="Unknown target service")
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                data = resp.json()
                status_val = data.get("status", "unknown")
                result = data.get("result")
                result_url = None
                if result:
                    result_url = result.get("dxf_path") or str(result)
                    
                return {
                    "job_id": job_id,
                    "status": status_val,
                    "stage": data.get("stage"),
                    "result_url": result_url,
                    "error": data.get("error")
                }
    except Exception as exc:
        logging.warning("HTTP query to target_url %s failed or timed out: %s", target_url, exc)
    
    # Fallback to DatabaseManager on HTTP timeout/error
    from app.core.database import DatabaseManager
    db_mgr = DatabaseManager()
    db_job = db_mgr.get_job(job_id)
    if db_job:
        return {
            "job_id": job_id,
            "status": db_job.get("status", "processing").lower(),
            "stage": db_job.get("stage_name"),
            "result_url": db_job.get("output_file_path"),
            "error": None
        }

    return {
        "job_id": job_id,
        "status": "processing",
        "stage": "AI Processing",
        "result_url": None,
        "error": None
    }
