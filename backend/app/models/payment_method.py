import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from backend.app.db.base import Base


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, default="stripe", nullable=False)  # 'stripe', 'paypal', 'instapay', etc.
    payment_token = Column(String, nullable=False, index=True)  # Secure vault token (e.g. pm_xxx, tok_xxx)
    brand = Column(String, default="visa", nullable=False)  # 'visa', 'mastercard', 'amex', etc.
    last4 = Column(String(4), nullable=False)  # Only last 4 digits stored for PCI compliance
    exp_month = Column(Integer, nullable=False)
    exp_year = Column(Integer, nullable=False)
    holder_name = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="payment_methods")
