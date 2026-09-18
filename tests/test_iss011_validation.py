import os
import pytest
from fastapi import HTTPException
from backend.app.schemas.schemas import ModelValidationRequest, ManufacturingValidationRequest
from backend.app.api.validation.router import validate_model, validate_manufacturing
from core.paths import STORAGE_DIR, ROOT_DIR

def test_iss011_validation_guards(tmp_path):
    test_storage = os.path.abspath(str(STORAGE_DIR))
    os.makedirs(test_storage, exist_ok=True)
    
    oversized_file = os.path.join(test_storage, "oversized_test.stl")
    traversal_file = os.path.join(str(tmp_path), "external.stl")
    corrupt_file = os.path.join(test_storage, "corrupt_mesh.stl")
    valid_box_file = os.path.join(test_storage, "valid_box.stl")
    
    # 1. External file (traversal attack)
    with open(traversal_file, "w") as f:
        f.write("solid external\nendsolid\n")
        
    # 2. Oversized file (>50MB)
    with open(oversized_file, "wb") as f:
        f.seek(51 * 1024 * 1024)
        f.write(b"0")

    # 3. Corrupt mesh (invalid content)
    with open(corrupt_file, "w") as f:
        f.write("This is not a valid STL file header or facet content.")

    # 4. Valid STL box
    import trimesh
    box = trimesh.creation.box(extents=(10.0, 10.0, 10.0))
    box.export(valid_box_file)

    try:
        # Test 1: Path traversal / external file access -> 403 Forbidden
        req_ext = ModelValidationRequest(file_path=traversal_file)
        with pytest.raises(HTTPException) as exc_info:
            validate_model(req_ext)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

        # Test 2: Oversized file (>50MB) -> 400 Bad Request
        req_over = ModelValidationRequest(file_path=oversized_file)
        with pytest.raises(HTTPException) as exc_info:
            validate_model(req_over)
        assert exc_info.value.status_code == 400
        assert "exceeds 50MB limit" in exc_info.value.detail

        # Test 3: Corrupt mesh -> 400 Bad Request (not 500)
        req_corrupt = ModelValidationRequest(file_path=corrupt_file)
        with pytest.raises(HTTPException) as exc_info:
            validate_model(req_corrupt)
        assert exc_info.value.status_code == 400

        # Test 4: Valid STL file -> 200 OK (returns valid ValidationResponse)
        req_valid = ModelValidationRequest(file_path=valid_box_file)
        res = validate_model(req_valid)
        assert res.is_valid is True
        assert res.is_watertight is True
        assert res.vertex_count > 0
        assert res.face_count > 0

        # Test 5: Manufacturing validation endpoint with valid STL
        mfg_req = ManufacturingValidationRequest(file_path=valid_box_file, tool_diameter_mm=3.0, max_depth_mm=20.0)
        mfg_res = validate_manufacturing(mfg_req)
        assert mfg_res.is_valid is True
        assert mfg_res.toolpath_clearance_passed is True

    finally:
        for p in [oversized_file, traversal_file, corrupt_file, valid_box_file]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def test_iss011_cwd_invariance_and_relative_paths(tmp_path):
    """Verifies that relative and absolute paths resolve consistently regardless of CWD."""
    original_cwd = os.getcwd()
    test_storage = os.path.abspath(str(STORAGE_DIR))
    os.makedirs(test_storage, exist_ok=True)
    valid_box_file = os.path.join(test_storage, "cwd_test_box.stl")

    import trimesh
    box = trimesh.creation.box(extents=(15.0, 15.0, 15.0))
    box.export(valid_box_file)

    external_attack = os.path.join(str(tmp_path), "secret.stl")
    with open(external_attack, "w") as f:
        f.write("solid secret\nendsolid\n")

    test_cwds = [
        str(ROOT_DIR),
        os.path.join(str(ROOT_DIR), "backend"),
        str(tmp_path),
    ]

    try:
        for test_cwd in test_cwds:
            os.chdir(test_cwd)
            print(f"\n[Testing from CWD: {test_cwd}]")

            # A. Relative path starting with 'storage/'
            req_rel1 = ModelValidationRequest(file_path="storage/cwd_test_box.stl")
            res1 = validate_model(req_rel1)
            assert res1.is_valid is True, f"Failed relative 'storage/' path from {test_cwd}"

            # B. Relative path relative to STORAGE_DIR directly
            req_rel2 = ModelValidationRequest(file_path="cwd_test_box.stl")
            res2 = validate_model(req_rel2)
            assert res2.is_valid is True, f"Failed relative filename path from {test_cwd}"

            # C. Absolute path
            req_abs = ModelValidationRequest(file_path=valid_box_file)
            res_abs = validate_model(req_abs)
            assert res_abs.is_valid is True, f"Failed absolute path from {test_cwd}"

            # D. Traversal Attack attempt from this CWD
            req_attack = ModelValidationRequest(file_path="../../.env")
            with pytest.raises(HTTPException) as exc:
                validate_model(req_attack)
            assert exc.value.status_code == 403, f"Attack was not blocked with 403 from {test_cwd}"

            # E. External file attack
            req_ext = ModelValidationRequest(file_path=external_attack)
            with pytest.raises(HTTPException) as exc:
                validate_model(req_ext)
            assert exc.value.status_code == 403, f"External attack was not blocked with 403 from {test_cwd}"

    finally:
        os.chdir(original_cwd)
        if os.path.exists(valid_box_file):
            try:
                os.remove(valid_box_file)
            except Exception:
                pass
        if os.path.exists(external_attack):
            try:
                os.remove(external_attack)
            except Exception:
                pass
