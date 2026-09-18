import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String, nullable=True)
    user_email = Column(String, nullable=True)
    plan_requested = Column(String, nullable=False)  # 'pro', 'pro_plus', 'business'
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    method = Column(String, nullable=False)  # 'cash', 'instapay'
    proof_reference = Column(String, nullable=True)
    proof_image_path = Column(String, nullable=True)
    status = Column(String, default="pending_approval", nullable=False)  # 'pending_approval', 'approved', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    admin_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="payments")
