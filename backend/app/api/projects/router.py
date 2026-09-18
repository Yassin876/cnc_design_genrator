from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from backend.app.schemas.schemas import (
    ProjectCreate, ProjectResponse, ProjectUpdate, ProjectVersionResponse, ModelResponse
)
from backend.app.schemas.user import UserRead
from backend.app.core.database import DatabaseManager
from backend.app.api.auth.router import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])
db = DatabaseManager()


def get_user_project_or_404(project_id: str, user_id: str) -> dict:
    """Verifies that the project exists and belongs to the authenticated user."""
    project = db.get_project_by_id(project_id, user_id=user_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(project_in: ProjectCreate, current_user: UserRead = Depends(get_current_user)):
    project_id = db.create_project(
        user_id=str(current_user.id),
        name=project_in.name,
        description=project_in.description or "",
        project_type=project_in.type or "3D",
        file_path=project_in.file_path
    )
    project = db.get_project_by_id(project_id, user_id=str(current_user.id))
    if not project:
        raise HTTPException(status_code=500, detail="Failed to retrieve created project")
    return project


@router.get("", response_model=List[ProjectResponse])
def get_projects(
    filter: Optional[str] = Query(None, description="Filter projects by: all, recent, favorites, trash"),
    status: Optional[str] = None,
    project_type: Optional[str] = None,
    favorites_only: bool = False,
    recent_only: bool = False,
    limit: Optional[int] = None,
    current_user: UserRead = Depends(get_current_user)
):
    filter_mode = filter
    if not filter_mode and not status:
        filter_mode = "all"

    projects = db.get_user_projects(
        user_id=str(current_user.id),
        status=status,
        limit=limit,
        favorites_only=favorites_only,
        recent_only=recent_only,
        filter_mode=filter_mode
    )
    if project_type:
        projects = [p for p in projects if p["type"] == project_type]
    return projects


@router.get("/recent", response_model=List[ProjectResponse])
def get_recent_projects(limit: int = 10, current_user: UserRead = Depends(get_current_user)):
    return db.get_user_projects(user_id=str(current_user.id), filter_mode="recent", limit=limit)


@router.get("/favorites", response_model=List[ProjectResponse])
def get_favorite_projects(current_user: UserRead = Depends(get_current_user)):
    return db.get_user_projects(user_id=str(current_user.id), filter_mode="favorites")


@router.get("/trash", response_model=List[ProjectResponse])
def get_trash_projects(current_user: UserRead = Depends(get_current_user)):
    return db.get_user_projects(user_id=str(current_user.id), filter_mode="trash")


@router.delete("/trash/clear")
def clear_trash(current_user: UserRead = Depends(get_current_user)):
    db.clear_user_trash(str(current_user.id))
    return {"message": "Trash cleared successfully"}


@router.get("/jobs")
def get_user_jobs(current_user: UserRead = Depends(get_current_user), limit: int = 100):
    return db.get_user_jobs(str(current_user.id), limit)


@router.delete("/jobs/clear")
def clear_user_history(current_user: UserRead = Depends(get_current_user)):
    db.clear_user_history(str(current_user.id))
    return {"message": f"Cleared generation history for user {current_user.id}"}


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, current_user: UserRead = Depends(get_current_user)):
    return get_user_project_or_404(project_id, str(current_user.id))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, update_in: ProjectUpdate, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    
    db.update_project(
        project_id,
        name=update_in.name,
        description=update_in.description,
        project_type=update_in.type,
        status=update_in.status,
        is_favorite=update_in.is_favorite,
        file_path=update_in.file_path,
        is_deleted=update_in.is_deleted,
        deleted_at=update_in.deleted_at
    )
    return db.get_project_by_id(project_id, user_id=str(current_user.id))


