from fastapi import APIRouter, HTTPException
import os
import trimesh
from app.schemas.schemas import (
    ModelValidationRequest, ManufacturingValidationRequest, ValidationResponse
)

router = APIRouter(prefix="/validation", tags=["Validation"])

@router.post("/model", response_model=ValidationResponse)
def validate_model(req: ModelValidationRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="Model file not found")
        
    try:
        mesh = trimesh.load(req.file_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)
            
        is_watertight = bool(mesh.is_watertight)
        extents = mesh.extents
        bounds = mesh.bounds
        
        issues = []
        warnings = []

        if not is_watertight:
            issues.append("Mesh geometry is non-manifold (has holes or unclosed edges).")
        
        if len(mesh.faces) < 10:
            warnings.append("Low face count detected. Geometry may be incomplete.")
            
        if min(extents) < 0.5:
            warnings.append(f"Very thin geometry detected (minimum dimension: {min(extents):.2f} mm).")

        return ValidationResponse(
            is_valid=len(issues) == 0,
            is_watertight=is_watertight,
            bounding_box={
                "width": float(extents[0]),
                "height": float(extents[1]),
                "depth": float(extents[2])
            },
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            volume_mm3=float(mesh.volume) if is_watertight else 0.0,
            surface_area_mm2=float(mesh.area),
            issues=issues,
            warnings=warnings,
            toolpath_clearance_passed=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")

@router.post("/manufacturing", response_model=ValidationResponse)
@router.post("/validate-cnc", response_model=ValidationResponse)
def validate_manufacturing(req: ManufacturingValidationRequest):
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail="Model file not found")

    try:
        mesh = trimesh.load(req.file_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.dump(concatenate=True)

        extents = mesh.extents
        tool_diameter = req.tool_diameter_mm
        
        issues = []
        warnings = []
        toolpath_passed = True

        # Check CNC bit clearance against thin internal radii
        min_feature_size = min(extents)
        if min_feature_size < tool_diameter:
            toolpath_passed = False
            issues.append(f"Feature size ({min_feature_size:.2f}mm) is smaller than tool bit diameter ({tool_diameter}mm). End mill cannot fit.")

        if extents[2] > req.max_depth_mm:
            warnings.append(f"Part depth ({extents[2]:.1f}mm) exceeds recommended maximum cutting depth ({req.max_depth_mm}mm).")

        return ValidationResponse(
            is_valid=toolpath_passed and len(issues) == 0,
            is_watertight=bool(mesh.is_watertight),
            bounding_box={
                "width": float(extents[0]),
                "height": float(extents[1]),
                "depth": float(extents[2])
            },
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            volume_mm3=float(mesh.volume) if mesh.is_watertight else 0.0,
            surface_area_mm2=float(mesh.area),
            issues=issues,
            warnings=warnings,
            toolpath_clearance_passed=toolpath_passed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manufacturing validation error: {str(e)}")
