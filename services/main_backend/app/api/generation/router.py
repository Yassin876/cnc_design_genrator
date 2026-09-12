from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json
import os
import time
from app.schemas.schemas import (
    TextTo3DRequest, ImageTo3DRequest, TextTo2DRequest, ImageTo2DRequest, JobProgressEvent
)
from app.core.database import DatabaseManager
from app.core.pipeline_manager import PipelineManager
from app.core.cad_2d_service import TwoDCADService

router = APIRouter(prefix="/generation", tags=["Generation"])
db = DatabaseManager()
pipeline = PipelineManager(db)
cad_2d = TwoDCADService(pipeline)

# Global dict tracking active job SSE progress queues
active_job_queues: dict[str, asyncio.Queue] = {}


async def push_job_event(
    job_id: str, status: str, stage_name: str, progress: int, message: str,
    output_file_path=None, output_filename=None
):
    event = JobProgressEvent(
        job_id=job_id,
        status=status,
        stage_name=stage_name,
        progress=progress,
        message=message,
        output_file_path=output_file_path,
        output_filename=output_filename
    )
    db.update_job_status(job_id=job_id, status=status, stage_name=stage_name, progress=progress)
    if job_id in active_job_queues:
        await active_job_queues[job_id].put(event)


@router.get("/stream/{job_id}")
async def stream_job_progress(job_id: str):
    """Server-Sent Events (SSE) endpoint for real-time CAD generation progress."""
    async def event_generator():
        q = asyncio.Queue()
        active_job_queues[job_id] = q
        heartbeat_task = None

        initial_job = db.get_job(job_id)
        if initial_job:
            evt = JobProgressEvent(
                job_id=job_id,
                status=initial_job["status"],
                stage_name=initial_job["stage_name"],
                progress=initial_job["progress"],
                message=f"Stage: {initial_job['stage_name']}",
                output_file_path=initial_job.get("output_file_path"),
                output_filename=initial_job.get("output_filename")
            )
            yield f"data: {evt.model_dump_json()}\n\n"

        async def heartbeat_sender():
            while True:
                await asyncio.sleep(10)
                await q.put(None)

        try:
            heartbeat_task = asyncio.create_task(heartbeat_sender())
            while True:
                evt: JobProgressEvent | None = await q.get()
                if evt is None:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {evt.model_dump_json()}\n\n"
                if evt.status in ["completed", "failed", "cancelled"]:
                    break
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
            active_job_queues.pop(job_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def run_pipeline_with_stages(
    job_id: str,
    task_fn,
    project_id=None,
    prompt_text: str = "",
    design_type: str = "2D"
):
    """
    Orchestrates SSE progress stages around a blocking pipeline task.
    Stages are labeled specifically for 2D (DXF) or 3D (STL) workflows.
    """
    start_time = time.time()
    is_2d = design_type == "2D"

    stage_msgs = {
        "queued":             "Job queued — waiting for pipeline slot",
        "processing":         "Initializing AI inference runtime",
        "understanding":      ("Gemini AI classifying image & extracting CAD features"
                               if is_2d else
                               "AI analyzing 3D geometry specification & material constraints"),
        "generating":         ("Running Image2CAD vectorization engine — converting to DXF polylines"
                               if is_2d else
                               "Synthesizing parametric 3D mesh geometry"),
        "geometry_processing":("Compiling DXF entities: lines, circles, arcs"
                               if is_2d else
                               "Compiling STL mesh triangles & watertight hull"),
        "optimizing":         ("Optimizing layer structure & DXF bounding box"
                               if is_2d else
                               "Healing non-manifold faces & optimizing vertex normals"),
        "validating":         ("Validating DXF entity count & toolpath clearances"
                               if is_2d else
                               "Validating watertight topology & CNC feasibility"),
    }

    try:
        await push_job_event(job_id, "queued",        "queued",        5,  stage_msgs["queued"])
        await asyncio.sleep(0.2)

        await push_job_event(job_id, "processing",    "processing",   15,  stage_msgs["processing"])
        await asyncio.sleep(0.3)

        await push_job_event(job_id, "understanding", "understanding", 30,  stage_msgs["understanding"])
        await asyncio.sleep(0.4)

        await push_job_event(job_id, "generating",    "generating",   50,  stage_msgs["generating"])

        # Run the blocking pipeline in a thread executor (non-blocking for async loop)
        loop = asyncio.get_running_loop()
        output_file_path = await loop.run_in_executor(None, task_fn)

        if not output_file_path:
            raise RuntimeError("Pipeline returned no output file path. Check backend logs.")

        await push_job_event(job_id, "geometry_processing", "geometry_processing", 72, stage_msgs["geometry_processing"])
        await asyncio.sleep(0.3)

        await push_job_event(job_id, "optimizing", "optimizing", 87, stage_msgs["optimizing"])
        await asyncio.sleep(0.2)

        await push_job_event(job_id, "validating", "validating", 95, stage_msgs["validating"])
        await asyncio.sleep(0.2)

        duration_ms = int((time.time() - start_time) * 1000)
        output_filename = os.path.basename(output_file_path)

        out_file_id = db.log_output_file(job_id, output_filename, output_file_path)
        db.update_job_status(
            job_id, "completed",
            stage_name="completed",
            progress=100,
            output_file_id=out_file_id,
            processing_time_ms=duration_ms
        )

        if project_id:
            v_id = db.create_project_version(
                project_id=project_id,
                prompt=prompt_text,
                generated_files=[output_file_path],
                model_metadata={"output_filename": output_filename, "processing_time_ms": duration_ms}
            )
            db.log_model(
                project_id=project_id,
                version_id=v_id,
                format_type=output_filename.split(".")[-1].upper(),
                file_path=output_file_path
            )

        fmt = "DXF" if is_2d else "STL"
        await push_job_event(
            job_id, "completed", "completed", 100,
            f"{fmt} generation complete — {duration_ms}ms",
            output_file_path=output_file_path,
            output_filename=output_filename
        )

    except Exception as e:
        import traceback
        print(f"[pipeline] Job {job_id} failed: {e}\n{traceback.format_exc()}")
        await push_job_event(job_id, "failed", "failed", 0, f"Pipeline error: {str(e)}")


# ── 3D Endpoints ──────────────────────────────────────────────────────────────

@router.post("/text-to-3d")
async def generate_text_to_3d(req: TextTo3DRequest, background_tasks: BackgroundTasks):
    job_id = db.create_job(
        user_id=req.user_id,
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
            user_id=req.user_id,
            project_id=req.project_id
        )

    background_tasks.add_task(run_pipeline_with_stages, job_id, task, req.project_id, req.prompt, "3D")
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"3D STL job queued. Stream progress at /api/v1/generation/stream/{job_id}"
    }


