from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.otp import OTPVerification

class OTPRepository:
    @staticmethod
    def create(db: Session, user_id: str, code_hash: str, purpose: str, expires_minutes: int) -> OTPVerification:
        # First invalidate any active unused OTP for this user & purpose
        OTPRepository.invalidate_otps(db, user_id, purpose)
        
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        otp = OTPVerification(
            user_id=user_id,
            code_hash=code_hash,
            purpose=purpose,
            expires_at=expires_at,
            attempt_count=0,
            used=False
        )
        db.add(otp)
        db.commit()
        db.refresh(otp)
        return otp

    @staticmethod
    def get_latest_otp(db: Session, user_id: str, purpose: str) -> Optional[OTPVerification]:
        return (
            db.query(OTPVerification)
            .filter(
                OTPVerification.user_id == user_id,
                OTPVerification.purpose == purpose,
                OTPVerification.used == False
            )
            .order_by(OTPVerification.created_at.desc())
            .first()
        )

    @staticmethod
    def invalidate_otps(db: Session, user_id: str, purpose: str) -> None:
        db.query(OTPVerification).filter(
            OTPVerification.user_id == user_id,
            OTPVerification.purpose == purpose,
            OTPVerification.used == False
        ).update({"used": True}, synchronize_session=False)
        db.commit()

    @staticmethod
    def increment_attempt(db: Session, otp_id: str) -> int:
        otp = db.query(OTPVerification).filter(OTPVerification.id == otp_id).first()
        if otp:
            otp.attempt_count += 1
            db.commit()
            return otp.attempt_count
        return 0

    @staticmethod
    def mark_used(db: Session, otp_id: str) -> None:
        otp = db.query(OTPVerification).filter(OTPVerification.id == otp_id).first()
        if otp:
            otp.used = True
            db.commit()
