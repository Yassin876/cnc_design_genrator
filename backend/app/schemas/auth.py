from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from backend.app.schemas.user import UserRead

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None

class RegisterResponse(BaseModel):
    success: bool = True
    message: str
    email: str
    require_verification: bool = True

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    purpose: str = "registration"  # "registration", "password_reset", or "email_change"

class VerifyOTPResponse(BaseModel):
    success: bool = True
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    user: Optional[UserRead] = None

class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "registration"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    success: bool = True
    message: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    avatar_url: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: Optional[str] = None

class RequestEmailChangeRequest(BaseModel):
    current_password: str
    new_email: EmailStr

class VerifyEmailChangeRequest(BaseModel):
    new_email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class GenericAuthResponse(BaseModel):
    success: bool = True
    message: str

class APIErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: str
