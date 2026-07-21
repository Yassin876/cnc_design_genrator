#!/usr/bin/env python3
"""
نقطة الدخول لتشغيل الـ pipeline من التيرمينال بدل النوت بوك.

استخدام:
    python scripts/run_pipeline.py --input data/input/th.webp --output data/output/part.dxf

اعمل .env في روت المشروع (انسخ من .env.example) وحط فيه HF_TOKEN بتاعك.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# يسمح بعمل import لـ image2cad من src/ من غير ما تعمل pip install -e .
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Mock Triton for Windows / non-Triton systems before importing image2cad/sam3
try:
    import triton
except ImportError:
    from types import ModuleType
    import importlib.machinery

    class MockClass:
        def __init__(self, *args, **kwargs):
            pass
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return MockClass()
        def __call__(self, *args, **kwargs):
            return MockClass()

    class MockLanguage(ModuleType):
        constexpr = object
        dtype = object
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return MockClass()
        def program_id(self, *args, **kwargs): return 0
        def load(self, *args, **kwargs): return 0
        def store(self, *args, **kwargs): pass
        def arange(self, *args, **kwargs): return []
        def where(self, *args, **kwargs): return 0
        def minimum(self, *args, **kwargs): return 0
        def atomic_min(self, *args, **kwargs): return 0
        def atomic_add(self, *args, **kwargs): return 0
        def ravel(self, *args, **kwargs): return []
        def debug_barrier(self, *args, **kwargs): pass
        def reduce(self, *args, **kwargs): return 0

    class MockTriton(ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return MockClass()
        def jit(self, *args, **kwargs):
            if len(args) == 1 and callable(args[0]):
                return args[0]
            return lambda f: f
        def autotune(self, *args, **kwargs):
            return lambda f: f
        def Config(self, *args, **kwargs):
            return object()
        def cdiv(self, a, b):
            return (a + b - 1) // b

    class TritonMockLoader:
        def create_module(self, spec):
            fullname = spec.name
            if fullname == "triton":
                m = MockTriton(fullname)
            elif fullname == "triton.language":
                m = MockLanguage(fullname)
            else:
                m = ModuleType(fullname)
                def safe_getattr(name):
                    if name.startswith("__"):
                        raise AttributeError(name)
                    return MockClass()
                m.__getattr__ = safe_getattr
            m.__path__ = []
            m.__spec__ = spec
            return m

        def exec_module(self, module):
            if module.__name__ == "triton":
                module.language = sys.modules.get("triton.language")

    class TritonMockFinder:
        def find_spec(self, fullname, path, target=None):
            if fullname == "triton" or fullname.startswith("triton."):
                return importlib.machinery.ModuleSpec(
                    name=fullname,
                    loader=TritonMockLoader(),
                    is_package=True
                )
            return None

    sys.meta_path.insert(0, TritonMockFinder())

    # Pre-populate basic imports to trigger the loader early
    import importlib
    try:
        importlib.import_module("triton")
        importlib.import_module("triton.language")
    except Exception:
        pass

    # Patch find_spec for transformers checks
    import importlib.util
    orig = importlib.util.find_spec
    importlib.util.find_spec = lambda name, pkg=None: None if name in (
        'triton', 'triton.language', 'triton.backends', 'triton.backends.compiler', 'triton.compiler'
    ) else orig(name, pkg)

from dotenv import load_dotenv  # noqa: E402

from image2cad.config import PipelineConfig  # noqa: E402
from image2cad.pipeline import run  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Image -> DXF vectorization pipeline")
    p.add_argument("--input", type=Path, default=Path("data/input/th.webp"), help="مسار صورة الإدخال")
    p.add_argument("--output", type=Path, default=Path("data/output/output_cnc.dxf"), help="مسار ملف DXF الناتج")
    p.add_argument("--preview", type=Path, default=Path("data/output/dxf_preview.png"), help="مسار صورة المعاينة")
    p.add_argument("--entity-type", choices=["lwpolyline", "spline"], default="lwpolyline")
    p.add_argument("--part-width-mm", type=float, default=700.0)
    p.add_argument("--part-height-mm", type=float, default=700.0)
    p.add_argument("--tool-diameter-mm", type=float, default=5.0)
    p.add_argument("--no-kerf", action="store_true", help="عطّل تعويض قطر الأداة")
    p.add_argument("--no-preview", action="store_true", help="متعملش صورة معاينة PNG")
    p.add_argument("--prompt", type=str, default=None, help="الـ prompt الأساسي للكشف (مثل tree أو plane)")
    p.add_argument("--score-threshold", type=float, default=None, help="الحد الأدنى لدرجة مطابقة الكشف (مثلاً 0.2)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    load_dotenv()  # بيقرأ ملف .env ويحط HF_TOKEN وغيره في environment variables

    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    cfg = PipelineConfig(
        input_image=args.input,
        output_dxf=args.output,
        output_preview=args.preview,
        entity_type=args.entity_type,
    )
    cfg.machine.part_width_mm = args.part_width_mm
    cfg.machine.part_height_mm = args.part_height_mm
    cfg.machine.tool_diameter_mm = args.tool_diameter_mm
    cfg.kerf.apply_kerf = not args.no_kerf
    if args.prompt:
        cfg.detection.prompts = [args.prompt] + cfg.detection.prompts[1:]
    if args.score_threshold is not None:
        cfg.detection.score_threshold = args.score_threshold

    run(cfg, skip_preview=args.no_preview)


if __name__ == "__main__":
    main()
