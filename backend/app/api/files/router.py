from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
import shutil
from backend.app.schemas.user import UserRead
from backend.app.api.auth.router import get_current_user
from backend.app.core.database import DatabaseManager

from backend.app.core.config import settings
from core.paths import (
    STORAGE_DIR as CORE_STORAGE_DIR,
    OUTPUT_DIR as CORE_OUTPUT_DIR,
    UPLOAD_DIR as CORE_UPLOAD_DIR,
    TEMP_DIR as CORE_TEMP_DIR,
)

router = APIRouter(prefix="/files", tags=["Files"])
db = DatabaseManager()

STORAGE_DIR = os.path.abspath(str(CORE_STORAGE_DIR))
UPLOAD_DIR = os.path.abspath(str(CORE_UPLOAD_DIR))
OUTPUT_DIR = os.path.abspath(str(CORE_OUTPUT_DIR))
TEMP_DIR = os.path.abspath(str(CORE_TEMP_DIR))

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)


def is_safe_storage_path(target_path: str, base_dir: str = STORAGE_DIR) -> bool:
    """Verifies that target_path is strictly within base_dir using path commonality."""
    try:
        abs_target = os.path.abspath(target_path)
        abs_base = os.path.abspath(base_dir)
        return os.path.commonpath([abs_target, abs_base]) == abs_base
    except (ValueError, OSError):
        return False



class DownloadFileRequest(BaseModel):
    file_path: str

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserRead = Depends(get_current_user)
):
    try:
        user_id = str(current_user.id)
        user_upload_dir = os.path.join(UPLOAD_DIR, "users", user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}_{file.filename}"
        dest_path = os.path.join(user_upload_dir, filename)
        
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        file_size = os.path.getsize(dest_path)
        db.log_input_file(user_id, file.filename, dest_path, size=file_size)
        
        return {
            "status": "SUCCESS",
            "original_name": file.filename,
            "saved_path": dest_path,
            "file_size": file_size
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.get("/download")
def download_file_get(
    file_path: str = Query(...),
    current_user: UserRead = Depends(get_current_user)
):
    return resolve_and_download(file_path, str(current_user.id))

@router.post("/download")
def download_file_post(
    req: DownloadFileRequest,
    current_user: UserRead = Depends(get_current_user)
):
    return resolve_and_download(req.file_path, str(current_user.id))

def resolve_and_download(file_path: str, user_id: str):
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path parameter is required")
        
    storage_root = os.path.abspath(STORAGE_DIR)
    clean_path = file_path.lstrip("/\\")

    candidates = [
        os.path.abspath(os.path.join(storage_root, "outputs", "users", user_id, clean_path)),
        os.path.abspath(os.path.join(storage_root, "uploads", "users", user_id, clean_path)),
        os.path.abspath(os.path.join(storage_root, "outputs", clean_path)),
        os.path.abspath(os.path.join(storage_root, "uploads", clean_path)),
        os.path.abspath(os.path.join(storage_root, clean_path)),
        os.path.abspath(os.path.join(storage_root, "outputs", os.path.basename(file_path))),
        os.path.abspath(os.path.join(storage_root, "uploads", os.path.basename(file_path))),
    ]
    
    if os.path.isabs(file_path):
        candidates.insert(0, os.path.abspath(file_path))
    
    for abs_p in candidates:
        if is_safe_storage_path(abs_p) and os.path.exists(abs_p) and os.path.isfile(abs_p):
            # Verify normalized path to ensure no cross-user leak
            norm_abs = os.path.normpath(abs_p).replace("\\", "/")
            if "/users/" in norm_abs:
                user_segment = norm_abs.split("/users/")[1].split("/")[0]
                if user_segment and user_segment != user_id and user_segment != "default_user":
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: file belongs to another account")
            filename = os.path.basename(abs_p)
            return FileResponse(abs_p, filename=filename)
            
    raise HTTPException(status_code=404, detail=f"File not found in storage: {file_path}")

