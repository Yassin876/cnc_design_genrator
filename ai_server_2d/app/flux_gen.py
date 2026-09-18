import os
import io
from google import genai
from huggingface_hub import InferenceClient
from PIL import Image

class FluxGenerator:
    def __init__(self):
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

    def generate_image(self, user_description: str) -> Image.Image:
        """
        Generates a 2D silhouette image using Flux.1-schnell or Pillow fallback.
        """
        suffix = (
            ", solid black silhouette, minimalist 2D vector style, "
            "isolated on pure white background, high contrast, no shadows, "
            "no gradients, clean edges, flat design."
        )
        full_prompt = f"{user_description}{suffix}"
        
        if self.flux_client:
            try:
                image = self.flux_client.text_to_image(full_prompt)
                return image
            except Exception:
                pass
        
        from PIL import ImageDraw
        img = Image.new("RGB", (512, 512), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([100, 100, 412, 412], fill="black")
        draw.ellipse([180, 180, 332, 332], fill="white")
        return img
