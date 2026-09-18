#!/usr/bin/env python3
"""Smoke test for synchronous 2D generation endpoints."""

from __future__ import annotations

import os
import sys
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
BASE = "http://127.0.0.1:8000/api/v1"


def _auth_headers(client: httpx.Client) -> dict[str, str]:
    email = f"gen_smoke_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        f"{BASE}/auth/register-dev",
        json={"email": email, "password": "Test1234!", "name": "Generation Smoke Test"},
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _sample_shape_png() -> bytes:
    image = Image.new("RGB", (320, 320), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([60, 60, 260, 260], fill="black")
    draw.ellipse([120, 120, 200, 200], fill="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> int:
    failures: list[str] = []

    with httpx.Client(timeout=180.0) as client:
        headers = _auth_headers(client)

        text_payload = {
            "prompt": "simple CNC star silhouette",
            "params": {
                "part_width_mm": 500,
                "part_height_mm": 500,
                "tool_diameter_mm": 6,
            },
        }
        text_response = client.post(
            f"{BASE}/generation/text-to-2d",
            headers=headers,
            json=text_payload,
        )
        print("text-to-2d:", text_response.status_code, text_response.text[:180])
        if text_response.status_code != 200:
            failures.append("text-to-2d failed")
        else:
            dxf_path = text_response.json().get("output_file_path")
            if not dxf_path or not os.path.isfile(dxf_path):
                failures.append("text-to-2d did not produce a DXF file")

        upload = client.post(
            f"{BASE}/files/upload",
            headers=headers,
            files={"file": ("sample_shape.png", _sample_shape_png(), "image/png")},
        )
        print("upload:", upload.status_code, upload.text[:180])
        upload.raise_for_status()
        image_path = upload.json()["saved_path"]

        image_payload = {
            "image_path": image_path,
            "prompt": "vectorize this CNC shape",
            "params": text_payload["params"],
        }
        image_response = client.post(
            f"{BASE}/generation/image-to-2d",
            headers=headers,
            json=image_payload,
        )
        print("image-to-2d:", image_response.status_code, image_response.text[:180])
        if image_response.status_code != 200:
            failures.append("image-to-2d failed")
        else:
            dxf_path = image_response.json().get("output_file_path")
            if not dxf_path or not os.path.isfile(dxf_path):
                failures.append("image-to-2d did not produce a DXF file")

    if failures:
        print("FAILED:", ", ".join(failures))
        return 1

    print("PASS: 2D generation smoke test succeeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
