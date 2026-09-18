from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import os
import asyncio
import shutil
import uuid
import httpx
from backend.app.schemas.schemas import AIEditRequest, ParametricEditRequest, GenerationJobResponse
from backend.app.schemas.user import UserRead
from backend.app.core.database import DatabaseManager
from backend.app.db.session import get_db
from backend.app.api.auth.router import get_current_user
from backend.app.services.subscription_service import SubscriptionService
from backend.app.core.config import settings
from core.pipeline_manager import PipelineManager

router = APIRouter(prefix="/editing", tags=["Editing"])
db = DatabaseManager()
pipeline_mgr = PipelineManager(db)

@router.post("/ai", response_model=GenerationJobResponse)
async def ai_edit_model(
    req: AIEditRequest,
    current_user: UserRead = Depends(get_current_user),
    sql_db: Session = Depends(get_db)
):
    user_id = str(current_user.id)
    if req.project_id:
        proj = db.get_project_by_id(req.project_id, user_id=user_id)
        if not proj:
            raise HTTPException(status_code=404, detail="Project not found")

    # 1. Enforce subscription limit
    SubscriptionService.check_and_increment_usage(sql_db, user_id)

    try:

        if req.design_type == "2D":
            edit_service_url = os.getenv("TWO_D_SERVICE_URL", settings.EDIT_SERVER_URL).strip().rstrip("/")
            if not edit_service_url:
                raise HTTPException(status_code=503, detail="2D edit service not configured (set EDIT_SERVER_URL or TWO_D_SERVICE_URL)")
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    health_res = await client.get(f"{edit_service_url}/health")
                    health_res.raise_for_status()
            except Exception as edit_err:

                raise HTTPException(
                    status_code=503,
                    detail=f"2D edit server unavailable at {edit_service_url}: {edit_err}",
                )
            output_file = os.path.abspath(os.path.join(
                settings.OUTPUT_DIR, "users", user_id, f"edited_2d_{uuid.uuid4().hex}.dxf"
            ))
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{edit_service_url}/edit/local",
                    json={"input_path": req.file_path, "instruction": req.prompt},
                )
                response.raise_for_status()
                job_id = response.json()["job_id"]
                for _ in range(120):
                    await asyncio.sleep(1)
                    status_response = await client.get(f"{edit_service_url}/edit/{job_id}")
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    if status_data.get("status") == "completed":
                        result_path = status_data.get("result", {}).get("dxf_path")
                        if not result_path or not os.path.isfile(result_path):
                            raise HTTPException(status_code=502, detail="2D edit server returned no DXF output")
                        shutil.copy2(result_path, output_file)
                        return GenerationJobResponse(
                            job_id=job_id, status="COMPLETED", stage_name="completed", progress=100,
                            output_file_path=output_file, output_filename=os.path.basename(output_file),
                            message="2D DXF modifications applied successfully"
                        )
                    if status_data.get("status") == "failed":
                        raise HTTPException(status_code=502, detail=status_data.get("error") or "2D edit failed")
            raise HTTPException(status_code=504, detail="2D edit timed out")
        else:
            output_file = pipeline_mgr.run_3d_pipeline(
                user_id=user_id,
                project_id=req.project_id,
                mode="Edit3D",
                prompt=req.prompt,
                image_path=req.file_path
            )


        if not output_file:
            raise HTTPException(
                status_code=500,
                detail="AI edit execution failed. Check that the file_path exists and GEMINI_API_KEY is set in .env"
            )

        return GenerationJobResponse(
            job_id="job_edit",
            status="COMPLETED",
            stage_name="completed",
            progress=100,
            output_file_path=output_file,
            output_filename=os.path.basename(output_file),
            message="AI modifications applied successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parameters")
def parametric_edit(
    req: ParametricEditRequest,
    current_user: UserRead = Depends(get_current_user)
):
    # Parametric edit scaling / transforms
    return {
        "status": "COMPLETED",
        "file_path": req.file_path,
        "transform": {
            "scale": [req.scale_x, req.scale_y, req.scale_z],
            "rotation": [req.rotation_x, req.rotation_y, req.rotation_z]
        },
        "message": "Parametric modifications saved"
    }
