import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io
import pytest
import ezdxf
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def create_valid_dxf_str():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 50), (0, 50)], close=True)
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["api_revision"] == "2d-contract-v2-paddle"
    assert data["status"] == "online"

def test_cors_headers_on_requests():
    # Preflight OPTIONS
    response = client.options(
        "/api/v1/cad/nesting",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

def test_nesting_with_in_memory_dxf():
    payload = {
        "part_paths": [
            {
                "dxf_content": create_valid_dxf_str(),
                "name": "in_memory_test_part",
                "quantity": 2,
                "thickness": 18.0
            }
        ],
        "sheet_width": 1200.0,
        "sheet_height": 600.0,
        "sheet_thickness": 18.0,
        "spacing": 5.0,
        "allow_rotate": True
    }
    response = client.post(
        "/api/v1/cad/nesting",
        json=payload,
        headers={"Origin": "http://127.0.0.1:5173"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_parts_placed" in data or "sheets" in data
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

def test_cors_headers_on_error_response():
    # Sending invalid payload that triggers 422 or 500 error
    response = client.post(
        "/api/v1/cad/nesting",
        json={"part_paths": []},
        headers={"Origin": "http://127.0.0.1:5173"}
    )
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

def test_parse_dxf_content_returns_entities_list():
    dxf_str = create_valid_dxf_str()
    response = client.post(
        "/api/v1/cad/parse-dxf-content",
        json={"dxf_content": dxf_str},
        headers={"Origin": "http://127.0.0.1:5173"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert isinstance(data["entities"], list)
    assert len(data["entities"]) > 0
    assert "points" in data["entities"][0] or "type" in data["entities"][0]

