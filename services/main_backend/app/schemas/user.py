from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserRead(BaseModel):
    id: str
    name: str
    email: EmailStr
    is_email_verified: bool
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserMinimal(BaseModel):
    id: str
    name: str
    email: str

    class Config:
        from_attributes = True
