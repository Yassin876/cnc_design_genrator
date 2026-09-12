from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
import shutil

router = APIRouter(prefix="/files", tags=["Files"])

UPLOAD_DIR = os.path.abspath("uploads")
OUTPUT_DIR = os.path.abspath("outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

class DownloadFileRequest(BaseModel):
    file_path: str

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        filename = f"{uuid.uuid4()}_{file.filename}"
        dest_path = os.path.join(UPLOAD_DIR, filename)
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "status": "SUCCESS",
            "original_name": file.filename,
            "saved_path": dest_path,
            "file_size": os.path.getsize(dest_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.get("/download")
def download_file_get(file_path: str = Query(...)):
    return resolve_and_download(file_path)

@router.post("/download")
def download_file_post(req: DownloadFileRequest):
    return resolve_and_download(req.file_path)

def resolve_and_download(file_path: str):
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path parameter is required")
        
    candidates = [
        os.path.abspath(file_path),
        os.path.join(OUTPUT_DIR, file_path),
        os.path.join(UPLOAD_DIR, file_path),
        os.path.join(OUTPUT_DIR, os.path.basename(file_path)),
        os.path.join(UPLOAD_DIR, os.path.basename(file_path))
    ]
    
    for path in candidates:
        if os.path.exists(path) and os.path.isfile(path):
            filename = os.path.basename(path)
            return FileResponse(path, filename=filename)
            
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
