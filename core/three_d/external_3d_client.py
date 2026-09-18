"""
External 3D API Client - Unified interface for all 3D generation operations

This module provides a clean, consistent interface to the external Hunyuan3D API.
All operations follow the same pattern:
1. Validate inputs
2. Call external API with proper error handling
3. Download generated STL
4. Save locally with validation
5. Return normalized result

External API Base URL: https://chargable-ashley-tychistic.ngrok-free.dev
"""

import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

logger = logging.getLogger("cad_studio.generation")

# Request lifecycle stages
class GenerationStage:
    STARTED = "STARTED"
    VALIDATING = "VALIDATING"
    SENT_TO_EXTERNAL_API = "SENT_TO_EXTERNAL_API"
    EXTERNAL_API_GENERATING = "EXTERNAL_API_GENERATING"
    RESULT_RECEIVED = "RESULT_RECEIVED"
    FILE_DOWNLOADING = "FILE_DOWNLOADING"
    FILE_SAVED = "FILE_SAVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class GenerationError(Exception):
    """Custom exception for generation errors with stage information"""
    def __init__(self, message: str, stage: str, cause: Optional[Exception] = None):
        self.message = message
        self.stage = stage
        self.cause = cause
        super().__init__(f"[{stage}] {message}")

def get_model_endpoint() -> str:
    """Get the external 3D API endpoint from configuration"""
    try:
        from backend.app.core.dynamic_endpoints import get_model_endpoint as dynamic_get
        ep = dynamic_get()
        if ep:
            return ep
    except Exception:
        pass
    load_dotenv(override=False)
    endpoint = os.getenv("MODEL_ENDPOINT", "").strip().rstrip("/")
    # Strip subpaths if misconfigured
    endpoint = endpoint.replace("/api/v1/generation", "").replace("/text-to-3d", "")
    return endpoint

def validate_endpoint(endpoint: str) -> None:
    """Validate that the endpoint is properly configured"""
    if not endpoint or not ("http://" in endpoint or "https://" in endpoint):
        raise GenerationError(
            "MODEL_ENDPOINT is not configured. Please set the Hunyuan3D API URL in settings or .env",
            GenerationStage.VALIDATING
        )

def save_stl_file(content: bytes, prefix: str = "model") -> str:
    """Save STL content to local storage with validation"""
    os.makedirs("storage/outputs/stl", exist_ok=True)
    out_path = os.path.join("storage/outputs/stl", f"{prefix}_{int(time.time() * 1000)}.stl")
    
    # Validate content
    if len(content) == 0:
        raise GenerationError("Downloaded STL file is empty", GenerationStage.FILE_DOWNLOADING)
    
    if len(content) < 100:  # Too small to be a valid STL
        raise GenerationError("Downloaded STL file is too small to be valid", GenerationStage.FILE_DOWNLOADING)
    
    # Try to validate STL header (binary STL starts with 80 bytes header + 4 bytes triangle count)
    if len(content) >= 84:
        try:
            import struct
            triangle_count = struct.unpack('<I', content[80:84])[0]
            # Validate triangle count is reasonable (0 to 10 million)
            if triangle_count > 10_000_000:
                raise GenerationError(f"Invalid STL triangle count: {triangle_count}", GenerationStage.FILE_DOWNLOADING)
            logger.info(f"[External3DClient] STL header validation passed: {triangle_count} triangles")
        except Exception as e:
            # If header validation fails, still try to save the file
            logger.warning(f"[External3DClient] STL header validation failed (continuing): {e}")
    
    with open(out_path, "wb") as f:
        f.write(content)
    
    # Verify file was written
    if not os.path.exists(out_path):
        raise GenerationError("Failed to save STL file", GenerationStage.FILE_SAVED)
    
    file_size = os.path.getsize(out_path)
    logger.info(f"[External3DClient] STL saved successfully: {out_path} ({file_size} bytes)")
    return out_path

