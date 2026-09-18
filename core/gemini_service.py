"""
Gemini Service Module for CNC Design Generator.
Provides AI-assisted intent classification and image routing (CAD vs Regular) with robust offline fallbacks.
"""
import os
import sys
import json
import base64
from typing import Dict, Any, Optional

# Ensure standard output encoding on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _get_api_key() -> str:
    """Retrieve Gemini API key from environment variables."""
    return os.getenv("GEMINI_API_KEY", "").strip()


def _fallback_intent(user_text: str, has_attachment: bool, has_active_cad: bool, current_mode: str) -> Dict[str, Any]:
    """Deterministic rule-based intent classification fallback."""
    text_lower = (user_text or "").lower()
    is_3d = current_mode.upper() == "3D"

    # 1. Edit intent
    if has_active_cad or any(w in text_lower for w in ["edit", "modify", "cut", "resize", "scale", "fillet", "chamfer", "hole"]):
        intent = "edit_3d" if is_3d else "edit_dxf"
        reply = f"Applying edit instruction to active {current_mode} design."
    # 2. Image conversion intent
    elif has_attachment:
        intent = "image_to_3d" if is_3d else "image_to_cad"
        reply = f"Processing attached image into {current_mode} CAD model."
    # 3. Generation intent
    elif any(w in text_lower for w in ["create", "generate", "design", "make", "draw", "model", "build", "gear", "bracket", "box"]):
        intent = "generate_3d" if is_3d else "generate_2d"
        reply = f"Generating new {current_mode} design for: '{user_text}'."
    # 4. General conversational chat
    elif len(text_lower.split()) < 3 and any(w in text_lower for w in ["hello", "hi", "help", "hey", "مرحبا", "سلام"]):
        intent = "general_chat"
        reply = "Hello! I am your CNC AI engineering assistant. What would you like to design or edit today?"
    else:
        intent = "generate_3d" if is_3d else "generate_2d"
        reply = f"Starting {current_mode} generation for: '{user_text}'."

    return {
        "intent": intent,
        "prompt_payload": user_text,
        "reply_text": reply,
        "reasoning": "Rule-based classification fallback",
    }


def classify_user_intent(
    user_text: str,
    has_attachment: bool = False,
    has_active_cad: bool = False,
    current_mode: str = "2D"
) -> Dict[str, Any]:
    """
    Classifies user natural language input into actionable CAD pipeline intents.
    Intents: ["generate_2d", "generate_3d", "image_to_cad", "edit_3d", "edit_dxf", "general_chat"]
    """
    api_key = _get_api_key()
    if not api_key:
        return _fallback_intent(user_text, has_attachment, has_active_cad, current_mode)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        system_instruction = f"""You are an AI CAD Router for Anti Design CNC Studio.
Analyze the user request and context:
- User Message: "{user_text}"
- Has Attachment (Image/File): {has_attachment}
- Has Active Model in Viewport: {has_active_cad}
- Current Active Canvas Mode: {current_mode}

Classify into exactly one of these intents:
1. "generate_2d": Text prompt to create a new 2D vector/DXF drawing.
2. "generate_3d": Text prompt to create a new 3D STL/mesh solid model.
3. "image_to_cad": Converting an attached image/sketch into a 2D DXF or 3D model.
4. "edit_dxf": Modifying an active 2D DXF drawing.
5. "edit_3d": Modifying an active 3D STL model.
6. "general_chat": Conversational questions, greeting, or CNC tooling advice.

Return strictly valid JSON with no markdown tags:
{{
  "intent": "generate_2d" | "generate_3d" | "image_to_cad" | "edit_3d" | "edit_dxf" | "general_chat",
  "prompt_payload": "<extracted core CAD generation or edit prompt>",
  "reply_text": "<short friendly engineer confirmation in English or Arabic>",
  "reasoning": "<one sentence explanation>"
}}"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=system_instruction
        )
        
        raw_text = (response.text or "").strip()
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)

        if "intent" not in data:
            return _fallback_intent(user_text, has_attachment, has_active_cad, current_mode)

        if "prompt_payload" not in data or not data["prompt_payload"]:
            data["prompt_payload"] = user_text

        return data

    except Exception:
        # Graceful fallback to rule-based parser on any network or API error
        return _fallback_intent(user_text, has_attachment, has_active_cad, current_mode)


def classify_image(image_path: str, api_key: Optional[str] = None) -> str:
    """
    Analyzes an image and classifies whether it is a technical blueprint ("CAD") or a decorative image ("REGULAR").
    """
    key = api_key or _get_api_key()
    if not key or not os.path.exists(image_path):
        return "REGULAR"

    try:
        from google import genai
        from google.genai import types

        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/png")

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        client = genai.Client(api_key=key)
        prompt = "Determine if this image is a technical blueprint/dimensioned schematic ('CAD') or standard artwork/ornament ('REGULAR'). Return JSON: {\"type\": \"CAD\" | \"REGULAR\"}"

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ]
        )

        clean = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data.get("type", "REGULAR").upper()
    except Exception:
        return "REGULAR"
