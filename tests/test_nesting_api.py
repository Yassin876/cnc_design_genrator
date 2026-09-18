"""
Test nesting API endpoint
"""
import requests
import json
import os

url = "http://127.0.0.1:8000/api/v1/cad/nesting"

# Use absolute path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dxf_path = os.path.join(project_root, "tests", "fixtures", "butterfly.dxf")


payload = {
    "part_paths": [
        {
            "path": dxf_path,
            "quantity": 1,
            "thickness": 18.0
        }
    ],
    "sheet_width": 1200.0,
    "sheet_height": 600.0,
    "sheet_thickness": 18.0,
    "spacing": 5.0,
    "allow_rotate": True
}

try:
    response = requests.post(url, json=payload, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
