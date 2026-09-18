from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import os
import sys
import time
import uuid

# Ensure root workspace is on python path so `core` can be imported seamlessly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.core.config import settings
from backend.app.core.logging import request_logger, error_logger
from backend.app.core.storage import ensure_storage_directories
from backend.app.api.auth.router import router as auth_router
from backend.app.api.projects.router import router as projects_router
from backend.app.api.generation.router import router as generation_router
from backend.app.api.editing.router import router as editing_router
from backend.app.api.cad.router import router as cad_router
from backend.app.api.files.router import router as files_router
from backend.app.api.validation.router import router as validation_router
from backend.app.api.export.router import router as export_router
from backend.app.api.billing.router import router as billing_router



@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_storage_directories()
    # Initialize database tables
    from backend.app.db.session import init_db
    init_db()
    
    request_logger.info(
        f"Anti Design Backend v{settings.VERSION} starting ({settings.ENVIRONMENT})",
        extra={
            "category": "lifecycle",
            "uploads": os.path.abspath(settings.UPLOAD_DIR),
            "outputs": os.path.abspath(settings.OUTPUT_DIR),
            "temp": os.path.abspath(settings.TEMP_DIR),
        },
    )
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)

# ── CORS Setup ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Section 39: Request Logging Middleware ────────────────────
@app.middleware("http")
async def structured_request_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    # Attach request_id to state for downstream use
    request.state.request_id = request_id

    request_logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "ip": request.client.host if request.client else "unknown",
        }
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.time() - start) * 1000)
        error_logger.error(
            f"Unhandled exception on {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url.path),
                "duration_ms": duration_ms,
            },
            exc_info=exc,
        )
        origin = request.headers.get("origin", "*")
        headers = {
            "Access-Control-Allow-Origin": origin if origin != "null" else "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*",
        }
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Engineering Backend Error: {str(exc)}"},
            headers=headers
        )

    duration_ms = int((time.time() - start) * 1000)
    request_logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({duration_ms}ms)",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }
    )
    return response


# ── Mount Routers under /api/v1 ──────────────────────────────
v1_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=v1_prefix)
app.include_router(projects_router, prefix=v1_prefix)
app.include_router(generation_router, prefix=v1_prefix)
app.include_router(editing_router, prefix=v1_prefix)
app.include_router(cad_router, prefix=v1_prefix)
app.include_router(files_router, prefix=v1_prefix)
app.include_router(validation_router, prefix=v1_prefix)
app.include_router(export_router, prefix=v1_prefix)
app.include_router(billing_router, prefix=v1_prefix)


# ── Static File Mounts ───────────────────────────────────────
outputs_path = os.path.abspath(settings.OUTPUT_DIR)
os.makedirs(outputs_path, exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=outputs_path), name="outputs")

uploads_path = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(uploads_path, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=uploads_path), name="uploads")


# ── Health Check ─────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.get(f"{settings.API_V1_STR}/health")
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "api_revision": "2d-contract-v2-paddle",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }



# ── Global Exception Handler ────────────────────────────────
from backend.app.core.exceptions import AuthException

@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    origin = request.headers.get("origin", "*")
    headers = {
        "Access-Control-Allow-Origin": origin if origin != "null" else "*",
        "Access-Control-Allow-Credentials": "true",
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
        headers=headers
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_logger.error(
        f"Global exception: {str(exc)}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
        },
        exc_info=exc,
    )
    origin = request.headers.get("origin", "*")
    headers = {
        "Access-Control-Allow-Origin": origin if origin != "null" else "*",
        "Access-Control-Allow-Credentials": "true",
    }
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"Internal Engineering Backend Error: {str(exc)}",
            "code": "INTERNAL_SERVER_ERROR"
        },
        headers=headers
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=(settings.ENVIRONMENT == "development"),
    )
