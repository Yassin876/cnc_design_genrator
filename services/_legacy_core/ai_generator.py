import os
import io
import sys
import json
from google import genai
from huggingface_hub import InferenceClient
from PIL import Image
from dotenv import load_dotenv

# Ensure stdout handles UTF-8 on Windows without charmap encoding crashes
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables from .env file
load_dotenv()

class AIGenerator:
    def __init__(self):
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key or "AIxxxx" in gemini_api_key:
            print("⚠️ Warning: GEMINI_API_KEY is missing or unconfigured in .env file.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=gemini_api_key)
            except Exception as e:
                print(f"⚠️ Warning: Failed to initialize Google GenAI Client: {e}")
                self.client = None

        self.model_name = 'gemini-3.6-flash'
        
        # Configure Flux via Hugging Face Inference Client (Optional)
        hf_token = os.getenv("HF_TOKEN")
        if hf_token and not hf_token.startswith("hf_xxxx"):
            try:
                self.flux_client = InferenceClient(
                    model="black-forest-labs/FLUX.1-schnell",
                    token=hf_token
                )
            except Exception:
                self.flux_client = None
        else:
            self.flux_client = None

    def extract_main_object(self, user_description: str) -> str:
        """
        Extracts the single most important noun from the description using Gemini.
        """
        if not self.client:
            return "object"

        system_instruction = (
            "You are a specialized assistant for a CAD/CNC software. "
            "Your task is to extract the single most important noun (the main object) "
            "from a user's drawing description. This noun will be used for image segmentation. "
            "Return ONLY the noun in English, lowercase, no punctuation."
        )
        
        full_prompt = f"{system_instruction}\n\nUser description: '{user_description}'\nMain object:"
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt
            )
            object_name = response.text.strip().lower()
            if "\n" in object_name:
                object_name = object_name.split("\n")[-1].strip()
            return object_name
        except Exception as e:
            print(f"⚠️ Warning: Gemini extraction failed ({e}). Falling back to 'object'.")
            return "object"

    def generate_image(self, user_description: str):
        """
        Generates a high-contrast 2D silhouette image using Flux.1-schnell if available, or returns a fallback Pillow Image.
        """
        suffix = (
            ", solid black silhouette, minimalist 2D vector style, "
            "isolated on pure white background, high contrast, no shadows, "
            "no gradients, clean edges, flat design."
        )
        full_prompt = f"{user_description}{suffix}"
        
        if self.flux_client:
            try:
                print(f"Generating image via Flux for: '{user_description}'...")
                image = self.flux_client.text_to_image(full_prompt)
                return image
            except Exception as e:
                print(f"Warning: Flux image generation failed ({e}). Creating fallback vector silhouette.")
        
        # Fallback vector shape generation using Pillow
        from PIL import ImageDraw
        img = Image.new("RGB", (512, 512), "white")
        draw = ImageDraw.Draw(img)
        # Draw a clean high-contrast black gear / part silhouette
        draw.rectangle([100, 100, 412, 412], fill="black")
        draw.ellipse([180, 180, 332, 332], fill="white")
        return img

    def generate_structured_edits(self, dxf_json: dict, instruction: str) -> dict:
        """
        Sends the DXF JSON and natural language instruction to Gemini and returns structured edits.
        """
        if not self.client:
            # Fallback edit dictionary if Gemini is unavailable
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
            print(f"Gemini structured modification failed ({e}). Returning fallback edit structure.")
            return {"resize_circles": [], "delete": []}
