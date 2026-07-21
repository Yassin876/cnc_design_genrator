import os
import json
import base64

CLASSIFY_PROMPT = """Analyze this image and determine its classification:
1. "CAD": A technical drawing, blueprint, or schematic. To be classified as "CAD", the image MUST contain ALL of the following:
   - Clear dimensions/measurements (مقاسات/أبعاد مثل 100mm, 50, etc.).
   - Directions, annotations, or orientations (اتجاهات/علامات توجيهية).
   - Dimension arrows or pointers (أسهم تشير للخطوط أو القياسات).
   If any of these three elements (dimensions, directions, arrows) are missing, it MUST NOT be classified as "CAD".

2. "REGULAR": A normal image, artistic drawing, ornament, logo, layout without annotations, or photo of an object (even if it has clean black lines on a white background, if it lacks dimensions, directions, and arrows, classify it as "REGULAR").

Return JSON only:
{
  "type": "CAD" | "REGULAR",
  "reasoning": "<one short sentence in Arabic explaining the choice>"
}

Return valid JSON code block only. No markdown formatting outside of JSON.
No explanations.
"""


def _encode_image(path: str) -> tuple[str, str]:
    """Reads an image and returns it as base64 with mime_type."""
    ext = os.path.splitext(path)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(ext, "image/png")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type

def _parse_reply(text: str) -> dict:
    clean = text
    if "```json" in clean:
        clean = clean.split("```json", 1)[1]
        clean = clean.split("```", 1)[0]
    elif "```" in clean:
        clean = clean.split("```", 1)[1]
        clean = clean.split("```", 1)[0]
    clean = clean.strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parse failed: {e}")
        return {}

def classify_image(image_path: str, api_key: str = None, model: str = "gemini-2.5-flash") -> str:
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return "REGULAR"
    
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        
        img_b64, img_mime = _encode_image(image_path)
        
        print(f"⏳ Calling Gemini to classify image...")
        response = client.models.generate_content(
            model=model,
            contents=[
                CLASSIFY_PROMPT,
                types.Part.from_bytes(
                    data=base64.b64decode(img_b64),
                    mime_type=img_mime
                ),
            ],
        )
        
        data = _parse_reply(response.text.strip())
        image_type = data.get("type", "REGULAR").upper()
        reason = data.get("reasoning", "")
        print(f"🔮 Classifier: {image_type} ({reason})")
        return image_type
    except Exception as e:
        print(f"⚠️ Gemini classification failed: {e}")
        return "REGULAR"

