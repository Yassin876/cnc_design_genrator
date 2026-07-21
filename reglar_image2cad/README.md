# image2cad

تحويل صورة راستر (PNG/JPG/WEBP) لملف DXF قابل للاستخدام في CNC، عن طريق:

```
CLIP (تحديد الجسم) → SAM3 (segmentation) → Potrace (تحويل لمسارات متجهية) → ezdxf (تصدير DXF)
```

المشروع ده مبني من نوت بوك `image2cad_used_Potrace.ipynb` الأصلي، بس متقسّم لموديولات
عادية عشان تشتغل عليه من VS Code زي أي مشروع بايثون، مش لازم Colab أو Jupyter.

## هيكل المشروع

```
image2cad/
├── README.md
├── requirements.txt
├── .env.example          ← انسخه لـ .env وحط فيه HF_TOKEN
├── .gitignore
├── .vscode/
│   ├── launch.json        ← تشغيل الـ pipeline بـ F5 من VS Code
│   └── settings.json
├── data/
│   ├── input/              ← حط صور الإدخال هنا
│   └── output/              ← الـ DXF والـ preview بيتحفظوا هنا
├── notebooks/
│   └── image2cad_used_Potrace.ipynb   ← النسخة الأصلية، للرجوع ليها بس
├── scripts/
│   └── run_pipeline.py      ← نقطة الدخول (CLI)
├── src/image2cad/
│   ├── __init__.py
│   ├── config.py            ← كل الإعدادات (dataclasses) في مكان واحد
│   ├── detection.py         ← Cell 2: CLIP sliding-window box detection
│   ├── segmentation.py      ← Cells 3-5: تحميل SAM3 + توليد القناع
│   ├── mask_utils.py        ← Cells 6-7: bbox من القناع + صورة ثنائية للتتبع
│   ├── vectorize.py         ← Cell 9: Potrace tracing + تحويل curves لـ polylines
│   ├── kerf.py               ← Cell 10: تعويض قطر الأداة (kerf compensation)
│   ├── dxf_export.py         ← Cell 11: بناء ملف DXF فعلي
│   ├── preview.py            ← Cell 14: عرض DXF كصورة PNG للمراجعة
│   └── pipeline.py           ← الأوركستريتور اللي بيشغّل كل الخطوات مرتبة
└── tests/
    └── test_vectorize.py
```

### إيه اللي اتغيّر عن النوت بوك (غير التقسيم لملفات)؟

- **HF Token**: بدل `getpass()` في كل مرة، بقى بييجي من ملف `.env` (متغيّر `HF_TOKEN`)
  عن طريق `python-dotenv`. لو مش لاقيه هيرجع لـ `getpass` تلقائي كـ fallback.
- **مسار bpe file بتاع SAM3**: بدل المسار الثابت بتاع Colab
  (`/usr/local/lib/python3.12/dist-packages/assets`)، بقى بيتحمّل جوه المشروع نفسه
  في `assets/sam3/` أول مرة بس (مش هيعيد التحميل كل تشغيلة).
- **كل الـ params** (`machine_params`, thresholds, model names, إلخ) اتلمّت في
  `config.py` كـ dataclasses بدل ما تكون متفرقة جوه الكود.
- **الـ `!pip install`** بقت في `requirements.txt` عادي.

## التثبيت (مرة واحدة)

```bash
# 1) افتح المجلد في VS Code، وافتح Terminal (Ctrl+`)

# 2) اعمل virtual environment
python -m venv .venv
source .venv/bin/activate        # على ويندوز: .venv\Scripts\activate

# 3) ثبّت المكتبات العادية
pip install -r requirements.txt

# 4) ثبّت SAM3 من GitHub (مش على PyPI)
pip install git+https://github.com/facebookresearch/segment-anything-2.git
pip install sam3

# 5) اعمل نسخة من ملف الإعدادات وحط فيه الـ HF token بتاعك
cp .env.example .env
# افتح .env واملأ HF_TOKEN=...
```

> ملحوظة: في VS Code اضغط `Ctrl+Shift+P` → **Python: Select Interpreter** واختار
> `.venv` اللي عملته، عشان الـ imports والـ debugging يشتغلوا صح.

## التشغيل

حط صورة الإدخال في `data/input/` وبعدين:

```bash
python scripts/run_pipeline.py \
    --input data/input/th.webp \
    --output data/output/part.dxf \
    --part-width-mm 700 \
    --part-height-mm 700 \
    --tool-diameter-mm 5
```

أو من جوه VS Code: افتح `scripts/run_pipeline.py` واضغط **F5** (الإعداد جاهز في
`.vscode/launch.json`).

### أهم الـ flags

| Flag | الافتراضي | الوظيفة |
|---|---|---|
| `--input` | `data/input/th.webp` | صورة الإدخال |
| `--output` | `data/output/output_cnc.dxf` | ملف DXF الناتج |
| `--entity-type` | `lwpolyline` | `lwpolyline` (خطوط) أو `spline` (منحنى ناعم) |
| `--part-width-mm` / `--part-height-mm` | 700 / 700 | مقاس القطعة الحقيقي بالمليمتر |
| `--tool-diameter-mm` | 5.0 | قطر ريشة القطع (لحساب الـ kerf) |
| `--no-kerf` | – | يعطّل تعويض قطر الأداة |
| `--no-preview` | – | ميعملش صورة PNG للمعاينة |
| `-v` | – | تفاصيل تشغيل أكتر (debug logging) |

باقي الإعدادات الدقيقة (thresholds بتاعة CLIP، `turdsize`/`alphamax` بتاعة Potrace،
إلخ) موجودة في `src/image2cad/config.py` وتقدر تعدلها مباشرة أو تبعتها كـ overrides
لو حبيت تزود CLI flags تانية.

## اختبار سريع للجزء اللي مش محتاج GPU/موديلات

```bash
pytest tests/
```

ده بيختبر جزء الـ Potrace vectorization بس (مربع بسيط)، من غير ما يحتاج SAM3 أو CLIP،
عشان تتأكد إن التثبيت شغال قبل ما تجرب الـ pipeline كامل.
