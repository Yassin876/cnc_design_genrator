import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)  # nullable for Google-only accounts
    google_id = Column(String, unique=True, nullable=True, index=True)  # Google OAuth sub
    avatar_url = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)

    # Subscription & Billing fields (Stored in DB as source of truth)
    plan = Column(String, default="free", nullable=False)  # 'free', 'pro', 'pro_plus', 'business'
    requests_used_current_cycle = Column(Integer, default=0, nullable=False)
    cycle_start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    cycle_end_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=30), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Paddle Billing Integration fields
    paddle_customer_id = Column(String, nullable=True, index=True)
    paddle_subscription_id = Column(String, nullable=True, index=True)
    subscription_status = Column(String, default="active", nullable=False)  # 'active', 'trialing', 'past_due', 'canceled', 'paused'
    next_billing_date = Column(DateTime, nullable=True)
    cancel_url = Column(String, nullable=True)
    update_url = Column(String, nullable=True)

    otps = relationship("OTPVerification", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    payment_methods = relationship("PaymentMethod", back_populates="user", cascade="all, delete-orphan")