@router.patch("/{project_id}/favorite")
@router.post("/{project_id}/favorite")
def toggle_favorite(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    is_fav = db.toggle_favorite_project(project_id)
    return {"id": project_id, "is_favorite": is_fav}


@router.patch("/{project_id}/trash")
def move_to_trash_patch(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    db.move_project_to_trash(project_id)
    return {"message": "Project moved to trash", "id": project_id}


@router.patch("/{project_id}/restore")
@router.post("/{project_id}/restore")
def restore_project(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    db.restore_project_from_trash(project_id)
    return {"message": "Project restored", "id": project_id}


@router.delete("/{project_id}")
def delete_project(project_id: str, current_user: UserRead = Depends(get_current_user)):
    project = get_user_project_or_404(project_id, str(current_user.id))
    
    if project.get("is_deleted") or project.get("status") == "TRASH":
        db.permanently_delete_project(project_id)
        return {"message": "Project permanently deleted", "id": project_id, "permanent": True}
    else:
        db.move_project_to_trash(project_id)
        return {"message": "Project moved to trash", "id": project_id, "permanent": False}


@router.delete("/{project_id}/permanent")
def delete_permanently(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    try:
        db.permanently_delete_project(project_id)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    return {"message": "Project permanently deleted", "id": project_id}


@router.get("/{project_id}/versions", response_model=List[ProjectVersionResponse])
def get_project_versions(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    return db.get_project_versions(project_id)


@router.post("/{project_id}/versions/{version_id}/restore")
def restore_project_version(project_id: str, version_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
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
def duplicate_project_version(project_id: str, version_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    versions = db.get_project_versions(project_id)
    target = next((v for v in versions if v["id"] == version_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Target version not found")

    new_project_id = db.create_project(
        user_id=str(current_user.id),
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
def get_project_models(project_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    return db.get_models_by_project(project_id)


# ── Chat & Conversation History Endpoints ─────────────────────────────────────

@router.get("/{project_id}/conversations")
def get_conversations(project_id: str, design_type: str = Query("2D"), current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    return db.get_user_conversations(user_id=str(current_user.id), project_id=project_id, design_type=design_type)


@router.post("/{project_id}/conversations")
def create_conversation(project_id: str, payload: dict, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    design_type = payload.get("design_type", "2D")
    title = payload.get("title", "محادثة جديدة")
    active_file_path = payload.get("active_file_path", None)
    conv_id = db.create_conversation(
        user_id=str(current_user.id),
        project_id=project_id,
        design_type=design_type,
        title=title,
        active_file_path=active_file_path
    )
    return {"id": conv_id, "title": title, "design_type": design_type, "active_file_path": active_file_path}


@router.put("/{project_id}/conversations/{conv_id}")
def update_conversation(project_id: str, conv_id: str, payload: dict, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    title = payload.get("title", None)
    active_file_path = payload.get("active_file_path", None)
    is_pinned = payload.get("is_pinned", None)
    success = db.update_conversation(conv_id, title=title, active_file_path=active_file_path, is_pinned=is_pinned)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found or unchanged")
    return {"message": "Updated successfully", "conv_id": conv_id}


@router.delete("/{project_id}/conversations/{conv_id}")
def delete_conversation(project_id: str, conv_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    db.delete_conversation(conv_id)
    return {"message": f"Deleted conversation {conv_id}"}


@router.get("/{project_id}/conversations/{conv_id}/messages")
def get_conversation_messages(project_id: str, conv_id: str, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    return db.get_conversation_messages(conv_id)


@router.get("/{project_id}/chat")
@router.get("/{project_id}/messages")
def get_chat_history(
    project_id: str,
    design_type: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),
    current_user: UserRead = Depends(get_current_user)
):
    get_user_project_or_404(project_id, str(current_user.id))
    return db.get_chat_history(
        user_id=str(current_user.id),
        project_id=project_id,
        design_type=design_type,
        conversation_id=conversation_id
    )


@router.post("/{project_id}/chat")
@router.post("/{project_id}/messages")
def save_chat_message(project_id: str, payload: dict, current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    design_type = payload.get("design_type", "2D")
    sender = payload.get("sender", "user")
    text = payload.get("text", "")
    attachments = payload.get("attachments", None)
    conversation_id = payload.get("conversation_id", None)
    
    if not text and not attachments:
        raise HTTPException(status_code=400, detail="Text or attachments required")
        
    msg_id = db.save_chat_message(
        user_id=str(current_user.id),
        project_id=project_id,
        design_type=design_type,
        sender=sender,
        text=text,
        attachments=attachments,
        conversation_id=conversation_id
    )
    return {"status": "saved", "message_id": msg_id, "id": msg_id}


@router.delete("/{project_id}/chat")
@router.delete("/{project_id}/messages")
def clear_chat_history(project_id: str, design_type: str = Query("2D"), current_user: UserRead = Depends(get_current_user)):
    get_user_project_or_404(project_id, str(current_user.id))
    db.clear_chat_history(user_id=str(current_user.id), project_id=project_id, design_type=design_type)
    return {"status": "cleared", "project_id": project_id, "design_type": design_type}



