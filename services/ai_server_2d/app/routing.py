import os
import sys
import subprocess
import glob
import shutil
import tempfile
import base64
import json
from google import genai
from google.genai import types

from app.hf_client import get_mask_from_hf_space

SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CLASSIFY_PROMPT = """Analyze this image and determine its classification:
1. "CAD": A technical drawing, blueprint, or schematic with dimensions/measurements.
2. "REGULAR": A normal image, artistic drawing, ornament, logo, or layout without annotations.

Return JSON only:
{
  "type": "CAD" | "REGULAR",
  "reasoning": "<one short sentence>"
}
"""

def _encode_image(path: str) -> tuple[str, str]:
    ext = os.path.splitext(path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type

def classify_image(image_path: str, api_key: str = None) -> str:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return "REGULAR"
    
    try:
        client = genai.Client(api_key=key)
        img_b64, img_mime = _encode_image(image_path)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                CLASSIFY_PROMPT,
                types.Part.from_bytes(data=base64.b64decode(img_b64), mime_type=img_mime),
            ],
        )
        clean = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data.get("type", "REGULAR").upper()
    except Exception:
        return "REGULAR"

async def route_and_generate(image_path: str, output_path: str, prompt: str = None, params: dict = None) -> str:
    if params is None:
        params = {}
        
    img_type = classify_image(image_path)
    
    # Run all 2D vectorization requests through the high-precision Potrace pipeline
    if False and img_type == "CAD":
        return _run_image2cad_local(image_path, output_path)
    else:
        # 1. Fetch Mask from HF ZeroGPU Space
        import asyncio
        from app.hf_client import get_mask_from_hf_space
        
        loop = asyncio.get_event_loop()
        try:
            mask_bytes = await loop.run_in_executor(
                None, 
                lambda: get_mask_from_hf_space(image_path, prompt or "object")
            )
        except Exception as err:
            print(f"[AI Server 2D] HF Space fallback trigger: {err}")
            import cv2
            import numpy as np
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
            _, buffer = cv2.imencode(".png", mask)
            mask_bytes = buffer.tobytes()
        
        # Save mask PNG to dedicated saved_masks directory for inspection
        import time
        saved_masks_dir = os.path.join(SERVICE_ROOT, "saved_masks")
        os.makedirs(saved_masks_dir, exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        saved_mask_name = f"mask_{timestamp}.png"
        saved_mask_path = os.path.join(saved_masks_dir, saved_mask_name)
        latest_mask_path = os.path.join(saved_masks_dir, "latest_mask.png")

        with open(saved_mask_path, "wb") as f:
            f.write(mask_bytes)
        shutil.copy2(saved_mask_path, latest_mask_path)
        print(f"[AI Server 2D] Saved HF mask to: {saved_mask_path}")

        # Save temporary mask PNG for processing
        temp_dir = tempfile.mkdtemp(prefix="mask_proc_")
        mask_path = os.path.join(temp_dir, "mask.png")
        with open(mask_path, "wb") as f:
            f.write(mask_bytes)
            
        # 2. Potrace Vectorization: Smooth Bezier curves + Kerf compensation via build_dxf_from_potrace
        import cv2
        from app.dxf_export import build_dxf_from_potrace

        mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
        if mask_img is None:
            raise FileNotFoundError(f"Failed to read mask image from {mask_path}")

        part_w = float(params.get("part_width_mm", 700.0))
        part_h = float(params.get("part_height_mm", 700.0))
        tool_d = float(params.get("tool_diameter_mm", 0.0))
        apply_kerf_flag = bool(params.get("apply_kerf", False)) and tool_d > 0

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        doc = build_dxf_from_potrace(
            mask_np=mask_img,
            part_width_mm=part_w,
            part_height_mm=part_h,
            tool_diameter_mm=tool_d,
            apply_kerf=apply_kerf_flag,
            output_path=output_path,
            entity_type="lwpolyline",
            bezier_steps=12,
        )

        if doc is None:
            raise RuntimeError("Potrace vectorization failed to find contours in the mask.")

        return output_path

def _run_image2cad_local(image_path: str, output_path: str) -> str:
    image_path = os.path.abspath(image_path)
    output_path = os.path.abspath(output_path)
    
    script_path = os.path.abspath(os.path.join(
        SERVICE_ROOT, "vendor", "Image2CAD-master", "Image2CAD-master", "Image2CAD", "Image2CAD_Headless.py"
    ))
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    python_exe = sys.executable

    with tempfile.TemporaryDirectory(prefix="image2cad_") as run_dir:
        isolated_image = os.path.join(run_dir, "input.png")
        shutil.copy2(image_path, isolated_image)
        folder_name = "input"

        result = subprocess.run(
            [python_exe, script_path, isolated_image],
            cwd=run_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            check=True
        )

        output_glob = os.path.join(run_dir, "Output", folder_name, "*", f"{folder_name}.dxf")
        dxf_files = glob.glob(output_glob)

        if dxf_files:
            generated_dxf = dxf_files[0]
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy2(generated_dxf, output_path)
            return output_path

        raise FileNotFoundError("Image2CAD produced no DXF output.")
