"""
SQLAlchemy models for the database.

Defines the tables and their structures using SQLAlchemy's
declarative base.
"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, Enum
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
