"""
Section 39: Structured Logging System for CNC Studio Backend

Categories:
  - request     : HTTP request / response lifecycle
  - user        : authentication, login, session
  - project     : project CRUD operations
  - job         : generation job lifecycle
  - generation  : AI pipeline stages
  - validation  : CNC manufacturing constraint checks
  - export      : CAD file export operations
  - error       : unhandled exceptions and system errors

Rules:
  - Never log secrets (API keys, JWT tokens, passwords)
  - Log structured JSON for machine-readability
  - Include request_id, timestamp, user_id where available
  - Write to both stdout and rotating file
"""

import logging
import logging.handlers
import os
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.app.core.config import settings


# ── Log Directory Bootstrap ──────────────────────────────────
os.makedirs(settings.LOG_DIR, exist_ok=True)


# ── JSON Formatter ───────────────────────────────────────────
class StructuredJsonFormatter(logging.Formatter):
    """Outputs each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "category": getattr(record, "category", "general"),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach optional structured fields
        for field in ("request_id", "user_id", "project_id", "job_id", "file_path",
                      "duration_ms", "status_code", "method", "path", "ip"):
            val = getattr(record, field, None)
            if val is not None:
                log_entry[field] = val

        if record.exc_info and record.exc_info[1]:
            import traceback
            log_entry["exception"] = str(record.exc_info[1])
            log_entry["traceback"] = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(log_entry, ensure_ascii=False)


# ── Logger Factory ───────────────────────────────────────────
_formatter = StructuredJsonFormatter()

# Console handler
_console = logging.StreamHandler()
_console.setFormatter(_formatter)

# Rotating file handler (10 MB per file, keep 5 backups)
_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(settings.LOG_DIR, "cad_studio.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(_formatter)


def get_logger(category: str = "general") -> logging.Logger:
    """
    Return a logger pre-configured with the given category tag.

    Usage:
        logger = get_logger("generation")
        logger.info("Pipeline started", extra={"job_id": job_id, "user_id": uid})
    """
    logger = logging.getLogger(f"cad_studio.{category}")

    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
        logger.addHandler(_console)
        logger.addHandler(_file_handler)
        logger.propagate = False

    # Inject category into every record automatically
    old_factory = logger.makeRecord.__func__ if hasattr(logger.makeRecord, '__func__') else None

    class _CategoryAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            kwargs.setdefault("extra", {})
            kwargs["extra"]["category"] = category
            return msg, kwargs

    return _CategoryAdapter(logger, {})


# ── Pre-built loggers for each domain ────────────────────────
request_logger   = get_logger("request")
user_logger      = get_logger("user")
project_logger   = get_logger("project")
job_logger       = get_logger("job")
generation_logger = get_logger("generation")
validation_logger = get_logger("validation")
export_logger    = get_logger("export")
error_logger     = get_logger("error")
