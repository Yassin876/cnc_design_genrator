import os
import json
from google import genai

class AIEditsGenerator:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key or "AIxxxx" in gemini_api_key:
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=gemini_api_key)
            except Exception:
                self.client = None

        self.model_name = 'gemini-3.6-flash'

    def generate_structured_edits(self, dxf_json: dict, instruction: str) -> dict:
        """
        Sends the DXF JSON and natural language instruction to Gemini and returns structured edits.
        """
        if not self.client:
            return {"resize_circles": [], "delete": []}

        system_instruction = (
            "You are a CAD DXF file editor assistant.\n\n"
            "The user will give you:\n"
            "1. A JSON description of all entities in a DXF modelspace.\n"
            "2. A natural-language instruction describing what to change.\n\n"
            "You must respond with ONLY a valid JSON object (no markdown, no explanation, no backticks) with this schema:\n\n"
            "{\n"
            "  \"delete\": [<list of integer entity ids to delete>],\n"
            "  \"resize_circles\": [\n"
            "    {\"id\": <int>, \"diameter\": <float in mm>}\n"
            "  ],\n"
            "  \"set_layer\": [\n"
            "    {\"id\": <int>, \"layer\": \"<layer name>\"}\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Only include keys that are needed; omit empty lists.\n"
            "- Never delete the main frame outline (the entity with the most points, shape=\"complex\" or shape=\"complex_closed\").\n"
            "- SHEET_BOUNDARY and MARGIN layer entities should be deleted only if the user explicitly asks.\n"
            "- When resizing circles, apply the new diameter to ALL entities where shape=\"circle\" unless the user specifies otherwise.\n"
            "- Use the entity id (integer) exactly as given in the JSON.\n"
            "- Do NOT invent entity ids that are not in the input.\n"
            "- Respond with raw JSON only — no backticks, no preamble."
        )

        user_message = (
            f"Here is the DXF entity list (JSON):\n"
            f"{json.dumps(dxf_json, indent=2)}\n\n"
            f"Instruction: {instruction}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                config=genai.types.GenerateContentConfig(
                    system_instruction=system_instruction
                ),
                contents=user_message
            )

            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            return {"resize_circles": [], "delete": []}
