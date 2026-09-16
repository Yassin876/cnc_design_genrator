"""
Centralized Paths Configuration for CNC Design Generator / Anti Design.
Ensures unified absolute paths regardless of current working directory or execution context.
"""
from pathlib import Path
import os

# Root directory of the repository (d:/cnc_design_genrator)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Storage and runtime directories
STORAGE_DIR = ROOT_DIR / "storage"
OUTPUT_DIR = STORAGE_DIR / "outputs"
UPLOAD_DIR = STORAGE_DIR / "uploads"
TEMP_DIR = STORAGE_DIR / "temp"
LOGS_DIR = ROOT_DIR / "logs"

# Database path (always absolute)
DEFAULT_DB_FILE = ROOT_DIR / "cad_studio.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DEFAULT_DB_FILE.as_posix()}"


def ensure_directories() -> None:
    """Ensure essential runtime storage and log directories exist."""
    for directory in [STORAGE_DIR, OUTPUT_DIR, UPLOAD_DIR, TEMP_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize essential directories on import
ensure_directories()
