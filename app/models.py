"""
SQLAlchemy models for the database.

Defines the tables and their structures using SQLAlchemy's
declarative base.
"""

from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, Enum, Text, BigInteger, 
    ForeignKey, DateTime, JSON, Boolean, PrimaryKeyConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    """
    SQLAlchemy model for the 'tbl_user' table.
    
    Represents a user in the system, storing credentials and metadata
    as defined in the project design.
    """
    __tablename__ = "tbl_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    
    # Using String for ENUM as discussed in the report for compatibility
    role = Column(String(10), nullable=False, default='user') 
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    images = relationship("Image", back_populates="owner")

class Tag(Base):
    """
    SQLAlchemy model for the 'tbl_tag' table.
    
    Stores the dictionary of all unique tags (user-defined, AI-generated, etc.)
    as defined in the project design.
    """
    __tablename__ = "tbl_tag"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), unique=True, nullable=False, index=True)
    
    # Using String for ENUM as discussed in the report for compatibility
    tag_type = Column(String(32), nullable=False, index=True) # 'user', 'exif_location', 'derived_time', 'ai_generated'

    # Relationship to the Image model (many-to-many)
    # 'secondary' points to the association table
    # 'back_populates' links this to the 'tags' attribute in the Image model
    images = relationship(
        "Image", 
        secondary="tbl_image_tag_link", 
        back_populates="tags"
    )

class ImageTagLink(Base):
    """
    SQLAlchemy model for the 'tbl_image_tag_link' table.
    
    This is an association table for the many-to-many relationship
    between images and tags, as defined in the project design.
    """
    __tablename__ = "tbl_image_tag_link"

    image_id = Column(BigInteger, ForeignKey("tbl_image.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tbl_tag.id", ondelete="CASCADE"), nullable=False)
    
    added_at = Column(TIMESTAMP, server_default=func.now())
    
    # Define composite primary key
    __table_args__ = (
        PrimaryKeyConstraint('image_id', 'tag_id'),
    )

class Image(Base):
    """
    SQLAlchemy model for the 'tbl_image' table.
    
    Stores all metadata for an uploaded image, including file paths,
    EXIF data, and status, as defined in the project design.
    """
    __tablename__ = "tbl_image"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Relationships
    user_id = Column(Integer, ForeignKey("tbl_user.id"), nullable=False, index=True)
    parent_image_id = Column(BigInteger, ForeignKey("tbl_image.id"), nullable=True)
    root_image_id = Column(BigInteger, nullable=True, index=True)
    
    # File Info
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False, unique=True)
    thumbnail_path = Column(String(512), nullable=True)
    mime_type = Column(String(64), nullable=False)
    file_size = Column(BigInteger, nullable=False)

    # Processing Status
    # Using String for ENUM as discussed in the report for compatibility
    status = Column(String(32), nullable=False, default='processing', index=True) # 'processing', 'active', 'archived', 'failed', 'active_deleted', 'archived_deleted'
    processing_error = Column(Text, nullable=True)
    uploaded_at = Column(TIMESTAMP, server_default=func.now(), index=True)

    # Custom Metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Derived EXIF for fast searching
    taken_at = Column(DateTime, nullable=True, index=True)
    location_name = Column(String(255), nullable=True, index=True)
    resolution_width = Column(Integer, nullable=True)
    resolution_height = Column(Integer, nullable=True)

    # Unstructured Metadata
    exif_data = Column(JSON, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    edit_history = Column(JSON, nullable=True)

    # RAG Support
    rag_indexed = Column(Boolean, nullable=False, default=False, index=True)

    # SQLAlchemy Relationships
    
    # Link back to the User model
    owner = relationship("User", back_populates="images")
    
    # Link to the Tag model (many-to-many)
    tags = relationship(
        "Tag", 
        secondary="tbl_image_tag_link", 
        back_populates="images"
    )
    
    # Self-referential relationship for edit history
    parent = relationship("Image", remote_side=[id], back_populates="children")
    children = relationship("Image", back_populates="parent")