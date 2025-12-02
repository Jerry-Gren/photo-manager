"""
CRUD (Create, Read, Update, Delete) operations for the application.

These functions interact directly with the database session to
perform operations on the models.
"""

from sqlalchemy.orm import Session
from . import models, auth

# User CRUD Operations
def get_user_by_username(db: Session, username: str):
    """
    Retrieves a single user from the database by their username.

    Args:
        db: The database session.
        username: The username to search for.

    Returns:
        The User model instance if found, None otherwise.
    """
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a single user from the database by their email.

    Args:
        db: The database session.
        email: The email address to search for.

    Returns:
        The User model instance if found, None otherwise.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: models.User):
    """
    Adds a new user instance to the database.

    Note: This function only adds, commits, and refreshes the user model.
    Password hashing should be handled before calling this.

    Args:
        db: The database session.
        user: The SQLAlchemy User model instance (with hashed password).

    Returns:
        The User model instance after it has been added to the database
        (including the new ID).
    """
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Image CRUD Operations
def create_image_placeholder(db: Session, image: models.Image):
    """
    Creates the initial 'processing' record for an image.
    
    Args:
        db: The database session.
        image: The SQLAlchemy Image model instance (populated with file info).
        
    Returns:
        The created Image model instance.
    """
    db.add(image)
    db.commit()
    db.refresh(image)
    
    # Set root_image_id to self if it's a new upload (not an edit)
    if image.root_image_id is None:
        image.root_image_id = image.id
        db.commit()
        db.refresh(image)
        
    return image

def get_image(db: Session, image_id: int):
    """Retrieves an image by ID."""
    return db.query(models.Image).filter(models.Image.id == image_id).first()

def update_image_status(db: Session, image_id: int, status: str, error: str = None):
    """
    Updates the status of an image.
    """
    db_image = get_image(db, image_id)
    if db_image:
        db_image.status = status
        if error:
            db_image.processing_error = error
        db.commit()
        db.refresh(db_image)
    return db_image