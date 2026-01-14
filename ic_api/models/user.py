"""User Pydantic models."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    """Full User model."""
    id: str
    username: str
    email: EmailStr
    company_id: Optional[str] = None
    role_key: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """User creation model."""
    username: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8)
    company_id: Optional[str] = None


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """User update model."""
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role_key: Optional[str] = None
    status: Optional[str] = None


class UserResponse(BaseModel):
    """User response model (no sensitive data)."""
    id: str
    username: str
    email: EmailStr
    company_id: Optional[str] = None
    role_key: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
