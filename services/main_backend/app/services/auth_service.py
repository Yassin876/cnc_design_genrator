from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import (
    hash_password, verify_password, generate_otp_code, hash_otp_code, verify_otp_code,
    create_access_token, create_refresh_token, decode_jwt_token
)
from app.core.mail import send_otp_email
from app.core.exceptions import AuthException
from app.utils.validators import normalize_email, validate_password_strength
from app.repositories.user_repository import UserRepository
from app.repositories.otp_repository import OTPRepository
from app.schemas.auth import (
    RegisterRequest, RegisterResponse, VerifyOTPRequest, ResendOTPRequest,
    LoginRequest, TokenResponse, ForgotPasswordRequest, ResetPasswordRequest, GenericAuthResponse
)
from app.schemas.user import UserRead


class AuthService:
    @staticmethod
    def register_user(db: Session, req: RegisterRequest) -> RegisterResponse:
        if req.confirm_password and req.password != req.confirm_password:
            raise AuthException(400, "Passwords do not match", "AUTH_PASSWORDS_DO_NOT_MATCH")

        email = normalize_email(req.email)
        
        is_valid_pwd, pwd_error = validate_password_strength(req.password)
        if not is_valid_pwd:
            raise AuthException(400, pwd_error, "AUTH_WEAK_PASSWORD")

        existing_user = UserRepository.get_by_email(db, email)
        if existing_user:
            if existing_user.is_email_verified:
                raise AuthException(400, "An account with this email address already exists.", "AUTH_USER_EXISTS")
            # If user exists but is unverified, update password & resend OTP
            pwd_hash = hash_password(req.password)
            UserRepository.update_password(db, existing_user.id, pwd_hash)
            user = existing_user
        else:
            pwd_hash = hash_password(req.password)
            user = UserRepository.create(db, name=req.name.strip(), email=email, password_hash=pwd_hash)

        # Generate OTP
        otp_code = generate_otp_code()
        code_hash = hash_otp_code(otp_code)
        OTPRepository.create(db, user_id=user.id, code_hash=code_hash, purpose="registration", expires_minutes=settings.OTP_EXPIRE_MINUTES)

        # Send Email
        send_otp_email(recipient_email=email, recipient_name=user.name, otp_code=otp_code, purpose="registration")

        return RegisterResponse(
            success=True,
            message="Account created successfully. Please enter the verification code sent to your email.",
            email=email,
            require_verification=True
        )

    @staticmethod
    def verify_otp(db: Session, req: VerifyOTPRequest):
        email = normalize_email(req.email)
        user = UserRepository.get_by_email(db, email)
        if not user:
            raise AuthException(404, "User account not found.", "AUTH_USER_NOT_FOUND")

        otp = OTPRepository.get_latest_otp(db, user.id, req.purpose)
        if not otp:
            raise AuthException(400, "No active verification code found for this account.", "AUTH_INVALID_OTP")

        if otp.expires_at < datetime.utcnow():
            raise AuthException(400, "Verification code has expired. Please request a new code.", "AUTH_OTP_EXPIRED")

        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            raise AuthException(400, "Maximum verification attempts exceeded. Please request a new code.", "AUTH_OTP_ATTEMPTS_EXCEEDED")

        if not verify_otp_code(req.otp, otp.code_hash):
            OTPRepository.increment_attempt(db, otp.id)
            remaining = settings.OTP_MAX_ATTEMPTS - (otp.attempt_count + 1)
            raise AuthException(400, f"Invalid verification code. {remaining} attempts remaining.", "AUTH_INVALID_OTP")

        # Code is valid! Mark as used
        OTPRepository.mark_used(db, otp.id)

        if req.purpose == "registration":
            UserRepository.mark_email_verified(db, user.id)
            user.is_email_verified = True
            UserRepository.update_last_login(db, user.id)

            access_token = create_access_token(subject=user.id, email=user.email)
            refresh_token = create_refresh_token(subject=user.id)

            return TokenResponse(
                success=True,
                message="Email verified successfully! Welcome to CNC Design Generator.",
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                user=UserRead.model_validate(user)
            )

        elif req.purpose == "password_reset":
            return GenericAuthResponse(
                success=True,
                message="Verification code validated. You may now reset your password."
            )
        else:
            raise AuthException(400, "Invalid verification purpose.", "AUTH_INVALID_OTP")

    @staticmethod
    def resend_otp(db: Session, req: ResendOTPRequest) -> GenericAuthResponse:
        email = normalize_email(req.email)
        user = UserRepository.get_by_email(db, email)
        if not user:
            # Return success safely to prevent account enumeration
            return GenericAuthResponse(
                success=True,
                message="If an account exists with that email, a new verification code has been sent."
            )

        latest_otp = OTPRepository.get_latest_otp(db, user.id, req.purpose)
        if latest_otp:
            time_since_created = (datetime.utcnow() - latest_otp.created_at).total_seconds()
            if time_since_created < settings.OTP_RESEND_COOLDOWN_SECONDS:
                cooldown_left = int(settings.OTP_RESEND_COOLDOWN_SECONDS - time_since_created)
                raise AuthException(429, f"Please wait {cooldown_left} seconds before requesting another code.", "AUTH_OTP_COOLDOWN")

        # Generate & send new OTP
        otp_code = generate_otp_code()
        code_hash = hash_otp_code(otp_code)
        OTPRepository.create(db, user_id=user.id, code_hash=code_hash, purpose=req.purpose, expires_minutes=settings.OTP_EXPIRE_MINUTES)
        send_otp_email(recipient_email=email, recipient_name=user.name, otp_code=otp_code, purpose=req.purpose)

        return GenericAuthResponse(
            success=True,
            message="A new verification code has been sent to your email."
        )

    @staticmethod
    def login_user(db: Session, req: LoginRequest) -> TokenResponse:
        email = normalize_email(req.email)
        user = UserRepository.get_by_email(db, email)
        if not user or not verify_password(req.password, user.password_hash):
            raise AuthException(401, "Invalid email address or password.", "AUTH_INVALID_CREDENTIALS")

        if not user.is_active:
            raise AuthException(403, "Account is disabled. Please contact support.", "AUTH_ACCOUNT_DISABLED")

        if not user.is_email_verified:
            # Resend OTP if email is unverified
            otp_code = generate_otp_code()
            code_hash = hash_otp_code(otp_code)
            OTPRepository.create(db, user_id=user.id, code_hash=code_hash, purpose="registration", expires_minutes=settings.OTP_EXPIRE_MINUTES)
            send_otp_email(recipient_email=email, recipient_name=user.name, otp_code=otp_code, purpose="registration")
            raise AuthException(403, "Your email address is not verified. A new verification code has been sent to your email.", "AUTH_UNVERIFIED_EMAIL")

        UserRepository.update_last_login(db, user.id)
        user.last_login_at = datetime.utcnow()

        access_token = create_access_token(subject=user.id, email=user.email)
        refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            success=True,
            message="Login successful.",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserRead.model_validate(user)
        )

    @staticmethod
    def forgot_password(db: Session, req: ForgotPasswordRequest) -> GenericAuthResponse:
        email = normalize_email(req.email)
        user = UserRepository.get_by_email(db, email)
        if user and user.is_active:
            # Check cooldown
            latest_otp = OTPRepository.get_latest_otp(db, user.id, "password_reset")
            if latest_otp:
                time_since = (datetime.utcnow() - latest_otp.created_at).total_seconds()
                if time_since < settings.OTP_RESEND_COOLDOWN_SECONDS:
                    cooldown_left = int(settings.OTP_RESEND_COOLDOWN_SECONDS - time_since)
                    raise AuthException(429, f"Please wait {cooldown_left} seconds before requesting a reset code.", "AUTH_OTP_COOLDOWN")

            otp_code = generate_otp_code()
            code_hash = hash_otp_code(otp_code)
            OTPRepository.create(db, user_id=user.id, code_hash=code_hash, purpose="password_reset", expires_minutes=settings.OTP_EXPIRE_MINUTES)
            send_otp_email(recipient_email=email, recipient_name=user.name, otp_code=otp_code, purpose="password_reset")

        return GenericAuthResponse(
            success=True,
            message="If an account exists with that email address, password reset instructions have been sent."
        )

    @staticmethod
    def reset_password(db: Session, req: ResetPasswordRequest) -> GenericAuthResponse:
        if req.confirm_password and req.new_password != req.confirm_password:
            raise AuthException(400, "Passwords do not match", "AUTH_PASSWORDS_DO_NOT_MATCH")

        is_valid_pwd, pwd_error = validate_password_strength(req.new_password)
        if not is_valid_pwd:
            raise AuthException(400, pwd_error, "AUTH_WEAK_PASSWORD")

        email = normalize_email(req.email)
        user = UserRepository.get_by_email(db, email)
        if not user:
            raise AuthException(404, "User account not found.", "AUTH_USER_NOT_FOUND")

        otp = OTPRepository.get_latest_otp(db, user.id, "password_reset")
        if not otp:
            raise AuthException(400, "No active password reset request found for this email.", "AUTH_INVALID_OTP")

        if otp.expires_at < datetime.utcnow():
            raise AuthException(400, "Password reset code has expired. Please request a new one.", "AUTH_OTP_EXPIRED")

        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            raise AuthException(400, "Maximum verification attempts exceeded. Please request a new reset code.", "AUTH_OTP_ATTEMPTS_EXCEEDED")

        if not verify_otp_code(req.otp, otp.code_hash):
            OTPRepository.increment_attempt(db, otp.id)
            remaining = settings.OTP_MAX_ATTEMPTS - (otp.attempt_count + 1)
            raise AuthException(400, f"Invalid reset code. {remaining} attempts remaining.", "AUTH_INVALID_OTP")

        # Mark OTP used and update user password
        OTPRepository.mark_used(db, otp.id)
        new_hash = hash_password(req.new_password)
        UserRepository.update_password(db, user.id, new_hash)

        return GenericAuthResponse(
            success=True,
            message="Password reset successfully. You can now log in with your new password."
        )

    @staticmethod
    def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_jwt_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthException(401, "Invalid refresh token", "AUTH_INVALID_TOKEN")
            user_id = payload.get("sub")
        except Exception:
            raise AuthException(401, "Expired or invalid refresh token", "AUTH_INVALID_TOKEN")

        user = UserRepository.get_by_id(db, user_id)
        if not user or not user.is_active:
            raise AuthException(401, "User not found or inactive", "AUTH_USER_NOT_FOUND")

        new_access_token = create_access_token(subject=user.id, email=user.email)
        new_refresh_token = create_refresh_token(subject=user.id)

        return TokenResponse(
            success=True,
            message="Access token refreshed successfully.",
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            user=UserRead.model_validate(user)
        )

    @staticmethod
    def update_user_profile(db: Session, user_id: str, name: str) -> UserRead:
        user = UserRepository.update_profile(db, user_id, name)
        if not user:
            raise AuthException(404, "User not found", "AUTH_USER_NOT_FOUND")
        return UserRead.model_validate(user)

    @staticmethod
    def change_password(db: Session, user_id: str, current_password: str, new_password: str, confirm_password: str = None) -> GenericAuthResponse:
        if confirm_password and new_password != confirm_password:
            raise AuthException(400, "Passwords do not match", "AUTH_PASSWORDS_DO_NOT_MATCH")

        user = UserRepository.get_by_id(db, user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise AuthException(400, "Current password is incorrect.", "AUTH_INVALID_CREDENTIALS")

        is_valid_pwd, pwd_error = validate_password_strength(new_password)
        if not is_valid_pwd:
            raise AuthException(400, pwd_error, "AUTH_WEAK_PASSWORD")

        new_hash = hash_password(new_password)
        UserRepository.update_password(db, user.id, new_hash)
        return GenericAuthResponse(success=True, message="Password updated successfully.")

    @staticmethod
    def request_email_change(db: Session, user_id: str, current_password: str, new_email: str) -> GenericAuthResponse:
        user = UserRepository.get_by_id(db, user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise AuthException(400, "Current password is incorrect.", "AUTH_INVALID_CREDENTIALS")

        new_email = normalize_email(new_email)
        if new_email == user.email:
            raise AuthException(400, "New email address must be different from current email.", "AUTH_SAME_EMAIL")

        existing_user = UserRepository.get_by_email(db, new_email)
        if existing_user and existing_user.is_email_verified:
            raise AuthException(400, "An account with this email address already exists.", "AUTH_USER_EXISTS")

        purpose = f"email_change:{new_email}"
        otp_code = generate_otp_code()
        code_hash = hash_otp_code(otp_code)

        OTPRepository.create(db, user_id=user.id, code_hash=code_hash, purpose=purpose, expires_minutes=settings.OTP_EXPIRE_MINUTES)
        send_otp_email(recipient_email=new_email, recipient_name=user.name, otp_code=otp_code, purpose="email_change")

        return GenericAuthResponse(
            success=True,
            message=f"Verification code sent to {new_email}. Please enter the code to confirm email change."
        )

    @staticmethod
    def verify_email_change(db: Session, user_id: str, new_email: str, otp_code: str) -> TokenResponse:
        new_email = normalize_email(new_email)
        purpose = f"email_change:{new_email}"

        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise AuthException(404, "User account not found.", "AUTH_USER_NOT_FOUND")

        otp = OTPRepository.get_latest_otp(db, user.id, purpose)
        if not otp:
            raise AuthException(400, "No active email change request found.", "AUTH_INVALID_OTP")

        if otp.expires_at < datetime.utcnow():
            raise AuthException(400, "Verification code has expired. Please request a new email change.", "AUTH_OTP_EXPIRED")

        if otp.attempt_count >= settings.OTP_MAX_ATTEMPTS:
            raise AuthException(400, "Maximum verification attempts exceeded.", "AUTH_OTP_ATTEMPTS_EXCEEDED")

        if not verify_otp_code(otp_code, otp.code_hash):
            OTPRepository.increment_attempt(db, otp.id)
            remaining = settings.OTP_MAX_ATTEMPTS - (otp.attempt_count + 1)
            raise AuthException(400, f"Invalid verification code. {remaining} attempts remaining.", "AUTH_INVALID_OTP")

        OTPRepository.mark_used(db, otp.id)

        # Safely update email in DB
        updated_user = UserRepository.update_email(db, user_id, new_email)

        # Issue new JWT tokens for updated user session
        access_token = create_access_token(subject=updated_user.id, email=updated_user.email)
        refresh_token = create_refresh_token(subject=updated_user.id)

        return TokenResponse(
            success=True,
            message="Email updated and verified successfully!",
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserRead.model_validate(updated_user)
        )

