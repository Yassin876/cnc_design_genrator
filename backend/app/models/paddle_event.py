import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text
from backend.app.db.base import Base


class PaddleWebhookEvent(Base):
    """
    Section: Paddle Webhook Idempotency Store.
    Ensures webhook events from Paddle are processed exactly once.
    """
    __tablename__ = "paddle_webhook_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, unique=True, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    payload = Column(Text, nullable=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
