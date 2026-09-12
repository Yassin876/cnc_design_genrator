from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, name: str, email: str, password_hash: str, is_verified: bool = False) -> User:
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            is_email_verified=is_verified,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_profile(db: Session, user_id: str, name: str) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.name = name.strip()
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
