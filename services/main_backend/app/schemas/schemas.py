from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserLogin(BaseModel):
    email: str
    password: str

LoginRequest = UserLogin

class GoogleAuthRequest(BaseModel):
    token: Optional[str] = ""
    email: str
    name: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: Optional[str] = None

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    type: Optional[str] = "3D"

class ProjectVersionResponse(BaseModel):
    id: str
    project_id: str
    version_number: int
    prompt: Optional[str] = ""
    source_files: List[str] = []
    generated_files: List[str] = []
    model_metadata: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    validation_result: Dict[str, Any] = {}
    created_at: str

class ModelResponse(BaseModel):
    id: str
    project_id: str
    version_id: str
    format: str
    file_path: str
    preview_path: Optional[str] = None
    geometry_metadata: Dict[str, Any] = {}
    dimensions: Dict[str, Any] = {}
    material: str = "Aluminum 6061"
    units: str = "mm"
    status: str = "READY"
    created_at: str

class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: Optional[str] = None
    type: str = "3D"
    current_version: int = 1
    status: str = "ACTIVE"
    is_favorite: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    is_favorite: Optional[bool] = None


# Real-Time Generation Job States per Section 11
class GenerationStageEnum:
    QUEUED = "queued"
    PROCESSING = "processing"
    UNDERSTANDING = "understanding"
    GENERATING = "generating"
    GEOMETRY_PROCESSING = "geometry_processing"
    OPTIMIZING = "optimizing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobProgressEvent(BaseModel):
    job_id: str
    status: str # queued, processing, understanding, generating, geometry_processing, optimizing, validating, completed, failed, cancelled
    stage_name: str
    progress: int # 0 to 100
    message: str
    output_file_path: Optional[str] = None
    output_filename: Optional[str] = None

class TextTo3DRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    prompt: str
    height: Optional[float] = 100.0
    width: Optional[float] = 100.0
    length: Optional[float] = 100.0

class ImageTo3DRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    image_path: str
    height: Optional[float] = 100.0
    width: Optional[float] = 100.0
    length: Optional[float] = 100.0

class TextTo2DRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    prompt: str
    params: Optional[dict] = Field(default_factory=dict)

class ImageTo2DRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    image_path: str
    prompt: Optional[str] = "Vector Blueprint"
    params: Optional[dict] = Field(default_factory=dict)

class AIEditRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    file_path: str
    prompt: str
    design_type: Optional[str] = "2D"

class ParametricEditRequest(BaseModel):
    user_id: Optional[str] = "default_user"
    project_id: Optional[str] = None
    file_path: str
    parameters: Dict[str, Any]
    design_type: Optional[str] = "3D"

class GenerationJobResponse(BaseModel):
    job_id: str
    status: str
    stage_name: str
    progress: int
    message: str
    output_file_path: Optional[str] = None
    output_filename: Optional[str] = None

class StockSheetSchema(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = ""
    material: Optional[str] = "Default"
    width: float = 1200.0
    height: float = 600.0
    thickness: float = 3.0
    available_quantity: Optional[int] = 10
    unlimited_quantity: Optional[bool] = True

class NestingRequest(BaseModel):
    part_paths: List[Any]
    stock_sheets: Optional[List[StockSheetSchema]] = None
    # Legacy single-sheet fields (kept for backward-compat)
    sheet_width: Optional[float] = None
    sheet_height: Optional[float] = None
    spacing: Optional[float] = 5.0
    allow_rotate: Optional[bool] = True
    nesting_mode: Optional[str] = "Finish priority parts first"

class ModelValidationRequest(BaseModel):
    file_path: str
    tolerance_mm: Optional[float] = 0.1

class ManufacturingValidationRequest(BaseModel):
    file_path: str
    tool_diameter_mm: Optional[float] = 3.175
    max_depth_mm: Optional[float] = 50.0

class ValidationResponse(BaseModel):
    is_valid: bool
    is_watertight: bool
    bounding_box: Dict[str, float]
    vertex_count: Optional[int] = 0
    face_count: Optional[int] = 0
    volume_mm3: Optional[float] = 0.0
    surface_area_mm2: Optional[float] = 0.0
    issues: List[Any] = []
    warnings: List[str] = []
    toolpath_clearance_passed: bool = True

class ExportRequest(BaseModel):
    input_file_path: str
    export_format: str = "STL" # STL, STEP, OBJ, GLB, DXF
    dest_path: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

