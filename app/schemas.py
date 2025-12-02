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

# Tag Schemas
class TagBase(BaseModel):
    name: str

class TagCreate(TagBase):
    """Schema for creating a user-defined tag."""
    pass

class Tag(TagBase):
    """Schema for reading a tag."""
    id: int
    tag_type: str # 'user', 'derived_time', 'ai_generated', etc.

    class Config:
        from_attributes = True

# Image Schemas
class ImageBase(BaseModel):
    """Base Pydantic schema for image properties."""
    title: str | None = None
    description: str | None = None

class ImageCreate(ImageBase):
    """Schema for creating an image (metadata only, file handled separately)."""
    pass

class Image(ImageBase):
    """
    Pydantic schema for reading image data (API response).
    Includes fields that might be populated asynchronously.
    """
    id: int
    user_id: int
    parent_image_id: int | None = None
    root_image_id: int | None = None
    
    # File Info
    original_filename: str
    mime_type: str
    file_size: int
    
    # Status
    status: str  # 'processing', 'active', etc.
    processing_error: str | None = None
    uploaded_at: datetime
    
    # Derived Info
    taken_at: datetime | None = None
    location_name: str | None = None
    resolution_width: int | None = None
    resolution_height: int | None = None
    
    # Flags
    rag_indexed: bool

    # Tags
    tags: list[Tag] = []

    class Config:
        from_attributes = True