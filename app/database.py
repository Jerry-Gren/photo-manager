"""
Database configuration and session management for SQLAlchemy.

This module sets up the database engine, the session factory,
and provides a dependency for yielding database sessions in
FastAPI endpoints.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get DATABASE_URL from environment variable
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
# 'pool_pre_ping=True' checks for stale connections
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_pre_ping=True
)

# Each SessionLocal instance will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models
Base = declarative_base()

# Dependency to get a DB session
def get_db():
    """
    FastAPI dependency to get a database session.

    Yields a SQLAlchemy session and ensures it is closed
    after the request is finished, even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
