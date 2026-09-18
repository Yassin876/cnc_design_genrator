import os

from backend.app.core.config import settings


def ensure_storage_directories() -> None:
    """Create storage/uploads, storage/outputs, and storage/temp if missing."""
    for directory in (settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR):
        os.makedirs(os.path.abspath(directory), exist_ok=True)
