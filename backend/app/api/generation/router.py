from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import shutil
import uuid
import asyncio
import json
import httpx
import threading
from backend.app.schemas.schemas import (
    TextTo3DRequest, ImageTo3DRequest, TextTo2DRequest, ImageTo2DRequest, Edit3DRequest, JobProgressEvent
)
from backend.app.schemas.user import UserRead
from backend.app.api.auth.router import get_current_user
from backend.app.core.security import decode_jwt_token
from backend.app.core.database import DatabaseManager
from backend.app.core.config import settings
from backend.app.core.dynamic_endpoints import get_model_endpoint
from backend.app.db.session import get_db
from backend.app.services.subscription_service import SubscriptionService
from backend.app.services.ai_2d_adapter import (
    generate_text_to_2d as ai2d_from_text,
    generate_image_to_2d as ai2d_from_image,
    is_2d_service_configured,
)
from core.pipeline_manager import PipelineManager
from backend.app.core.logging import generation_logger


router = APIRouter(prefix="/generation", tags=["Generation"])
db = DatabaseManager()
pipeline = PipelineManager(db)
active_job_queues: dict[str, set[asyncio.Queue]] = {}


def verify_token(token: str) -> str | None:
    """Verify JWT token and return user_id, or None if invalid."""
    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            return None
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        return user_id
    except Exception:
        return None


# ── Background Task Functions ──────────────────────────────────────────────────

def run_image_to_3d_background(job_id: str, image_path: str, dims: dict, user_id: str, project_id: str, existing_job_id: str = None):
    """Background task for image-to-3d processing."""
    try:
        generation_logger.info(f"[Workflow: IMAGE_TO_3D] Background processing started for job {job_id}")
        generation_logger.info(f"[Workflow: IMAGE_TO_3D] Job details: user_id={user_id}, project_id={project_id}, image_path={image_path}, dims={dims}")
        push_job_event(job_id, "processing", "generating", 10, "Uploading image to Hunyuan3D...")

        output_file_path = pipeline.image_to_3d(
            image_path=image_path,
            desired_dims=dims,
            user_id=user_id,
            project_id=project_id,
            job_id=existing_job_id  # Pass existing job_id to avoid duplicate creation
        )

        if output_file_path:
            output_filename = os.path.basename(output_file_path)
            out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
            db.update_job_status(
                job_id, "completed",
                output_file_id=out_file_id,
                processing_time_ms=1000
            )
            push_job_event(job_id, "completed", "completed", 100, "Generation finished", output_file_path, output_filename)
            generation_logger.info(f"[Workflow: IMAGE_TO_3D] COMPLETED for job {job_id}: {output_file_path}")
        else:
            db.update_job_status(job_id, "failed")
            push_job_event(job_id, "failed", "failed", 0, "Pipeline returned no output")
            generation_logger.warning(f"[Workflow: IMAGE_TO_3D] FAILED for job {job_id}: pipeline returned None")
    except Exception as e:
        import traceback
        db.update_job_status(job_id, "failed")
        error_msg = str(e)
        error_trace = traceback.format_exc()
        push_job_event(job_id, "failed", "failed", 0, f"Processing failed: {error_msg}")
        generation_logger.error(f"[Workflow: IMAGE_TO_3D] ERROR for job {job_id}: {error_msg}\n{error_trace}")


def run_edit_3d_background(job_id: str, file_path: str, prompt: str, dims: dict, user_id: str, project_id: str):
    """Background task for 3D model editing."""
    try:
        generation_logger.info(f"[Workflow: EDIT] Background processing started for job {job_id}")
        generation_logger.info(f"[Workflow: EDIT] file={file_path} | prompt={prompt}")
        push_job_event(job_id, "processing", "understanding", 10, "Analyzing edit request...")

        output_file_path = pipeline.run_3d_pipeline(
            user_id=user_id,
            project_id=project_id,
            mode="Edit3D",
            prompt=prompt,
            image_path=file_path,
            params=dims,
        )

        if output_file_path:
            output_filename = os.path.basename(output_file_path)
            out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
            db.update_job_status(
                job_id, "completed",
                output_file_id=out_file_id,
                processing_time_ms=1000
            )
            push_job_event(job_id, "completed", "completed", 100, "Edit completed", output_file_path, output_filename)
            generation_logger.info(f"[Workflow: EDIT] COMPLETED for job {job_id}: {output_file_path}")
        else:
            db.update_job_status(job_id, "failed")
            push_job_event(job_id, "failed", "failed", 0, "Pipeline returned no output")
            generation_logger.warning(f"[Workflow: EDIT] FAILED for job {job_id}: pipeline returned None")
    except Exception as e:
        db.update_job_status(job_id, "failed")
        error_msg = str(e)
        push_job_event(job_id, "failed", "failed", 0, f"Edit failed: {error_msg}")
        generation_logger.error(f"[Workflow: EDIT] ERROR for job {job_id}: {error_msg}")


