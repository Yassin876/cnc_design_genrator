"""
Cells 3-5 من النوت بوك: تسجيل دخول Hugging Face + تحميل موديل SAM3 + توليد القناع
(mask) للجسم باستخدام box prompt.

الفرق عن Colab:
- التوكن بييجي من ملف .env (متغير HF_TOKEN) بدل ما يتكتب يدوي في كل مرة بالـ getpass.
- مسار bpe file بقى configurable بدل مسار Colab الثابت
  (/usr/local/lib/python3.12/dist-packages/assets).
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .config import SegmentationConfig

log = logging.getLogger(__name__)


def get_hf_token() -> str:
    """
    بيقرأ HF_TOKEN من environment variable (اتحمّل مسبقًا من .env بواسطة python-dotenv
    في نقطة دخول السكربت). لو مش موجود، بيرجع لـ getpass كـ fallback تفاعلي.
    """
    token = os.environ.get("HF_TOKEN")
    if token:
        return token

    from getpass import getpass

    log.warning("HF_TOKEN مش موجود في .env — هيتطلب منك تدخله يدويًا.")
    return getpass("HF token: ")


def ensure_bpe_file(cfg: SegmentationConfig) -> str:
    """يحمّل ملف bpe_simple_vocab لو مش موجود، ويرجع مساره."""
    assets_dir = Path(cfg.sam3_assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    bpe_path = assets_dir / "bpe_simple_vocab_16e6.txt.gz"

    if not bpe_path.exists():
        import requests

        log.info("تحميل bpe file من %s ...", cfg.bpe_url)
        resp = requests.get(cfg.bpe_url, timeout=60)
        resp.raise_for_status()
        bpe_path.write_bytes(resp.content)

    return str(bpe_path)


def load_sam3(cfg: SegmentationConfig):
    """يحمّل موديل SAM3 والـ processor بتاعه. لازم تعمل login بـ HF token الأول."""
    from huggingface_hub import login
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    login(token=get_hf_token())

    bpe_path = ensure_bpe_file(cfg)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    sam_model = build_sam3_image_model(bpe_path)
    sam_model.to(device)
    sam_model.eval()

    return Sam3Processor(sam_model)


def segment_object(
    image: Image.Image, box: list[float], sam_processor, cfg: SegmentationConfig
) -> np.ndarray:
    """
    يرجع قناع ثنائي (numpy array) للجسم نفسه (مش الخلفية) — inverted mask زي
    النوت بوك بالظبط.
    """
    start_time = time.perf_counter()
    state = sam_processor.set_image(image)
    sam_processor.add_geometric_prompt(box=box, label=cfg.box_label, state=state)

    masks = state["masks"]  # القناع على الخلفية
    inverted_masks = ~masks  # القناع على الجسم نفسه

    if isinstance(inverted_masks, torch.Tensor):
        mask_np = inverted_masks.cpu().numpy().squeeze()
    else:
        mask_np = np.array(inverted_masks).squeeze()

    elapsed = time.perf_counter() - start_time
    print(f"[TIMING] Mask generation took {elapsed:.2f} seconds")
    log.info("[TIMING] Mask generation took %.2f seconds", elapsed)
    log.info("mask shape: %s", mask_np.shape)
    return mask_np
