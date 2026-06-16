import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str = "employee"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}