@router.post("/image-to-3d")
async def generate_image_to_3d(req: ImageTo3DRequest, background_tasks: BackgroundTasks):
    if not os.path.exists(req.image_path):
        raise HTTPException(status_code=404, detail="Input image file not found on server")

    job_id = db.create_job(
        user_id=req.user_id,
        project_id=req.project_id,
        job_type="image-to-3d",
        design_type="3D",
        output_format="STL"
    )

    def task():
        return pipeline.image_to_3d(
            image_path=req.image_path,
            desired_dims={"height": req.height, "width": req.width, "length": req.length},
            user_id=req.user_id,
            project_id=req.project_id
        )

    background_tasks.add_task(run_pipeline_with_stages, job_id, task, req.project_id, f"Image→3D: {os.path.basename(req.image_path)}", "3D")
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Image to 3D STL job queued. Stream at /api/v1/generation/stream/{job_id}"
    }


# ── 2D Endpoints ──────────────────────────────────────────────────────────────

@router.post("/text-to-2d")
async def generate_text_to_2d(req: TextTo2DRequest, background_tasks: BackgroundTasks):
    job_id = db.create_job(
        user_id=req.user_id,
        project_id=req.project_id,
        job_type="text-to-2d",
        design_type="2D",
        output_format="DXF",
        text_prompt=req.prompt
    )

    def task():
        return cad_2d.generate_from_text(
            prompt=req.prompt,
            params=req.params,
            user_id=req.user_id,
            project_id=req.project_id
        )

    background_tasks.add_task(run_pipeline_with_stages, job_id, task, req.project_id, req.prompt, "2D")
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"2D DXF job queued. Stream progress at /api/v1/generation/stream/{job_id}"
    }


@router.post("/image-to-2d")
async def generate_image_to_2d(req: ImageTo2DRequest, background_tasks: BackgroundTasks):
    if not os.path.exists(req.image_path):
        raise HTTPException(status_code=404, detail="Input image file not found on server")

    job_id = db.create_job(
        user_id=req.user_id,
        project_id=req.project_id,
        job_type="image-to-2d",
        design_type="2D",
        output_format="DXF",
        text_prompt=req.prompt
    )

    def task():
        return cad_2d.generate_from_image(
            image_path=req.image_path,
            user_prompt=req.prompt,
            params=req.params,
            user_id=req.user_id,
            project_id=req.project_id
        )

    background_tasks.add_task(run_pipeline_with_stages, job_id, task, req.project_id, req.prompt or "Image→DXF", "2D")
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Image to 2D DXF job queued. Stream at /api/v1/generation/stream/{job_id}"
    }


@router.get("/jobs/{job_id}")
def get_generation_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job