def handle_external_api_response(resp: requests.Response, stage: str) -> Dict[str, Any]:
    """Handle and validate external API response"""
    if resp.status_code == 404:
        if "ERR_NGROK" in resp.text or "offline" in resp.text.lower():
            raise GenerationError(
                f"نفق ngrok غير متصل أو منتهي الصلاحية (ERR_NGROK_3200 Offline). يرجى تشغيل السيرفر البعيد وتحديث الرابط الجديد في الإعدادات أو .env",
                stage
            )
        raise GenerationError(
            f"الرابط المطلوب غير موجود على خادم التوليد (404 Not Found: {resp.url}). يرجى التحقق من صحة رابط السيرفر.",
            stage
        )
    elif resp.status_code == 429:
        raise GenerationError(
            "خادم التوليد مشغول بعملية أخرى حالياً، يرجى الانتظار قليلاً ثم المحاولة مرة أخرى.",
            stage
        )
    elif resp.status_code == 503:
        raise GenerationError(
            "خدمة التوليد ثلاثي الأبعاد غير متوفرة حالياً في السيرفر البعيد (503).",
            stage
        )
    elif resp.status_code == 413:
        raise GenerationError(
            "حجم الملف المرفوع يتجاوز الحد الأقصى المسموح (50 ميجابايت).",
            stage
        )
    elif resp.status_code != 200:
        if "ERR_NGROK" in resp.text:
            raise GenerationError(
                f"تعذر الاتصال بنفق ngrok ({resp.status_code}). يرجى التأكد من تشغيل نفق السيرفر البعيد.",
                stage
            )
        try:
            err_json = resp.json()
            raw_err = err_json.get("error") or err_json.get("detail") or ""
            if "ZeroGPU quota" in raw_err:
                raise GenerationError(
                    "⚠️ تم استنفاد الحصة المجانية لبطاقة الرسوميات (Hugging Face ZeroGPU Quota). يرجى الانتظار حتى يتم تجديد الحصة اليومية أو استخدام حساب Hugging Face PRO.",
                    stage
                )
            if raw_err:
                raise GenerationError(f"خطأ من خادم التوليد: {raw_err}", stage)
        except Exception as parse_err:
            if isinstance(parse_err, GenerationError):
                raise parse_err
        raise GenerationError(f"استجاب خادم التوليد برمز خطأ {resp.status_code}", stage)
    
    try:
        return resp.json()
    except Exception as e:
        raise GenerationError(f"فشل تحليل استجابة JSON: {str(e)}", stage, e)

def download_stl(download_url: str, endpoint: str) -> bytes:
    """Download STL file from external API"""
    full_download_url = f"{endpoint}{download_url}" if download_url.startswith("/") else f"{endpoint}/{download_url}"
    
    logger.info(f"[External3DClient] Downloading STL from: {full_download_url}")
    file_resp = requests.get(
        full_download_url,
        headers={"ngrok-skip-browser-warning": "true"},
        timeout=60
    )
    
    if file_resp.status_code != 200:
        raise GenerationError(
            f"فشل تحميل ملف الـ STL (رمز الاستجابة {file_resp.status_code})",
            GenerationStage.FILE_DOWNLOADING
        )
    
    content = file_resp.content
    if len(content) == 0:
        raise GenerationError("Downloaded STL file is empty", GenerationStage.FILE_DOWNLOADING)
    
    logger.info(f"[External3DClient] STL downloaded successfully ({len(content)} bytes)")
    return content

def text_to_3d(prompt: str, height: float = 50.0, width: float = 100.0, length: float = 100.0) -> str:
    """
    3D text-to-CAD generation via Hunyuan3D API.
    
    Args:
        prompt: Text description for 3D model
        height: Target height in mm
        width: Target width in mm  
        length: Target length in mm
    
    Returns:
        Local path to generated STL file
    
    Raises:
        GenerationError: If generation fails at any stage
    """
    try:
        # Validation
        if not prompt or not prompt.strip():
            raise GenerationError("Text prompt is required for 3D generation", GenerationStage.VALIDATING)
        
        endpoint = get_model_endpoint()
        validate_endpoint(endpoint)
        
        # API Call
        target_url = f"{endpoint}/text"
        headers = {"ngrok-skip-browser-warning": "true"}
        form_data = {"prompt": prompt.strip()}
        
        logger.info(f"[External3DClient] {GenerationStage.SENT_TO_EXTERNAL_API}: POST {target_url} with prompt: \"{prompt}\"")
        
        resp = requests.post(target_url, data=form_data, headers=headers, timeout=300)
        data = handle_external_api_response(resp, GenerationStage.EXTERNAL_API_GENERATING)
        
        # Response Validation
        if not data.get("success") or not data.get("download_url"):
            err_detail = data.get("error", "فشل التوليد في خادم الذكاء الاصطناعي")
            raise GenerationError(f"فشل التوليد: {err_detail}", GenerationStage.RESULT_RECEIVED)
        
        # Download STL
        download_url = data["download_url"]
        content = download_stl(download_url, endpoint)
        
        # Save STL
        out_path = save_stl_file(content, "model")
        
        logger.info(f"[External3DClient] {GenerationStage.COMPLETED}: Text-to-3D generation successful")
        return out_path
        
    except requests.exceptions.Timeout:
        raise GenerationError(
            "استغرق التوليد وقتاً أطول من المتوقع (أكثر من 5 دقائق). الخادم قد يكون تحت ضغط، يرجى إعادة المحاولة.",
            GenerationStage.EXTERNAL_API_GENERATING
        )
    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(
            f"Unexpected error during text-to-3D generation: {str(e)}",
            GenerationStage.FAILED,
            e
        )

