from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyOTPRequest, VerifyOTPResponse, ResendOTPRequest,
    LoginRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest,
    RefreshTokenRequest, GenericAuthResponse, UpdateProfileRequest, ChangePasswordRequest,
    RequestEmailChangeRequest, VerifyEmailChangeRequest
)

from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.core.security import decode_jwt_token
from app.core.exceptions import AuthException

router = APIRouter(prefix="/auth", tags=["Authentication"])
security_scheme = HTTPBearer(auto_error=False)


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
    return AuthService.update_user_profile(db, current_user.id, req.name)


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

