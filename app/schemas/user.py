from typing import Optional

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    avatar: Optional[str] = None


class UserCreate(UserBase):
    auth_provider: str = "EMAIL"
    auth_provider_id: Optional[str] = None
    password: Optional[str] = None  # For email registration


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    role: Optional[str] = None


class UserOut(UserBase):
    id: str
    role: str
    auth_provider: str
    created_at: str

    class Config:
        orm_mode = True