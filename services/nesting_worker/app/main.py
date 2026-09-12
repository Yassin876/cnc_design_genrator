import uuid
import os
import tempfile
import requests
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.nesting_logic import nest_parts, StockSheet

app = FastAPI(title="CAD Studio — Nesting Worker Service")

# In-memory storage for jobs
jobs_db: Dict[str, Dict[str, Any]] = {}

class StockSheetSchema(BaseModel):
    name: Optional[str] = "Sheet"
    material: Optional[str] = "Default"
    width: float
    height: float
    thickness: float = 1.0
    available_quantity: int = 1
    unlimited_quantity: bool = False

class NestRequest(BaseModel):
    part_files_urls: List[str]
    stock_sheets: List[StockSheetSchema]
    spacing: float = 5.0
    allow_rotate: bool = True
    nesting_mode: str = "Finish priority parts first"
    continue_on_incomplete: bool = True

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "nesting_worker"}

def run_nesting_job(job_id: str, req: NestRequest):
    jobs_db[job_id]["status"] = "processing"
    temp_dir = tempfile.mkdtemp(prefix=f"nest_{job_id}_")
    
    try:
        local_parts = []
        for idx, url in enumerate(req.part_files_urls):
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            
            filename = os.path.basename(url.split("?")[0]) or f"part_{idx}.dxf"
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, "wb") as f:
                f.write(resp.content)
            local_parts.append(file_path)
        
        stock_sheets = [s.dict() for s in req.stock_sheets]
        
        output_dir = os.path.join(temp_dir, "output")
        result = nest_parts(
            parts=local_parts,
            stock_sheets=stock_sheets,
            spacing=req.spacing,
            allow_rotate=req.allow_rotate,
            nesting_mode=req.nesting_mode,
            continue_on_incomplete=req.continue_on_incomplete,
            output_dir=output_dir
        )
        
        jobs_db[job_id]["status"] = "completed"
        jobs_db[job_id]["result"] = result
    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)

@app.post("/nest")
def create_nest_job(req: NestRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "result": None,
        "error": None
    }
    background_tasks.add_task(run_nesting_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/nest/{job_id}")
def get_nest_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]
