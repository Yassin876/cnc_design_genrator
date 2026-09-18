#!/usr/bin/env python3
"""Smoke test: generate a 2D DXF then nest it on a stock sheet."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
BASE = "http://127.0.0.1:8000/api/v1"


def main() -> int:
    with httpx.Client(timeout=180.0) as client:
        health = client.get(f"{BASE}/health")
        print("backend health:", health.status_code, health.text[:160])
        health.raise_for_status()

        email = f"nest_smoke_{uuid.uuid4().hex[:8]}@example.com"
        auth = client.post(
            f"{BASE}/auth/register-dev",
            json={"email": email, "password": "Test1234!", "name": "Nesting Smoke"},
        )
        print("register-dev:", auth.status_code)
        auth.raise_for_status()
        headers = {"Authorization": f"Bearer {auth.json()['access_token']}"}

        gen = client.post(
            f"{BASE}/generation/text-to-2d",
            headers=headers,
            json={
                "prompt": "simple CNC square plate",
                "params": {
                    "part_width_mm": 120,
                    "part_height_mm": 80,
                    "tool_diameter_mm": 6,
                },
            },
        )
        print("text-to-2d:", gen.status_code, gen.text[:180])
        if gen.status_code != 200:
            print("FAIL: generation")
            return 1

        dxf_path = gen.json()["output_file_path"]
        if not os.path.isfile(dxf_path):
            print("FAIL: generated DXF missing on disk")
            return 1

        parsed = client.get(
            f"{BASE}/cad/parse-dxf",
            headers=headers,
            params={"file_path": dxf_path},
        )
        print("parse-dxf:", parsed.status_code)
        if parsed.status_code != 200:
            print("FAIL: parse-dxf", parsed.text[:200])
            return 1
        entities = parsed.json().get("entities")
        count = len(entities) if isinstance(entities, list) else "n/a"
        print("parse-dxf entities:", count)

        nest = client.post(
            f"{BASE}/cad/nesting",
            headers=headers,
            json={
                "part_paths": [{"path": dxf_path, "quantity": 1, "thickness": 18}],
                "sheet_width": 1200,
                "sheet_height": 600,
                "sheet_thickness": 18,
                "spacing": 5,
                "allow_rotate": True,
            },
        )
        print("nesting:", nest.status_code, nest.text[:400])
        if nest.status_code != 200:
            print("FAIL: nesting")
            return 1

        data = nest.json()
        placed = data.get("total_parts_placed", 0)
        sheets = data.get("sheets") or []
        nested_path = sheets[0].get("dxf_path") if sheets else None
        print(
            "placed:",
            placed,
            "sheets:",
            data.get("total_sheets_used"),
            "nested:",
            nested_path,
        )
        if placed < 1 or not nested_path or not os.path.isfile(nested_path):
            print("FAIL: nesting did not produce a nested DXF")
            return 1

        parsed_nested = client.get(
            f"{BASE}/cad/parse-dxf",
            headers=headers,
            params={"file_path": nested_path},
        )
        print("parse nested dxf:", parsed_nested.status_code)
        if parsed_nested.status_code != 200:
            print("FAIL: nested DXF did not parse")
            return 1

    print("PASS: nesting smoke test succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
