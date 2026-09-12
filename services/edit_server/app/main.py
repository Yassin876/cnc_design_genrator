import uuid
import os
import tempfile
import requests
from typing import Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.dxf_editor import dxf_to_json, apply_edits
from app.ai_edits import AIEditsGenerator

app = FastAPI(title="CAD Studio — Edit Server Service")
ai_edits_gen = AIEditsGenerator()

# In-memory job storage
jobs_db: Dict[str, Dict[str, Any]] = {}

class EditRequest(BaseModel):
    dxf_url: str
    instruction: str

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "edit_server"}

def run_edit_job(job_id: str, req: EditRequest):
    jobs_db[job_id]["status"] = "processing"
    temp_dir = tempfile.mkdtemp(prefix=f"edit_{job_id}_")
    
    try:
        # Download DXF file from URL
        resp = requests.get(req.dxf_url, timeout=30)
        resp.raise_for_status()
        
        input_path = os.path.join(temp_dir, "input.dxf")
        with open(input_path, "wb") as f:
            f.write(resp.content)
        
        # Convert DXF to JSON schema
        dxf_json = dxf_to_json(input_path)
        
        # Get structured edits from Gemini
        structured_edits = ai_edits_gen.generate_structured_edits(dxf_json, req.instruction)
        
        # Apply edits
        output_path = os.path.join(temp_dir, "edited.dxf")
        apply_edits(input_path, structured_edits, output_path)
        
        jobs_db[job_id]["status"] = "completed"
        jobs_db[job_id]["result"] = {
            "dxf_path": output_path,
            "edits": structured_edits
        }
    except Exception as e:
        jobs_db[job_id]["status"] = "failed"
        jobs_db[job_id]["error"] = str(e)

@app.post("/edit")
def create_edit_job(req: EditRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "result": None,
        "error": None
    }
    background_tasks.add_task(run_edit_job, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/edit/{job_id}")
def get_edit_job_status(job_id: str):
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs_db[job_id]
