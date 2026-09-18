from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.app.models.user import User

class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, name: str, email: str, password_hash: str, is_verified: bool = False, is_admin: bool = False) -> User:
        now = datetime.utcnow()
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_email_verified=is_verified,
            is_active=True,
            plan="free",
            requests_used_current_cycle=0,
            cycle_start_date=now,
            cycle_end_date=now + timedelta(days=30),
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


    @staticmethod
    def update_profile(db: Session, user_id: str, name: Optional[str] = None, avatar_url: Optional[str] = None) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if name is not None and name.strip():
                user.name = name.strip()
            if avatar_url is not None:
                user.avatar_url = avatar_url
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def update_email(db: Session, user_id: str, new_email: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.email = new_email.strip().lower()
            user.is_email_verified = True
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
        return user

    @staticmethod
    def update_last_login(db: Session, user_id: str) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.last_login_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def mark_email_verified(db: Session, user_id: str) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_email_verified = True
            user.updated_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def update_password(db: Session, user_id: str, new_password_hash: str) -> None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.password_hash = new_password_hash
            user.updated_at = datetime.utcnow()
            db.commit()

    @staticmethod
    def get_by_google_id(db: Session, google_id: str) -> Optional[User]:
        return db.query(User).filter(User.google_id == google_id).first()

    @staticmethod
    def create_google_user(db: Session, name: str, email: str, google_id: str) -> User:
        """Create a new user authenticated exclusively via Google OAuth."""
        now = datetime.utcnow()
        user = User(
            name=name,
            email=email,
            password_hash=None,
            google_id=google_id,
            is_email_verified=True,
            is_active=True,
            plan="free",
            requests_used_current_cycle=0,
            cycle_start_date=now,
            cycle_end_date=now + timedelta(days=30),
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


    @staticmethod
    def link_google_id(db: Session, user_id: str, google_id: str) -> None:
        """Link a Google account to an existing email/password user."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.google_id = google_id
            user.is_email_verified = True
            user.updated_at = datetime.utcnow()
            db.commit()
