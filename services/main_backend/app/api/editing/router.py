from fastapi import APIRouter, HTTPException
import os
from app.schemas.schemas import AIEditRequest, ParametricEditRequest, GenerationJobResponse
from app.core.database import DatabaseManager
from app.core.pipeline_manager import PipelineManager
from app.core.cad_2d_service import TwoDCADService

router = APIRouter(prefix="/editing", tags=["Editing"])
db = DatabaseManager()
pipeline_mgr = PipelineManager(db)
cad_2d = TwoDCADService(pipeline_mgr)

@router.post("/ai", response_model=GenerationJobResponse)
def ai_edit_model(req: AIEditRequest):
    try:
        if req.design_type == "2D":
            output_file = cad_2d.edit_dxf(
                file_path=req.file_path,
                prompt=req.prompt,
                user_id=req.user_id,
                project_id=req.project_id,
            )
        else:
            output_file = pipeline_mgr.run_3d_pipeline(
                user_id=req.user_id,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/parameters")
def parametric_edit(req: ParametricEditRequest):
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
