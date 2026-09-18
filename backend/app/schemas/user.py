from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    is_email_verified: bool
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    plan: Optional[str] = "free"
    requests_used_current_cycle: Optional[int] = 0
    cycle_start_date: Optional[datetime] = None
    cycle_end_date: Optional[datetime] = None
    is_admin: Optional[bool] = False

class UserMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    plan: Optional[str] = "free"
    is_admin: Optional[bool] = False

