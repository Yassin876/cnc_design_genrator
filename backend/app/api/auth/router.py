from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import httpx

from backend.app.db.session import get_db
from backend.app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyOTPRequest, VerifyOTPResponse, ResendOTPRequest,
    LoginRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest,
    RefreshTokenRequest, GenericAuthResponse, UpdateProfileRequest, ChangePasswordRequest,
    RequestEmailChangeRequest, VerifyEmailChangeRequest
)

from backend.app.schemas.user import UserRead
from backend.app.services.auth_service import AuthService
from backend.app.repositories.user_repository import UserRepository
from backend.app.core.security import decode_jwt_token, create_access_token, create_refresh_token
from backend.app.core.exceptions import AuthException
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)


@router.get("/status")
def auth_status():
    """Simple status check for auth service availability."""
    return {"status": "available", "service": "Anti Design Auth Service"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> UserRead:
    """
    FastAPI dependency to authenticate requests via Bearer JWT access token.
    Returns the authenticated user or raises HTTP 401.
    """
    if not credentials or not credentials.credentials:
        raise AuthException(status.HTTP_401_UNAUTHORIZED, "Authentication credentials were not provided.", "AUTH_UNAUTHORIZED")
    
    token = credentials.credentials
    try:
        payload = decode_jwt_token(token)
        if payload.get("type") != "access":
            raise AuthException(status.HTTP_401_UNAUTHORIZED, "Invalid access token type.", "AUTH_INVALID_TOKEN")
        user_id: str = payload.get("sub")
        if not user_id:
            raise AuthException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload.", "AUTH_INVALID_TOKEN")
    except AuthException:
        raise
    except Exception:
        raise AuthException(status.HTTP_401_UNAUTHORIZED, "Token expired or invalid signature.", "AUTH_TOKEN_EXPIRED")

    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise AuthException(status.HTTP_401_UNAUTHORIZED, "User account no longer exists.", "AUTH_USER_NOT_FOUND")
    
    if not user.is_active:
        raise AuthException(status.HTTP_403_FORBIDDEN, "User account is disabled.", "AUTH_ACCOUNT_DISABLED")

    return UserRead.model_validate(user)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Validates input, creates user record, hashes password, generates OTP, and dispatches verification email."
)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    return AuthService.register_user(db, req)


@router.post(
    "/register-dev",
    summary="Register and auto-verify (development only)",
    description="For development: creates user without email verification and returns tokens."
)
def register_dev(req: RegisterRequest, db: Session = Depends(get_db)):
    """Development endpoint that bypasses email verification."""
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development registration endpoint is disabled in production."
        )
    # Import AuthService to create user
    result = AuthService.register_user(db, req)
    
    # Auto-verify the user by updating is_email_verified
    user = UserRepository.get_by_email(db, req.email)
    if user:
        user.is_email_verified = True
        db.commit()
        db.refresh(user)
        
        # Generate tokens directly using correct function signatures
        access_token = create_access_token(subject=str(user.id), email=user.email)
        refresh_token = create_refresh_token(subject=str(user.id))
        
        return {
            "success": True,
            "message": "Account created and auto-verified (development mode)",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": UserRead.model_validate(user).model_dump()
        }
    
    raise HTTPException(status_code=500, detail="Failed to create user")


@router.post(
    "/verify-otp",
    response_model=VerifyOTPResponse,
    summary="Verify 6-digit OTP code",
    description="Validates OTP code for registration or password reset. On registration success, marks email verified and returns JWT tokens."
)
def verify_otp(req: VerifyOTPRequest, db: Session = Depends(get_db)):
    return AuthService.verify_otp(db, req)



@router.post(
    "/resend-otp",
    response_model=GenericAuthResponse,
    summary="Resend verification OTP email",
    description="Invalidates active OTP, generates a new 6-digit OTP code, and sends email. Enforces a 60-second cooldown rate limit."
)
def resend_otp(req: ResendOTPRequest, db: Session = Depends(get_db)):
    return AuthService.resend_otp(db, req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and obtain JWT tokens",
    description="Verifies user credentials and email verification status, updating last login timestamp."
)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    return AuthService.login_user(db, req)


@router.post(
    "/forgot-password",
    response_model=GenericAuthResponse,
    summary="Request a password reset OTP code",
    description="Sends a password reset 6-digit OTP code to the provided email address if the account exists."
)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.forgot_password(db, req)


