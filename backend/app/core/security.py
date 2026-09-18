import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from backend.app.core.config import settings

# Password hashing context using argon2 with bcrypt fallback
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash plaintext password securely using Argon2 / bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against stored hash.
    
    Returns False if hashed_password is None (Google-only account).
    This prevents verify_password(None) from raising an exception.
    """
    if hashed_password is None:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def generate_otp_code() -> str:
    """Generate a secure 6-digit numeric OTP string."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp_code(code: str) -> str:
    """
    Hash OTP code using HMAC-SHA256 with JWT_SECRET_KEY.
    Ensures OTP is never stored in plaintext in the database.
    """
    secret = settings.JWT_SECRET_KEY.encode('utf-8')
    return hmac.new(secret, code.strip().encode('utf-8'), hashlib.sha256).hexdigest()


def verify_otp_code(plain_code: str, stored_hash: str) -> bool:
    """Verify provided OTP string against stored HMAC hash using constant-time comparison."""
    computed_hash = hash_otp_code(plain_code)
    return hmac.compare_digest(computed_hash, stored_hash)


def create_access_token(subject: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": subject,
        "email": email,
        "type": "access",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT refresh token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "sub": subject,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token signature and expiration.
    Raises jwt.PyJWTError subclass on failure.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
