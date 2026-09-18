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


def safe_resolve_storage_path(target_path: str, base_dir: Path | str = STORAGE_DIR) -> str | None:
    """Safely resolves target_path (whether absolute or relative) against STORAGE_DIR/ROOT_DIR
    regardless of the process current working directory (CWD).
    
    Returns the canonical absolute path if it is strictly within base_dir, else None.
    """
    if not target_path or not isinstance(target_path, str):
        return None
    try:
        base_abs = os.path.abspath(str(base_dir))
        root_abs = os.path.abspath(str(ROOT_DIR))
        
        if os.path.isabs(target_path):
            candidate = os.path.abspath(target_path)
        else:
            # If path starts with storage/ or relative to project root
            cand_root = os.path.abspath(os.path.join(root_abs, target_path))
            if os.path.commonpath([cand_root, base_abs]) == base_abs and os.path.exists(cand_root):
                candidate = cand_root
            else:
                # Resolve relative to base_dir
                candidate = os.path.abspath(os.path.join(base_abs, target_path))
                
        if os.path.commonpath([candidate, base_abs]) == base_abs:
            return candidate
        return None
    except (ValueError, OSError):
        return None


def is_safe_storage_path(target_path: str, base_dir: Path | str = STORAGE_DIR) -> bool:
    """Returns True if target_path is strictly contained within base_dir."""
    return safe_resolve_storage_path(target_path, base_dir) is not None


def ensure_directories() -> None:
    """Ensure essential runtime storage and log directories exist."""
    for directory in [STORAGE_DIR, OUTPUT_DIR, UPLOAD_DIR, TEMP_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize essential directories on import
ensure_directories()