def image_to_3d(image_path: str, height: float = 50.0, width: float = 100.0, length: float = 100.0) -> str:
    """
    3D image-to-CAD generation via Hunyuan3D API.
    
    Args:
        image_path: Path to input image file
        height: Target height in mm
        width: Target width in mm
        length: Target length in mm
    
    Returns:
        Local path to generated STL file
    
    Raises:
        GenerationError: If generation fails at any stage
    """
    try:
        # Validation
        if not os.path.exists(image_path):
            raise GenerationError(f"Input image file not found: {image_path}", GenerationStage.VALIDATING)
        
        endpoint = get_model_endpoint()
        validate_endpoint(endpoint)
        
        # API Call
        target_url = f"{endpoint}/image"
        headers = {"ngrok-skip-browser-warning": "true"}
        
        logger.info(f"[External3DClient] {GenerationStage.SENT_TO_EXTERNAL_API}: POST {target_url} with file: {image_path}")
        
        mime_type = "image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        with open(image_path, "rb") as img_file:
            files = {"file": (os.path.basename(image_path), img_file, mime_type)}
            resp = requests.post(target_url, files=files, headers=headers, timeout=300)
        
        data = handle_external_api_response(resp, GenerationStage.EXTERNAL_API_GENERATING)
        
        # Response Validation
        if not data.get("success") or not data.get("download_url"):
            err_detail = data.get("error", "فشل التوليد في خادم الذكاء الاصطناعي")
            raise GenerationError(f"فشل التوليد من الصورة: {err_detail}", GenerationStage.RESULT_RECEIVED)
        
        # Download STL
        download_url = data["download_url"]
        content = download_stl(download_url, endpoint)
        
        # Save STL
        out_path = save_stl_file(content, "model_img")
        
        logger.info(f"[External3DClient] {GenerationStage.COMPLETED}: Image-to-3D generation successful")
        return out_path
        
    except requests.exceptions.Timeout:
        raise GenerationError(
            "استغرق التوليد من الصورة وقتاً أطول من المتوقع (أكثر من 5 دقائق). الخادم قد يكون تحت ضغط، يرجى إعادة المحاولة.",
            GenerationStage.EXTERNAL_API_GENERATING
        )
    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(
            f"Unexpected error during image-to-3D generation: {str(e)}",
            GenerationStage.FAILED,
            e
        )

def edit_3d(file_path: str, prompt: str, multi_view: bool = False) -> str:
    """
    3D model / image edit via Hunyuan3D API.
    
    Args:
        file_path: Path to input file (image or 3D model)
        prompt: Edit instruction
        multi_view: Whether to use multi-view editing
    
    Returns:
        Local path to generated STL file
    
    Raises:
        GenerationError: If generation fails at any stage
    """
    try:
        # Validation
        if not file_path or not os.path.exists(file_path):
            raise GenerationError(f"Input file not found: {file_path}", GenerationStage.VALIDATING)
        
        endpoint = get_model_endpoint()
        validate_endpoint(endpoint)
        
        # API Call
        target_url = f"{endpoint}/edit"
        headers = {"ngrok-skip-browser-warning": "true"}
        
        logger.info(f"[External3DClient] {GenerationStage.SENT_TO_EXTERNAL_API}: POST {target_url} with file: {file_path}, prompt: \"{prompt}\"")
        
        with open(file_path, "rb") as model_file:
            files = {"file": (os.path.basename(file_path), model_file)}
            form_fields = {"prompt": prompt or "Edit and refine 3D model", "multi_view": str(multi_view).lower()}
            resp = requests.post(target_url, files=files, data=form_fields, headers=headers, timeout=300)
        
        data = handle_external_api_response(resp, GenerationStage.EXTERNAL_API_GENERATING)
        
        # Response Validation
        if not data.get("success") or not data.get("download_url"):
            err_detail = data.get("error", "فشل تعديل المجسم في خادم الذكاء الاصطناعي")
            raise GenerationError(f"فشل التعديل ثلاثي الأبعاد: {err_detail}", GenerationStage.RESULT_RECEIVED)
        
        # Download STL
        download_url = data["download_url"]
        content = download_stl(download_url, endpoint)
        
        # Save STL
        out_path = save_stl_file(content, "model_edit")
        
        logger.info(f"[External3DClient] {GenerationStage.COMPLETED}: 3D edit successful")
        return out_path
        
    except requests.exceptions.Timeout:
        raise GenerationError(
            "استغرق تعديل المجسم وقتاً أطول من المتوقع (أكثر من 3 دقائق). الخادم قد يكون تحت ضغط، يرجى إعادة المحاولة.",
            GenerationStage.EXTERNAL_API_GENERATING
        )
    except GenerationError:
        raise
    except Exception as e:
        raise GenerationError(
            f"Unexpected error during 3D edit: {str(e)}",
            GenerationStage.FAILED,
            e
        )