@router.post(
    "/reset-password",
    response_model=GenericAuthResponse,
    summary="Reset password using OTP code",
    description="Validates password reset OTP code, enforces password strength rules, and updates account password."
)
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    return AuthService.reset_password(db, req)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using refresh token",
    description="Issues a new access token and refresh token pair."
)
def refresh_token(req: RefreshTokenRequest, db: Session = Depends(get_db)):
    return AuthService.refresh_access_token(db, req.refresh_token)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user profile",
    description="Returns full profile of currently logged in user based on Bearer token."
)
def get_me(current_user: UserRead = Depends(get_current_user)):
    return current_user


@router.post(
    "/logout",
    response_model=GenericAuthResponse,
    summary="Logout user session",
    description="Client clears tokens on logout."
)
def logout(current_user: UserRead = Depends(get_current_user)):
    return GenericAuthResponse(success=True, message="Successfully logged out.")


@router.put(
    "/profile",
    response_model=UserRead,
    summary="Update authenticated user profile information"
)
def update_profile(
    req: UpdateProfileRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AuthService.update_user_profile(db, current_user.id, name=req.name, avatar_url=req.avatar_url)


@router.post(
    "/change-password",
    response_model=GenericAuthResponse,
    summary="Change account password for authenticated user"
)
def change_password(
    req: ChangePasswordRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AuthService.change_password(db, current_user.id, req.current_password, req.new_password, req.confirm_password)


@router.post(
    "/request-email-change",
    response_model=GenericAuthResponse,
    summary="Initiate email change process by requesting OTP to new email address"
)
def request_email_change(
    req: RequestEmailChangeRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AuthService.request_email_change(db, current_user.id, req.current_password, str(req.new_email))


@router.post(
    "/verify-email-change",
    response_model=TokenResponse,
    summary="Verify OTP code sent to new email address and update user email in database"
)
def verify_email_change(
    req: VerifyEmailChangeRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AuthService.verify_email_change(db, current_user.id, str(req.new_email), req.otp)


# ── Google OAuth (Desktop Electron Loopback) ──────────────────────────────────

from pydantic import BaseModel as _GoogleBaseModel

class GoogleAuthCodeRequest(_GoogleBaseModel):
    code: str
    redirect_uri: str  # loopback redirect (e.g. http://127.0.0.1:{port}/callback)

@router.post(
    "/google",
    summary="Authenticate or register with Google OAuth code (Electron loopback)",
    description=(
        "Exchanges a Google OAuth2 authorization code (from the loopback redirect) for an ID token, "
        "verifies it with Google, then creates or logs in a user and returns JWT tokens."
    )
)
async def google_auth(req: GoogleAuthCodeRequest, db: Session = Depends(get_db)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        )

    # Step 1: Exchange authorization code for tokens at Google's token endpoint
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": req.code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": req.redirect_uri,
                "grant_type": "authorization_code",
            }
        )

    if token_resp.status_code != 200:
        raise HTTPException(
            status_code=400,
            detail=f"Google token exchange failed: {token_resp.text[:300]}"
        )

    token_data = token_resp.json()
    id_token_str = token_data.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="Google did not return an ID token")

    # Step 2: Verify the ID token by calling Google's tokeninfo endpoint
    async with httpx.AsyncClient(timeout=10.0) as client:
        info_resp = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token_str}
        )

    if info_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to verify Google ID token")

    google_info = info_resp.json()
    google_id = google_info.get("sub")
    email = google_info.get("email", "").lower().strip()
    name = google_info.get("name") or google_info.get("email", "User").split("@")[0]
    email_verified = google_info.get("email_verified") in [True, "true"]

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="Google token is missing required fields (sub, email)")

    if not email_verified:
        raise HTTPException(status_code=400, detail="Google account email is not verified")

    # Verify token was issued for OUR client
    if google_info.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google token audience mismatch")

    # Step 3: Find or create user
    # Priority: find by google_id first, then by email (link account)
    user = UserRepository.get_by_google_id(db, google_id)
    if not user:
        existing = UserRepository.get_by_email(db, email)
        if existing:
            # Link Google to existing account
            UserRepository.link_google_id(db, existing.id, google_id)
            user = UserRepository.get_by_id(db, existing.id)
        else:
            # Create new Google-only account
            user = UserRepository.create_google_user(db, name=name, email=email, google_id=google_id)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    UserRepository.update_last_login(db, user.id)

    # Step 4: Issue our own JWT tokens
    access_token = create_access_token(subject=str(user.id), email=user.email)
    refresh_token = create_refresh_token(subject=str(user.id))

    return {
        "success": True,
        "message": "Signed in with Google successfully.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user).model_dump()
    }
