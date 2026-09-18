import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from backend.app.db.base import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    type = Column(String, default="3D", nullable=False)  # "2D" or "3D"
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", nullable=True)
    file_path = Column(String, nullable=True)
    is_favorite = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    current_version = Column(Integer, default=1, nullable=True)

    owner = relationship("User", back_populates="projects")
