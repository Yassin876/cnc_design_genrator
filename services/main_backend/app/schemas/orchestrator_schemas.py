from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class GenerationParamsSchema(BaseModel):
    material_thickness_mm: Optional[float] = None
    part_width_mm: Optional[float] = 0.0
    part_height_mm: Optional[float] = 0.0
    tool_diameter_mm: Optional[float] = 0.0

class ImageGenRequestSchema(BaseModel):
    image_url: str
    prompt: Optional[str] = None
    params: GenerationParamsSchema

class TextGenRequestSchema(BaseModel):
    prompt: str
    params: GenerationParamsSchema

class EditRequestSchema(BaseModel):
    dxf_url: str
    instruction: str

class StockSheetSchema(BaseModel):
    name: Optional[str] = "Sheet"
    material: Optional[str] = "Default"
    width: float
    height: float
    thickness: float = 1.0
    available_quantity: int = 1
    unlimited_quantity: bool = False

class NestRequestSchema(BaseModel):
    part_files_urls: List[str]
    stock_sheets: List[StockSheetSchema]
    spacing: float = 5.0
    allow_rotate: bool = True
    nesting_mode: str = "Finish priority parts first"
    continue_on_incomplete: bool = True

class JobStatusResponseSchema(BaseModel):
    job_id: str
    status: str
    stage: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
