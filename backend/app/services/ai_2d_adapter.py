"""
Calls ai_server_2d over HTTP when it exposes the 2d-contract-v2 routes.
Falls back to in-process generation when the microservice is stale or unreachable.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from backend.app.core.config import settings

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_AI_SERVER_ROOT = os.path.join(_PROJECT_ROOT, "ai_server_2d")

_HTTP_PATH_PROMPT = "/api/2d/generate-from-prompt"
_HTTP_PATH_IMAGE = "/api/2d/generate-from-image"
_FALLBACK_STATUS_CODES = {404, 500, 502, 503, 504}


def is_2d_service_configured() -> bool:
    """True when at least one 2D generation backend is available."""
    if settings.AI_SERVER_2D_URL:
        return True
    return bool(settings.GEMINI_API_KEY or settings.HF_TOKEN)


def _normalize_service_url(url: str) -> str:
    """Prefer IPv4 loopback to avoid Windows localhost/IPv6 resolution issues."""
    normalized = (url or "").strip().rstrip("/")
    if normalized.startswith("http://localhost"):
        return normalized.replace("http://localhost", "http://127.0.0.1", 1)
    if normalized.startswith("https://localhost"):
        return normalized.replace("https://localhost", "https://127.0.0.1", 1)
    return normalized


def _ai_server_url(path: str) -> str:
    base = _normalize_service_url(settings.AI_SERVER_2D_URL or "http://127.0.0.1:8001")
    return f"{base}{path}"


def _ensure_user_output_path(user_id: str) -> str:
    rel = os.path.join(settings.OUTPUT_DIR, "users", user_id, f"generated_2d_{uuid.uuid4().hex}.dxf")
    output_path = os.path.abspath(os.path.join(_PROJECT_ROOT, rel))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    return output_path


def _ai_server_imports():
    """Load ai_server_2d callables with its package root first on sys.path."""
    if _AI_SERVER_ROOT not in sys.path:
        sys.path.insert(0, _AI_SERVER_ROOT)
    from app.routing import route_and_generate  # noqa: WPS433
    from app.flux_gen import FluxGenerator  # noqa: WPS433

    return route_and_generate, FluxGenerator


def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text or f"2D microservice returned HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail", payload)
        if isinstance(detail, dict):
            return detail.get("message") or detail.get("code") or json.dumps(detail, ensure_ascii=False)
        if isinstance(detail, list):
            return json.dumps(detail, ensure_ascii=False)
        return str(detail)

    return str(payload)


def _map_generation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc

    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()

    if "not found" in lowered and "image" in lowered:
        return HTTPException(status_code=404, detail="Input image file not found on server")
    if "potrace" in lowered or "contour" in lowered or "no contours" in lowered:
        return HTTPException(
            status_code=422,
            detail=(
                "Could not detect a clear CNC-ready shape in the image. "
                "Upload a high-contrast silhouette (dark shape on a light background) and try again."
            ),
        )
    if "prompt is required" in lowered:
        return HTTPException(status_code=400, detail="prompt is required")

    return HTTPException(status_code=500, detail=f"2D generation failed: {message}")


async def _generate_in_process(
    *,
    prompt: Optional[str],
    image_path: Optional[str],
    params: dict,
    output_path: str,
) -> dict[str, Any]:
    route_and_generate, FluxGenerator = _ai_server_imports()

    if image_path:
        if not os.path.isfile(image_path):
            raise HTTPException(status_code=404, detail="Input image file not found on server")
        resolved_image = image_path
    else:
        if not prompt or not str(prompt).strip():
            raise HTTPException(status_code=400, detail="prompt is required")
        flux = FluxGenerator()
        generated = flux.generate_image(prompt)
        temp_dir = tempfile.mkdtemp(prefix="txt2d_")
        resolved_image = os.path.join(temp_dir, "prompt.png")
        generated.save(resolved_image)

    try:
        out = await route_and_generate(resolved_image, output_path, prompt, params or {})
    except Exception as exc:
        raise _map_generation_error(exc) from exc

    return {
        "status": "completed",
        "message": "2D DXF generation completed",
        "output_file_path": out,
        "output_filename": os.path.basename(out),
    }


async def _post_http(
    client: httpx.AsyncClient,
    path: str,
    payload: dict,
) -> Optional[httpx.Response]:
    headers = {"X-Internal-Key": settings.INTERNAL_API_KEY}
    try:
        return await client.post(_ai_server_url(path), json=payload, headers=headers)
    except httpx.RequestError:
        return None


async def _generate_with_fallback(
    *,
    prompt: Optional[str],
    image_path: Optional[str],
    params: dict,
    output_path: str,
    http_path: str,
    http_payload: dict,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await _post_http(client, http_path, http_payload)

    if response is not None and response.status_code == 200:
        try:
            return response.json()
        except ValueError as exc:
            raise HTTPException(status_code=502, detail="2D microservice returned an invalid JSON payload.") from exc

    if response is not None and response.status_code not in _FALLBACK_STATUS_CODES:
        raise HTTPException(status_code=response.status_code, detail=_extract_error_detail(response))

    try:
        return await _generate_in_process(
            prompt=prompt,
            image_path=image_path,
            params=params,
            output_path=output_path,
        )
    except HTTPException as in_process_error:
        if response is not None and response.status_code in _FALLBACK_STATUS_CODES:
            microservice_detail = _extract_error_detail(response)
            if in_process_error.status_code >= 500:
                raise HTTPException(
                    status_code=in_process_error.status_code,
                    detail=f"{in_process_error.detail} (microservice: {microservice_detail})",
                ) from in_process_error
        raise


async def generate_text_to_2d(
    *,
    user_id: str,
    prompt: str,
    params: dict,
) -> dict[str, Any]:
    output_path = _ensure_user_output_path(user_id)
    payload = {"prompt": prompt, "params": params, "output_path": output_path}
    return await _generate_with_fallback(
        prompt=prompt,
        image_path=None,
        params=params,
        output_path=output_path,
        http_path=_HTTP_PATH_PROMPT,
        http_payload=payload,
    )


async def generate_image_to_2d(
    *,
    user_id: str,
    image_path: str,
    prompt: Optional[str],
    params: dict,
) -> dict[str, Any]:
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Input image file not found on server")

    output_path = _ensure_user_output_path(user_id)
    resolved_prompt = prompt or "Vectorize and produce a CNC-ready DXF blueprint"
    payload = {
        "image_path": image_path,
        "prompt": resolved_prompt,
        "params": params,
        "output_path": output_path,
    }
    return await _generate_with_fallback(
        prompt=resolved_prompt,
        image_path=image_path,
        params=params,
        output_path=output_path,
        http_path=_HTTP_PATH_IMAGE,
        http_payload=payload,
    )
