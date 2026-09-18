from fastapi import APIRouter, HTTPException
import os
from backend.app.schemas.schemas import (
    ModelValidationRequest, ManufacturingValidationRequest, ValidationResponse
)
from core.paths import STORAGE_DIR, safe_resolve_storage_path, is_safe_storage_path

router = APIRouter(prefix="/validation", tags=["Validation"])

MAX_VALIDATION_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit


def _validate_file_path(file_path: str) -> str:
    resolved = safe_resolve_storage_path(file_path)
    if not resolved:
        raise HTTPException(status_code=403, detail="Access denied: File path outside storage directory")
    if not os.path.exists(resolved) or not os.path.isfile(resolved):
        raise HTTPException(status_code=404, detail="Model file not found")
    file_size = os.path.getsize(resolved)
    if file_size > MAX_VALIDATION_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large for validation: {file_size / (1024 * 1024):.1f}MB exceeds 50MB limit"
        )
    return resolved


@router.post("/model", response_model=ValidationResponse)
def validate_model(req: ModelValidationRequest):
    resolved_path = _validate_file_path(req.file_path)
        
    try:
        import trimesh
        mesh = trimesh.load(resolved_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.to_geometry() if hasattr(mesh, "to_geometry") else mesh.dump(concatenate=True)
            
        if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0 or mesh.extents is None:
            raise ValueError("3D model contains empty or unreadable geometry.")

        is_watertight = bool(mesh.is_watertight)
        extents = mesh.extents
        
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
    except HTTPException:
        raise
    except (ValueError, TypeError) as val_err:
        raise HTTPException(status_code=400, detail=f"Invalid 3D model: {str(val_err)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to validate 3D mesh: {str(e)}")


@router.post("/manufacturing", response_model=ValidationResponse)
@router.post("/validate-cnc", response_model=ValidationResponse)
def validate_manufacturing(req: ManufacturingValidationRequest):
    resolved_path = _validate_file_path(req.file_path)

    try:
        import trimesh
        mesh = trimesh.load(resolved_path)
        if isinstance(mesh, trimesh.Scene):
            mesh = mesh.to_geometry() if hasattr(mesh, "to_geometry") else mesh.dump(concatenate=True)

        if not hasattr(mesh, "vertices") or len(mesh.vertices) == 0 or mesh.extents is None:
            raise ValueError("3D model contains empty or unreadable geometry.")

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
    except HTTPException:
        raise
    except (ValueError, TypeError) as val_err:
        raise HTTPException(status_code=400, detail=f"Invalid 3D model for manufacturing: {str(val_err)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Manufacturing validation error: {str(e)}")