# ── 3D Endpoints ──────────────────────────────────────────────────────────────

@router.post("/text-to-3d")
async def generate_text_to_3d(
    req: TextTo3DRequest,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    if req.project_id:
        proj = db.get_project_by_id(req.project_id, user_id=user_id)
        if not proj:
            generation_logger.warning(f"[text-to-3d] Project not found: {req.project_id}")
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit
    SubscriptionService.check_and_increment_usage(sql_db, user_id)

    # ── Request traceability log ──────────────────────────────────────────────
    generation_logger.info(
        f"[Workflow: TEXT_TO_3D] REQUEST | user={user_id!r} | prompt={req.prompt!r} | "
        f"dims=h{req.height}xw{req.width}xl{req.length} | attachment=NONE (text-only)"
    )

    job_id = db.create_job(
        user_id=user_id,
        project_id=req.project_id,
        job_type="text-to-3d",
        design_type="3D",
        output_format="STL",
        text_prompt=req.prompt
    )

    def task():
        return pipeline.text_to_3d(
            user_prompt=req.prompt,
            desired_dims={"height": req.height, "width": req.width, "length": req.length},
            user_id=user_id,
            project_id=req.project_id,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )

    try:
        output_file_path = task()

        if output_file_path:
            output_filename = os.path.basename(output_file_path)
            out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
            db.update_job_status(
                job_id, "completed",
                output_file_id=out_file_id,
                processing_time_ms=1000
            )
            generation_logger.info(f"[Workflow: TEXT_TO_3D] COMPLETED | output_file={output_file_path!r} | job_id={job_id!r}")
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "3D STL generation completed",
                "output_file_path": output_file_path,
                "output_filename": output_filename
            }
        else:
            db.update_job_status(job_id, "failed")
            generation_logger.warning(f"[Workflow: TEXT_TO_3D] FAILED | job_id={job_id!r} | pipeline returned None")
            raise HTTPException(status_code=500, detail="Pipeline returned no output")
    except Exception as e:
        import traceback
        db.update_job_status(job_id, "failed")
        error_trace = traceback.format_exc()
        generation_logger.error(f"[Workflow: TEXT_TO_3D] ERROR: Exception during processing | job_id={job_id!r} | error={str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Text-to-3D generation failed: {str(e)}")


