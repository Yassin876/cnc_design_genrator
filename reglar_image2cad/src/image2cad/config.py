"""
كل الإعدادات القابلة للتعديل في مكان واحد بدل ما تكون متفرقة في خلايا النوت بوك.
عدّل هنا (أو مرّر overrides من CLI) بدل ما تدور جوه الكود.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectionConfig:
    """Cell 2: CLIP sliding-window box detection."""
    clip_model_name: str = "openai/clip-vit-base-patch32"
    prompts: list[str] = field(default_factory=lambda: [
        "plane", "random object", "metal machine", "human face",
    ])
    patch_size: int = 128
    stride: int = 64
    score_threshold: float = 0.3


@dataclass
class SegmentationConfig:
    """Cells 3-5: SAM3 model + mask generation."""
    sam3_assets_dir: str = "assets/sam3"  # فين هيتحط bpe file لوكل بدل مسار Colab الثابت
    bpe_url: str = "https://github.com/openai/CLIP/raw/main/clip/bpe_simple_vocab_16e6.txt.gz"
    box_label: int = 2  # 2 = box prompt في SAM3


@dataclass
class MaskConfig:
    """Cells 6-7: bbox من القناع + بناء صورة ثنائية للتتبع."""
    bbox_pad_px: int = 10
    use_otsu: bool = True
    manual_thresh: int | None = None


@dataclass
class VectorizeConfig:
    """Cell 9: Potrace tracing."""
    turdsize: int = 2
    alphamax: float = 1.0
    opticurve: bool = True
    opttolerance: float = 0.2
    bezier_steps: int = 12


@dataclass
class KerfConfig:
    """Cell 10: تعويض قطر الأداة."""
    apply_kerf: bool = True
    is_internal: bool = True


@dataclass
class MachineConfig:
    """Cell 12: machine_params."""
    part_width_mm: float = 700.0
    part_height_mm: float = 700.0
    tool_diameter_mm: float = 5.0
    sheet_width_mm: float = 1000.0
    sheet_height_mm: float = 1000.0
    margin_mm: float = 10.0


@dataclass
class PipelineConfig:
    input_image: Path = Path("data/input/th.webp")
    output_dxf: Path = Path("data/output/output_cnc.dxf")
    output_preview: Path = Path("data/output/dxf_preview.png")
    entity_type: str = "lwpolyline"  # "lwpolyline" أو "spline"

    detection: DetectionConfig = field(default_factory=DetectionConfig)
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    mask: MaskConfig = field(default_factory=MaskConfig)
    vectorize: VectorizeConfig = field(default_factory=VectorizeConfig)
    kerf: KerfConfig = field(default_factory=KerfConfig)
    machine: MachineConfig = field(default_factory=MachineConfig)
