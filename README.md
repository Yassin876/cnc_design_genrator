# Capstone Project

هذا المشروع عبارة عن تطبيق بايثون للمعالجة والتوليد في مجال CAD، مع بنية تحتوي على ملفات مصدر وأدوات تحليل.

## هيكل المشروع

- `main_app_new.py` - نقطة الدخول الرئيسية للتطبيق.
- `core/` - يحتوي على منطق التطبيق الأساسي مثل `ai_generator`, `database`, `dxf_editor`, و `pipeline_manager`.
- `assets/` - موارد المشروع.
- `outputs/` - مخرجات المشروع.
- `uploads/` - الملفات المرفوعة / المدخلة.
- `env/` - بيئة بايثون الافتراضية.

## المتطلبات

- Python 3.x
- الحزم الموجودة في `requirements.txt`

## التثبيت

```bash
python -m pip install -r requirements.txt
```

## التشغيل

```bash
python main_app_new.py
```

## ملاحظات

- تأكد من تفعيل البيئة الافتراضية قبل التشغيل.
- يمكن تحديث `.gitignore` حسب احتياجات المشروع الخاصة بك.