@router.post("/image-to-3d")
async def generate_image_to_3d(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    content_type = request.headers.get("content-type", "").lower()
    project_id = None
    height = 50.0
    width = 100.0
    length = 100.0
    image_path = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            req = ImageTo3DRequest(**body)
            project_id = req.project_id
            height = req.height
            width = req.width
            length = req.length
            image_path = req.image_path
        except Exception as json_err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON request: {str(json_err)}")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        project_id = form.get("project_id")
        try:
            height = float(form.get("height", 50.0))
            width = float(form.get("width", 100.0))
            length = float(form.get("length", 100.0))
        except (ValueError, TypeError):
            height, width, length = 50.0, 100.0, 100.0
        
        file_obj = form.get("file") or form.get("image")
        if file_obj and hasattr(file_obj, "filename") and file_obj.filename:
            user_upload_dir = os.path.join(os.path.abspath(settings.UPLOAD_DIR), "users", user_id)
            os.makedirs(user_upload_dir, exist_ok=True)
            saved_name = f"{uuid.uuid4()}_{file_obj.filename}"
            image_path = os.path.join(user_upload_dir, saved_name)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(file_obj.file, buffer)
        else:
            image_path = form.get("image_path")
    else:
        # Fallback to json attempt
        try:
            body = await request.json()
            req = ImageTo3DRequest(**body)
            project_id = req.project_id
            height = req.height
            width = req.width
            length = req.length
            image_path = req.image_path
        except Exception as parse_err:
            raise HTTPException(status_code=400, detail=f"Unsupported content type or invalid payload: {str(parse_err)}")

    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail=f"Input image file not found on server: {image_path!r}")

    if project_id:
        proj = db.get_project_by_id(project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit
    try:
        generation_logger.info(f"[Workflow: IMAGE_TO_3D] Checking subscription limit for user {user_id}")
        SubscriptionService.check_and_increment_usage(sql_db, user_id)
        generation_logger.info(f"[Workflow: IMAGE_TO_3D] Subscription check passed for user {user_id}")
    except Exception as sub_err:
        generation_logger.error(f"[Workflow: IMAGE_TO_3D] Subscription check FAILED for user {user_id}: {sub_err}")
        raise

    # ── Request traceability log ──────────────────────────────────────────────
    img_size = os.path.getsize(image_path) if os.path.exists(image_path) else -1
    generation_logger.info(
        f"[Workflow: IMAGE_TO_3D] REQUEST | user={user_id!r} | "
        f"image_path={image_path!r} | image_size={img_size}B | "
        f"dims=h{height}xw{width}xl{length}"
    )

    job_id = db.create_job(
        user_id=user_id,
        project_id=project_id,
        job_type="image-to-3d",
        design_type="3D",
        output_format="STL"
    )

    # Use synchronous processing for consistent behavior
    # The external API is synchronous, so we should be too
    try:
        dims = {"height": height, "width": width, "length": length}
        generation_logger.info(f"[Workflow: IMAGE_TO_3D] Starting synchronous processing for job {job_id}")
        
        output_file_path = pipeline.image_to_3d(
            image_path=image_path,
            desired_dims=dims,
            user_id=user_id,
            project_id=project_id,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )

        if output_file_path:
            output_filename = os.path.basename(output_file_path)
            out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
            db.update_job_status(
                job_id, "completed",
                output_file_id=out_file_id,
                processing_time_ms=1000
            )
            generation_logger.info(f"[Workflow: IMAGE_TO_3D] COMPLETED | output_file={output_file_path!r} | job_id={job_id!r}")
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "3D STL generation completed",
                "output_file_path": output_file_path,
                "output_filename": output_filename
            }
        else:
            db.update_job_status(job_id, "failed")
            generation_logger.warning(f"[Workflow: IMAGE_TO_3D] FAILED | job_id={job_id!r} | pipeline returned None")
            raise HTTPException(status_code=500, detail="Pipeline returned no output")
    except Exception as e:
        import traceback
        db.update_job_status(job_id, "failed")
        error_trace = traceback.format_exc()
        generation_logger.error(f"[Workflow: IMAGE_TO_3D] ERROR: Exception during processing | job_id={job_id!r} | error={str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Image-to-3D generation failed: {str(e)}")


