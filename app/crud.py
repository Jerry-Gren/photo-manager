"""
CRUD (Create, Read, Update, Delete) operations for the application.

These functions interact directly with the database session to
perform operations on the models.
"""

from sqlalchemy.orm import Session, defer
from sqlalchemy import func
from datetime import datetime
from . import models

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
    """Updates the status of an image."""
    db_image = get_image(db, image_id)
    if db_image:
        db_image.status = status
        if error:
            db_image.processing_error = error
        db.commit()
        db.refresh(db_image)
    return db_image

# Tag CRUD
def get_tag_by_name(db: Session, name: str):
    return db.query(models.Tag).filter(models.Tag.name == name).first()

def get_or_create_tag(db: Session, name: str, tag_type: str = "user"):
    """Implements 'Get or Create' logic for tags."""
    tag = get_tag_by_name(db, name)
    if not tag:
        tag = models.Tag(name=name, tag_type=tag_type)
        db.add(tag)
        db.commit()
        db.refresh(tag)
    return tag

def add_tag_to_image(db: Session, image_id: int, tag_name: str, tag_type: str = "user"):
    """Links a tag to an image. Creates the tag if it doesn't exist."""
    image = get_image(db, image_id)
    if not image:
        return None
    
    tag = get_or_create_tag(db, name=tag_name, tag_type=tag_type)
    
    # Check if link already exists to avoid duplicates
    if tag not in image.tags:
        image.tags.append(tag)
        db.commit()
        db.refresh(image)
    return image

def remove_tag_from_image(db: Session, image_id: int, tag_id: int):
    """Removes a tag link from an image."""
    image = get_image(db, image_id)
    if image:
        tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
        if tag and tag in image.tags:
            image.tags.remove(tag)
            db.commit()
            db.refresh(image)
    return image

def get_all_tags(db: Session):
    """
    [DEPRECATED] Returns all tags.
    WARNING: Potential privacy leak in multi-user environments.
    Use get_tags_by_user instead.
    """
    return db.query(models.Tag).all()

def get_tags_by_user(db: Session, user_id: int):
    """
    Returns only tags that are associated with images owned by the specific user.
    """
    return (
        db.query(models.Tag)
        .join(models.Tag.images)
        .filter(models.Image.user_id == user_id)
        .filter(models.Image.status == 'active')
        .distinct()
        .all()
    )

# Advanced Image Search
def get_images(
    db: Session, 
    user_id: int,
    skip: int = 0, 
    limit: int = 50,
    tags: list[str] = None,
    start_date: datetime = None,
    end_date: datetime = None,
    sort_by: str = "uploaded_at",
    sort_order: str = "desc",
    status: str = "active"
):
    """
    Retrieves images based on complex filters.
    
    Flow:
    1. Filter by user_id and status.
    2. Filter by Time Range (if provided).
    3. Filter by Tags (image must have all provided tags).
    4. Apply Sorting.
    5. Apply Pagination.
    """
    # Base query
    query = db.query(models.Image).options(
        defer(models.Image.exif_data),
        defer(models.Image.ai_analysis),
        defer(models.Image.edit_history)
    ).filter(models.Image.user_id == user_id)
    if status:
        query = query.filter(models.Image.status == status)

    # 1. Date Range Filter
    if start_date:
        query = query.filter(models.Image.taken_at >= start_date)
    if end_date:
        query = query.filter(models.Image.taken_at <= end_date)

    # 2. Tag Filter (Intersection / AND Logic)
    if tags and len(tags) > 0:
        # Join with tags table
        query = query.join(models.Image.tags)
        # Filter rows where tag name is in the list
        query = query.filter(models.Tag.name.in_(tags))
        # Group by Image ID
        query = query.group_by(models.Image.id)
        # Ensure the count of matching tags equals the number of requested tags
        # e.g., if searching for ["Winter", "Dog"], the image must match both.
        query = query.having(func.count(models.Tag.id) == len(tags))

    # 3. Sorting
    sort_attr = getattr(models.Image, sort_by, models.Image.uploaded_at)
    if sort_order == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())

    # Secondary sort by ID for stability
    query = query.order_by(models.Image.id.desc())

    # 4. Pagination
    return query.offset(skip).limit(limit).all()