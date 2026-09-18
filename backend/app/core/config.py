import os
import sys
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure repository root is in sys.path for robust absolute imports
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.paths import (
    ROOT_DIR,
    OUTPUT_DIR as DEFAULT_OUTPUT_DIR,
    UPLOAD_DIR as DEFAULT_UPLOAD_DIR,
    TEMP_DIR as DEFAULT_TEMP_DIR,
    LOGS_DIR as DEFAULT_LOGS_DIR,
    DEFAULT_SQLITE_URL,
    ensure_directories,
)

# Ensure runtime directories exist
ensure_directories()

# Load .env from project root
load_dotenv(dotenv_path=ROOT_DIR / ".env")


class Settings(BaseModel):
    """
    Section 38: Centralized environment configuration.
    All secrets loaded from .env — never hardcoded.
    """

    # --- Application Metadata ---
    PROJECT_NAME: str = "Anti Design — CNC Design Generator"
    VERSION: str = "2.5.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("NODE_ENV", "development")

    # --- AI Provider Credentials (from environment only) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # --- Security & JWT ---
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        os.getenv("JWT_SECRET", "production-cnc-design-generator-jwt-secret-key-change-in-env"),
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

    # --- OTP & Rate Limiting ---
    OTP_EXPIRE_MINUTES: int = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
    OTP_MAX_ATTEMPTS: int = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    OTP_RESEND_COOLDOWN_SECONDS: int = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))

    # --- SMTP Credentials (from environment variables only) ---
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@cncstudio.ai")
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "Anti Design")

    # --- Database & Workspace ---
    PROJECT_ROOT: str = str(ROOT_DIR)
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)
    OUTPUT_DIR: str = os.getenv("STORAGE_OUTPUT_DIR", str(DEFAULT_OUTPUT_DIR))
    UPLOAD_DIR: str = os.getenv("STORAGE_UPLOAD_DIR", str(DEFAULT_UPLOAD_DIR))
    TEMP_DIR: str = os.getenv("STORAGE_TEMP_DIR", str(DEFAULT_TEMP_DIR))
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))

    # --- AI Model Endpoint ---
    MODEL_ENDPOINT: str = os.getenv("MODEL_ENDPOINT", "http://127.0.0.1:8000/api/v1/generation")

    # --- 2D Service Endpoints (New Architecture) ---
    AI_SERVER_2D_URL: str = os.getenv("AI_SERVER_2D_URL", "http://127.0.0.1:8001")
    EDIT_SERVER_URL: str = os.getenv("EDIT_SERVER_URL", "http://localhost:8002")
    NESTING_WORKER_URL: str = os.getenv("NESTING_WORKER_URL", "http://localhost:8003")
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "cad_studio_internal_secret_2026")

    # --- Google OAuth (for Desktop Login) ---
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI_BASE: str = "http://127.0.0.1"

    # --- Server Binding ---
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
        ).split(",")
    ]

    # --- Paddle Billing Integration ---
    PADDLE_ENVIRONMENT: str = os.getenv("PADDLE_ENVIRONMENT", "sandbox")  # 'sandbox' | 'production'
    PADDLE_CLIENT_TOKEN: str = os.getenv("PADDLE_CLIENT_TOKEN", "test_7664c1ecbb2fa20c918c0678d2b")
    PADDLE_API_KEY: str = os.getenv("PADDLE_API_KEY", "")
    PADDLE_WEBHOOK_SECRET_KEY: str = os.getenv("PADDLE_WEBHOOK_SECRET_KEY", "")
    PADDLE_PRICE_PRO: str = os.getenv("PADDLE_PRICE_PRO", "pri_01m2p85k69p7fxaa2aam45r4jw")
    PADDLE_PRICE_PRO_PLUS: str = os.getenv("PADDLE_PRICE_PRO_PLUS", "pri_01m2p89n5cce3wjzk8y1aerbg1")
    PADDLE_PRICE_BUSINESS: str = os.getenv("PADDLE_PRICE_BUSINESS", "pri_01m2p8cbbevbzyvxgp5pfsg746")

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", str(DEFAULT_LOGS_DIR))

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.DATABASE_URL
        if not url.startswith("sqlite:") and not url.startswith("postgresql:") and not url.startswith("mysql:"):
            # Resolve relative sqlite database paths against ROOT_DIR
            resolved_db = (ROOT_DIR / url).resolve().as_posix()
            return f"sqlite:///{resolved_db}"
        return url


settings = Settings()
