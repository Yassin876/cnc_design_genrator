from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from app.schemas.schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate, ProjectVersionResponse, ModelResponse
)
from app.core.database import DatabaseManager
from app.core.security import decode_jwt_token

router = APIRouter(prefix="/projects", tags=["Projects"])
db = DatabaseManager()
security_scheme = HTTPBearer(auto_error=False)

def resolve_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme), query_user_id: Optional[str] = None) -> str:
    if credentials and credentials.credentials:
        try:
            payload = decode_jwt_token(credentials.credentials)
            user_id = payload.get("sub")
            if user_id:
                return user_id
        except Exception:
            pass
    if query_user_id:
        return query_user_id
    return "default_user"

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, user_id: str = Depends(resolve_user_id)):
    project_id = db.create_project(
        user_id=user_id,
        name=project_in.name,
        description=project_in.description or "",
        project_type=project_in.type or "3D"
    )
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=500, detail="Failed to retrieve created project")
    return project

@router.get("", response_model=List[ProjectResponse])
def get_projects(
    status: Optional[str] = "ACTIVE",
    project_type: Optional[str] = None,
    favorites_only: bool = False,
    recent_only: bool = False,
    limit: Optional[int] = None,
    user_id: str = Depends(resolve_user_id)
):
    projects = db.get_user_projects(
        user_id=user_id,
        status=status,
        limit=limit,
        favorites_only=favorites_only,
        recent_only=recent_only
    )
    if project_type:
        projects = [p for p in projects if p["type"] == project_type]
    return projects

@router.get("/recent", response_model=List[ProjectResponse])
def get_recent_projects(limit: int = 10, user_id: str = Depends(resolve_user_id)):
    return db.get_user_projects(user_id=user_id, status="ACTIVE", limit=limit)

@router.get("/favorites", response_model=List[ProjectResponse])
def get_favorite_projects(user_id: str = Depends(resolve_user_id)):
    return db.get_user_projects(user_id=user_id, favorites_only=True)

@router.get("/trash", response_model=List[ProjectResponse])
def get_trash_projects(user_id: str = Depends(resolve_user_id)):
    return db.get_user_projects(user_id=user_id, status="TRASH")

@router.delete("/trash/clear")
def clear_trash(user_id: str = Depends(resolve_user_id)):
    db.clear_user_trash(user_id)
    return {"message": "Trash cleared successfully"}

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, update_in: ProjectUpdate):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.update_project(
        project_id,
        name=update_in.name,
        description=update_in.description,
        project_type=update_in.type,
        status=update_in.status,
        is_favorite=update_in.is_favorite
    )
    updated = db.get_project_by_id(project_id)
    return updated

@router.post("/{project_id}/favorite")
def toggle_favorite(project_id: str):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    is_fav = db.toggle_favorite_project(project_id)
    return {"id": project_id, "is_favorite": is_fav}

@router.delete("/{project_id}")
def move_to_trash(project_id: str):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.move_project_to_trash(project_id)
    return {"message": "Project moved to trash", "id": project_id}

@router.post("/{project_id}/restore")
def restore_project(project_id: str):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.restore_project_from_trash(project_id)
    return {"message": "Project restored", "id": project_id}

@router.delete("/{project_id}/permanent")
def delete_permanently(project_id: str):
    project = db.get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.permanently_delete_project(project_id)
    return {"message": "Project permanently deleted", "id": project_id}

@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
def get_project_versions(project_id: str):
    return db.get_project_versions(project_id)

@router.post("/{project_id}/versions/{version_id}/restore")
def restore_project_version(project_id: str, version_id: str):
    versions = db.get_project_versions(project_id)
    target = next((v for v in versions if v["id"] == version_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target version not found")
    
    new_v_id = db.create_project_version(
        project_id=project_id,
        prompt=f"Restored to Version v{target['version_number']} ({target['prompt']})",
        source_files=target.get("source_files", []),
        generated_files=target.get("generated_files", []),
        model_metadata=target.get("model_metadata", {}),
        parameters=target.get("parameters", {})
    )
    return {
        "status": "RESTORED",
        "restored_version_number": target["version_number"],
        "new_version_id": new_v_id,
        "message": f"Project state restored to Version v{target['version_number']}"
    }

@router.post("/{project_id}/versions/{version_id}/duplicate")
def duplicate_project_version(project_id: str, version_id: str, user_id: str = Depends(resolve_user_id)):
    versions = db.get_project_versions(project_id)
    target = next((v for v in versions if v["id"] == version_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target version not found")

    new_project_id = db.create_project(
        user_id=user_id,
        name=f"Copy of Project (v{target['version_number']})",
        description=f"Branch created from version v{target['version_number']}: {target['prompt']}"
    )
    return {
        "status": "DUPLICATED",
        "new_project_id": new_project_id,
        "source_version_number": target["version_number"],
        "message": f"New project branch created from Version v{target['version_number']}"
    }

@router.get("/{project_id}/models", response_model=List[ModelResponse])
def get_project_models(project_id: str):
    return db.get_models_by_project(project_id)

@router.get("/jobs")
def get_user_jobs(user_id: str = Depends(resolve_user_id), limit: int = 100):
    return db.get_user_jobs(user_id, limit)

@router.delete("/jobs/clear")
def clear_user_history(user_id: str = Depends(resolve_user_id)):
    db.clear_user_history(user_id)
    return {"message": f"Cleared generation history for user {user_id}"}

