import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env from main_backend or project root
_main_backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
_root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

if os.path.exists(_main_backend_env):
    load_dotenv(dotenv_path=_main_backend_env)
else:
    load_dotenv(dotenv_path=_root_env)



class Settings(BaseModel):
    """
    Section 38: Centralized environment configuration.
    All secrets loaded from .env — never hardcoded.
    """

    # --- Application Metadata ---
    PROJECT_NAME: str = "CNC Studio AI — CAD Engineering Suite"
    VERSION: str = "2.5.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = os.getenv("NODE_ENV", "development")

    # --- AI Provider Credentials (from environment only) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # --- Security & JWT ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", os.getenv("JWT_SECRET", "production-cnc-design-generator-jwt-secret-key-change-in-env"))
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
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "CNC Design Generator")

    # --- Database & Workspace ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cad_studio.db")
    OUTPUT_DIR: str = os.getenv("STORAGE_OUTPUT_DIR", "outputs")
    UPLOAD_DIR: str = os.getenv("STORAGE_UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(50 * 1024 * 1024)))

    # --- AI Model Endpoint ---
    MODEL_ENDPOINT: str = os.getenv("MODEL_ENDPOINT", "http://127.0.0.1:8000/api/v1/generation")

    # --- Server Binding ---
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # --- CORS ---
    BACKEND_CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    ]

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.DATABASE_URL
        if not url.startswith("sqlite:") and not url.startswith("postgresql:") and not url.startswith("mysql:"):
            return f"sqlite:///./{url}"
        return url


settings = Settings()

