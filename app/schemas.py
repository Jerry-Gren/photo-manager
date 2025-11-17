"""
Pydantic schemas for data validation and serialization.

These models define the shape of data for API requests (input)
and responses (output).
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    """Base Pydantic schema for user properties."""
    username: str = Field(..., min_length=6)
    email: EmailStr

class UserCreate(UserBase):
    """Pydantic schema for user creation (registration)."""
    password: str = Field(..., min_length=6)

class User(UserBase):
    """
    Pydantic schema for reading user data (API response).
    Excludes sensitive information like the password hash.
    """
    id: int
    role: str
    created_at: datetime

    # This allows SQLAlchemy models to be converted to Pydantic schemas
    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    """Pydantic schema for the JWT access token response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Pydantic schema for the data stored in the JWT payload."""
    sub: str | None = None
