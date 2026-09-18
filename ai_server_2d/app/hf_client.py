import os
import base64
import json
import requests

HF_SPACE_URL = os.getenv("HF_SPACE_URL", "https://yassin2346-img-pipline.hf.space")
HF_TOKEN = os.getenv("HF_TOKEN", "")

def get_mask_from_hf_space(image_path: str, prompt: str = "object") -> bytes:
    """
    Sends image as base64, receives binary mask as base64 PNG bytes via Gradio 5 SSE endpoint.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    # Gradio 5 standard api_prefix is /gradio_api
    base_url = HF_SPACE_URL.rstrip('/')
    url_call = f"{base_url}/gradio_api/call/predict_mask"
    payload = {
        "data": [image_b64, prompt]
    }

    resp = requests.post(url_call, json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        # Fallback to direct /call/predict_mask
        url_call = f"{base_url}/call/predict_mask"
        resp = requests.post(url_call, json=payload, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"HF Space POST error ({resp.status_code}): {resp.text}")

    event_id = resp.json().get("event_id")
    if not event_id:
        raise RuntimeError(f"No event_id returned by HF Space: {resp.text}")

    # Stream SSE response for result
    res_resp = requests.get(f"{url_call}/{event_id}", headers=headers, timeout=60, stream=True)
    if res_resp.status_code != 200:
        raise RuntimeError(f"HF Space GET event error ({res_resp.status_code}): {res_resp.text}")

    for line in res_resp.iter_lines():
        if line:
            decoded_line = line.decode("utf-8", errors="ignore")
            if decoded_line.startswith("data:"):
                raw_data = decoded_line[5:].strip()
                try:
                    data_json = json.loads(raw_data)
                    if isinstance(data_json, list) and len(data_json) > 0:
                        result_b64 = data_json[0]
                        return base64.b64decode(result_b64)
                except Exception:
                    continue

    raise RuntimeError("Failed to parse mask data from HF Space SSE stream")