@router.post("/edit-3d")
async def edit_3d_model(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    """Edit an existing 3D model with a text prompt."""
    user_id = str(current_user.id)
    content_type = request.headers.get("content-type", "").lower()
    project_id = None
    file_path = None
    prompt = ""
    height = None
    width = None
    length = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            req = Edit3DRequest(**body)
            project_id = req.project_id
            file_path = req.file_path
            prompt = req.prompt
            height = req.height
            width = req.width
            length = req.length
        except Exception as json_err:
            raise HTTPException(status_code=400, detail=f"Invalid JSON request: {str(json_err)}")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        project_id = form.get("project_id")
        file_path = form.get("file_path")
        prompt = form.get("prompt", "")
        try:
            height = float(form.get("height")) if form.get("height") else None
            width = float(form.get("width")) if form.get("width") else None
            length = float(form.get("length")) if form.get("length") else None
        except (ValueError, TypeError):
            height, width, length = None, None, None
    else:
        raise HTTPException(status_code=400, detail="Unsupported content type")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Input 3D file not found on server: {file_path!r}")

    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="Edit prompt is required")

    if project_id:
        proj = db.get_project_by_id(project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit
    SubscriptionService.check_and_increment_usage(sql_db, user_id)

    # ── Request traceability log ──────────────────────────────────────────────
    generation_logger.info(
        f"[Workflow: EDIT] REQUEST | user={user_id!r} | "
        f"file_path={file_path!r} | prompt={prompt!r} | "
        f"dims=h{height}xw{width}xl{length}"
    )

    job_id = db.create_job(
        user_id=user_id,
        project_id=project_id,
        job_type="edit-3d",
        design_type="3D",
        output_format="STL",
        text_prompt=prompt
    )

    # Use synchronous processing for consistent behavior
    try:
        dims = {"height": height, "width": width, "length": length}
        generation_logger.info(f"[Workflow: EDIT] Starting synchronous processing for job {job_id}")
        
        output_file_path = pipeline.edit_3d(
            file_path=file_path,
            prompt=prompt,
            desired_dims=dims,
            user_id=user_id,
            project_id=project_id,
            job_id=job_id  # Pass job_id to avoid duplicate creation
        )

        if output_file_path:
            output_filename = os.path.basename(output_file_path)
            out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
            db.update_job_status(
                job_id, "completed",
                output_file_id=out_file_id,
                processing_time_ms=1000
            )
            generation_logger.info(f"[Workflow: EDIT] COMPLETED | output_file={output_file_path!r} | job_id={job_id!r}")
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "3D model edit completed",
                "output_file_path": output_file_path,
                "output_filename": output_filename
            }
        else:
            db.update_job_status(job_id, "failed")
            generation_logger.warning(f"[Workflow: EDIT] FAILED | job_id={job_id!r} | pipeline returned None")
            raise HTTPException(status_code=500, detail="Pipeline returned no output")
    except Exception as e:
        import traceback
        db.update_job_status(job_id, "failed")
        error_trace = traceback.format_exc()
        generation_logger.error(f"[Workflow: EDIT] ERROR: Exception during processing | job_id={job_id!r} | error={str(e)}\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"3D model edit failed: {str(e)}")

# ── 2D Endpoints (New Architecture) ──────────────────────────────────────────────────────────────

@router.post("/text-to-2d")
async def generate_text_to_2d(
    req: TextTo2DRequest,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    """Generate 2D DXF from text prompt using AI_SERVER_2D."""
    user_id = str(current_user.id)
    if req.project_id:
        proj = db.get_project_by_id(req.project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit first
    SubscriptionService.check_and_increment_usage(sql_db, user_id)

    # Ensure params dict exists
    if req.params is None:
        req.params = {}
    
    # Provide default fallbacks for 2D parameters if missing
    req.params.setdefault("part_width_mm", req.params.get("width", 700.0))
    req.params.setdefault("part_height_mm", req.params.get("height", 700.0))
    req.params.setdefault("tool_diameter_mm", req.params.get("tool_diameter", 5.0))
    
    # Validate that required dimensions are provided
    required_params = ["part_width_mm", "part_height_mm", "tool_diameter_mm"]
    missing_params = [p for p in required_params if p not in req.params]
    if missing_params:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required parameters: {', '.join(missing_params)}. All dimensions are mandatory for 2D generation."
        )
    
    # Validate that dimensions are positive numbers
    for param in required_params:
        if not isinstance(req.params[param], (int, float)) or req.params[param] <= 0:
            raise HTTPException(status_code=400, detail=f"{param} must be a positive number")

    try:
        return await ai2d_from_text(user_id=user_id, prompt=req.prompt, params=req.params)
    except HTTPException:
        raise
    except Exception as e:
        generation_logger.error(f"Text-to-2D error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image-to-2d")
async def generate_image_to_2d(
    req: ImageTo2DRequest,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    """Generate 2D DXF from image using AI_SERVER_2D."""
    user_id = str(current_user.id)
    if req.project_id:
        proj = db.get_project_by_id(req.project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit first
    SubscriptionService.check_and_increment_usage(sql_db, user_id)

    if not os.path.exists(req.image_path):
        raise HTTPException(status_code=404, detail="Input image file not found on server")

    # Ensure params dict exists
    if req.params is None:
        req.params = {}
    
    # Provide default fallbacks for 2D parameters if missing
    req.params.setdefault("part_width_mm", req.params.get("width", 700.0))
    req.params.setdefault("part_height_mm", req.params.get("height", 700.0))
    req.params.setdefault("tool_diameter_mm", req.params.get("tool_diameter", 5.0))
    
    # Validate that required dimensions are provided
    required_params = ["part_width_mm", "part_height_mm", "tool_diameter_mm"]
    missing_params = [p for p in required_params if p not in req.params]
    if missing_params:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required parameters: {', '.join(missing_params)}. All dimensions are mandatory for 2D generation."
        )
    
    # Validate that dimensions are positive numbers
    for param in required_params:
        if not isinstance(req.params[param], (int, float)) or req.params[param] <= 0:
            raise HTTPException(status_code=400, detail=f"{param} must be a positive number")

    try:
        return await ai2d_from_image(
            user_id=user_id,
            image_path=req.image_path,
            prompt=req.prompt,
            params=req.params,
        )
    except HTTPException:
        raise
    except Exception as e:
        generation_logger.error(f"Image-to-2D error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
def get_generation_job(job_id: str, current_user: UserRead = Depends(get_current_user)):
    job = db.get_job(job_id)
    if not job or job.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


def push_job_event(
    job_id: str,
    status: str,
    stage_name: str,
    progress: int,
    message: str,
    output_file_path: str = None,
    output_filename: str = None,
    dxf_content: str = None,
    dxf_url: str = None
):
    evt = {
        "job_id": job_id,
        "status": status,
        "stage_name": stage_name,
        "progress": progress,
        "message": message,
        "output_file_path": output_file_path,
        "output_filename": output_filename,
        "dxf_content": dxf_content,
        "dxf_url": dxf_url
    }
    if job_id in active_job_queues:
        for q in list(active_job_queues[job_id]):
            try:
                q.put_nowait(evt)
            except Exception as e:
                generation_logger.warning(f"Error pushing SSE event: {e}")


@router.get("/stream/{job_id}")
async def stream_job_progress(job_id: str, token: str = None):
    """Real-Time SSE progress stream for job progress tracking.
    
    Authentication via query parameter token (required for EventSource compatibility).
    """
    # Verify token and get user
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    try:
        # Decode and verify token
        user_id = verify_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")
    
    job = db.get_job(job_id)
    if job and job.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Generation job not found")

    async def event_generator():
        queue = asyncio.Queue()
        if job_id not in active_job_queues:
            active_job_queues[job_id] = set()
        active_job_queues[job_id].add(queue)

        try:
            job = db.get_job(job_id)
            if job:
                st = job.get("status", "processing")
                initial_event = {
                    "job_id": job_id,
                    "status": st,
                    "stage_name": job.get("stage_name", "generating"),
                    "progress": 100 if st in ["completed", "COMPLETED"] else job.get("progress", 50),
                    "message": job.get("text_prompt") or "Processing job",
                    "output_file_path": job.get("output_file_path"),
                    "output_filename": job.get("output_filename"),
                    "dxf_content": job.get("dxf_content"),
                    "dxf_url": job.get("dxf_url")
                }
                yield f"data: {json.dumps(initial_event)}\n\n"
                if st in ["completed", "COMPLETED", "failed", "FAILED"]:
                    return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    if event is None:
                        yield ": heartbeat\n\n"
                        break
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ["completed", "COMPLETED", "failed", "FAILED"]:
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            if job_id in active_job_queues:
                active_job_queues[job_id].discard(queue)
                if not active_job_queues[job_id]:
                    active_job_queues.pop(job_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")



@router.post("/intent")
async def classify_intent_endpoint(
    payload: dict,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    user_text = payload.get("user_text", "")
    has_attachment = payload.get("has_attachment", False)
    attachment_path = payload.get("attachment_path", None)
    active_file_path = payload.get("active_file_path", None)
    has_active_cad = payload.get("has_active_cad", False)
    current_mode = payload.get("current_mode", "2D")
    project_id = payload.get("project_id", None)
    params = payload.get("params", None)

    if project_id and project_id != "default_project":
        proj = db.get_project_by_id(project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")
    
    from core.gemini_service import classify_user_intent
    result = classify_user_intent(
        user_text=user_text,
        has_attachment=has_attachment,
        has_active_cad=has_active_cad,
        current_mode=current_mode
    )

    intent = result.get("intent")
    prompt_payload = result.get("prompt_payload") or user_text

    # Execute generation pipeline if intent is generation/editing
    if intent in ["generate_2d", "generate_3d", "image_to_cad", "edit_3d", "edit_dxf"]:
        # 1. Enforce subscription limit
        SubscriptionService.check_and_increment_usage(sql_db, user_id)

        is_3d_intent = intent in ["generate_3d", "edit_3d"] or current_mode == "3D"

        job_type = "image-to-3d" if (is_3d_intent and has_attachment) else ("text-to-3d" if is_3d_intent else ("image-to-2d" if has_attachment else "text-to-2d"))
        design_type = "3D" if is_3d_intent else "2D"
        out_fmt = "STL" if is_3d_intent else "DXF"

        job_id = db.create_job(
            user_id=user_id,
            project_id=project_id,
            job_type=job_type,
            design_type=design_type,
            output_format=out_fmt,
            text_prompt=prompt_payload
        )

        push_job_event(job_id, "processing", "generating", 30, f"Generating {design_type} model...")

        try:
            if not is_3d_intent:
                if not is_2d_service_configured():
                    db.update_job_status(job_id, "failed")
                    push_job_event(job_id, "failed", "failed", 0, "2D service not configured")
                    result["job_id"] = job_id
                    result["status"] = "failed"
                    result["reply_text"] = "⚠️ خدمة توليد 2D DXF غير مهيأة حالياً في الإعدادات."
                    result["message"] = "2D service not configured"
                    return result

                if has_attachment and attachment_path:
                    external_response = await ai2d_from_image(
                        user_id=user_id,
                        image_path=attachment_path,
                        prompt=prompt_payload,
                        params=params or {},
                    )
                else:
                    external_response = await ai2d_from_text(
                        user_id=user_id,
                        prompt=prompt_payload,
                        params=params or {},
                    )

                dxf_content = external_response.get("dxf_content")
                dxf_url = external_response.get("dxf_url")
                output_file_path = external_response.get("output_file_path")
                if output_file_path and not dxf_url:
                    dxf_url = f"/static/outputs/{os.path.relpath(output_file_path, os.path.abspath(settings.OUTPUT_DIR)).replace(os.sep, '/')}"
                
                if dxf_content or dxf_url or output_file_path:
                    db.update_job_status(job_id, "completed", processing_time_ms=1000)
                    push_job_event(
                        job_id, "completed", "completed", 100, "Generation finished",
                        output_file_path=output_file_path,
                        output_filename=external_response.get("output_filename") or (os.path.basename(output_file_path) if output_file_path else None),
                        dxf_content=dxf_content,
                        dxf_url=dxf_url
                    )
                    
                    result["job_id"] = job_id
                    result["status"] = "completed"
                    if dxf_content:
                        result["dxf_content"] = dxf_content
                    if dxf_url:
                        result["dxf_url"] = dxf_url
                    if output_file_path:
                        result["output_file_path"] = output_file_path
                        result["output_filename"] = external_response.get("output_filename") or os.path.basename(output_file_path)
                else:
                    db.update_job_status(job_id, "failed")
                    push_job_event(job_id, "failed", "failed", 0, "External API returned no DXF")
                    result["status"] = "failed"
                    result["reply_text"] = "❌ لم يُرجع سيرفر التوليد الـ DXF المطلوب."

            else:
                # 3D Generation Pipeline
                dims = params if isinstance(params, dict) else {"height": 50, "width": 100, "length": 100}
                is_img_attachment = has_attachment and attachment_path and any(
                    attachment_path.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]
                )
                is_cad_attachment = has_attachment and attachment_path and attachment_path.lower().endswith(".stl")

                # ── Traceability log — what is actually being used for this request ──────
                generation_logger.info(
                    f"[intent/3D] INFO: REQUEST | user={user_id!r} | intent={intent!r} | "
                    f"has_attachment={has_attachment} | is_img_attachment={bool(is_img_attachment)} | "
                    f"is_cad_attachment={bool(is_cad_attachment)} | "
                    f"attachment_path={attachment_path!r} | "
                    f"has_active_cad={has_active_cad} | active_file_path={active_file_path!r}"
                )

                # ── Workflow Decision Logic for Intent Endpoint ─────────────────────
                # Priority: EDIT (existing model + prompt) > IMAGE_TO_3D > TEXT_TO_3D
                if has_active_cad and active_file_path and prompt_payload and prompt_payload.strip():
                    # EDIT workflow: existing model + edit prompt
                    target_path = active_file_path
                    generation_logger.info(f"[intent/3D] INFO: Workflow: EDIT (existing model + prompt) | using target_path={target_path!r}")
                    output_file_path = pipeline.run_3d_pipeline(
                        user_id=user_id,
                        project_id=project_id,
                        mode="Edit3D",
                        prompt=prompt_payload,
                        image_path=target_path,
                        params=dims,
                    )
                elif is_img_attachment:
                    if prompt_payload and prompt_payload.strip() and prompt_payload.strip().lower() != "image to 3d":
                        generation_logger.info(f"[intent/3D] INFO: Workflow: EDIT (image+text) | using attachment_path={attachment_path!r}")
                        output_file_path = pipeline.run_3d_pipeline(
                            user_id=user_id,
                            project_id=project_id,
                            mode="Edit3D",
                            prompt=prompt_payload,
                            image_path=attachment_path,
                            params=dims,
                        )
                    else:
                        generation_logger.info(f"[intent/3D] INFO: Workflow: IMAGE_TO_3D (image-only) | using attachment_path={attachment_path!r}")
                        output_file_path = pipeline.image_to_3d(
                            image_path=attachment_path,
                            desired_dims=dims,
                            user_id=user_id,
                            project_id=project_id
                        )
                elif intent == "edit_3d" or (has_active_cad and is_cad_attachment):
                    target_path = attachment_path or active_file_path
                    generation_logger.info(f"[intent/3D] INFO: Workflow: EDIT (STL/active) | using target_path={target_path!r}")
                    output_file_path = pipeline.run_3d_pipeline(
                        user_id=user_id,
                        project_id=project_id,
                        mode="Edit3D",
                        prompt=prompt_payload,
                        image_path=target_path,
                        params=dims,
                    )
                else:
                    generation_logger.info(f"[intent/3D] INFO: Workflow: TEXT_TO_3D (text-only) | prompt={prompt_payload!r}")
                    output_file_path = pipeline.text_to_3d(
                        user_prompt=prompt_payload,
                        desired_dims=dims,
                        user_id=user_id,
                        project_id=project_id
                    )

                if output_file_path and os.path.exists(output_file_path):
                    output_filename = os.path.basename(output_file_path)
                    out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
                    db.update_job_status(job_id, "completed", output_file_id=out_file_id, processing_time_ms=1000)

                    push_job_event(job_id, "completed", "completed", 100, "Generation finished", output_file_path, output_filename)

                    result["job_id"] = job_id
                    result["status"] = "completed"
                    result["output_file_path"] = output_file_path
                    result["output_filename"] = output_filename
                else:
                    db.update_job_status(job_id, "failed")
                    push_job_event(job_id, "failed", "failed", 0, "Pipeline failed")
                    result["status"] = "failed"
                    result["reply_text"] = "❌ فشل توليد مجسم 3D من السيرفر. يرجى التحقق من اتصال Hunyuan3D والمحاولة مرة أخرى."

        except Exception as err:
            generation_logger.error(f"[intent/3D] ERROR: Pipeline execution error: {err}")
            db.update_job_status(job_id, "failed")
            push_job_event(job_id, "failed", "failed", 0, str(err))
            result["status"] = "failed"
            result["reply_text"] = f"❌ خطأ أثناء التوليد: {str(err)}"

    return result
