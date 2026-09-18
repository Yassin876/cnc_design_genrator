import os
import json
from dotenv import load_dotenv

CONFIG_FILE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "api_endpoints.json")
)

def get_dynamic_endpoints() -> dict:
    """
    Reads backend/config/api_endpoints.json dynamically on every call.
    This guarantees that URL updates (e.g. fresh ngrok URLs) take effect
    immediately without rebuilding or restarting the application.
    """
    endpoints = {
        "model_endpoint": "",
        "external_2d_api_url": "",
        "external_2d_api_key": ""
    }

    # 1. Check external JSON config file first
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if data.get("model_endpoint"):
                        endpoints["model_endpoint"] = str(data["model_endpoint"]).strip()
                    if data.get("external_2d_api_url"):
                        endpoints["external_2d_api_url"] = str(data["external_2d_api_url"]).strip()
                    if data.get("external_2d_api_key"):
                        endpoints["external_2d_api_key"] = str(data["external_2d_api_key"]).strip()
        except Exception as e:
            print(f"[Config Watcher] Warning reading {CONFIG_FILE_PATH}: {e}")

    # 2. Fall back to environment variables (.env) if not set in JSON
    load_dotenv(override=False)
    if not endpoints["model_endpoint"]:
        endpoints["model_endpoint"] = os.getenv("MODEL_ENDPOINT", "").strip()
    if not endpoints["external_2d_api_url"]:
        endpoints["external_2d_api_url"] = os.getenv("EXTERNAL_2D_API_URL", "").strip()
    if not endpoints["external_2d_api_key"]:
        endpoints["external_2d_api_key"] = os.getenv("EXTERNAL_2D_API_KEY", "").strip()

    return endpoints


def get_model_endpoint() -> str:
    """
    Returns the normalized 3D Model Endpoint (e.g. ngrok base URL).
    """
    endpoints = get_dynamic_endpoints()
    raw = endpoints.get("model_endpoint", "").rstrip("/")
    # Strip unnecessary path suffixes if user pasted a full endpoint
    cleaned = raw.replace("/api/v1/generation", "").replace("/text-to-3d", "").replace("/text", "").replace("/image", "")
    return cleaned


def get_external_2d_endpoint() -> tuple[str, str]:
    """
    Returns (url, api_key) for external 2D generation service.
    """
    endpoints = get_dynamic_endpoints()
    return endpoints.get("external_2d_api_url", ""), endpoints.get("external_2d_api_key", "")


def update_dynamic_endpoints(
    model_endpoint: str | None = None,
    external_2d_api_url: str | None = None,
    external_2d_api_key: str | None = None,
) -> dict:
    """
    Updates backend/config/api_endpoints.json with new endpoint URLs.
    """
    current = get_dynamic_endpoints()
    if model_endpoint is not None:
        current["model_endpoint"] = model_endpoint.strip()
    if external_2d_api_url is not None:
        current["external_2d_api_url"] = external_2d_api_url.strip()
    if external_2d_api_key is not None:
        current["external_2d_api_key"] = external_2d_api_key.strip()

    os.makedirs(os.path.dirname(CONFIG_FILE_PATH), exist_ok=True)
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "_comment": "Configure external AI generation endpoints here without rebuilding or restarting the application. Changes take effect on the next request.",
            "model_endpoint": current["model_endpoint"],
            "external_2d_api_url": current["external_2d_api_url"],
            "external_2d_api_key": current["external_2d_api_key"],
        }, f, indent=2)

    return current

