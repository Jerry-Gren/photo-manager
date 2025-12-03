"""
API router for image-related endpoints.

Handles file uploads, storage, and initiates asynchronous processing.
"""

import os
import shutil
import uuid
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import auth, crud, models, schemas
from ..database import get_db
from .. import tasks 

router = APIRouter(
    prefix="/api/v1/images",
    tags=["Images"],
)

# Configuration for upload paths
UPLOAD_DIR = "/app/uploads"
ORIGINALS_DIR = os.path.join(UPLOAD_DIR, "originals")

# Ensure directories exist
os.makedirs(ORIGINALS_DIR, exist_ok=True)

@router.post("", response_model=schemas.Image, status_code=status.HTTP_202_ACCEPTED)
async def upload_image(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Uploads a new image.

    Flow:
    1. Validates file type.
    2. Generates a secure UUID filename.
    3. Saves the file to the 'originals' directory.
    4. Set default title if not provided
    5. Creates a DB record with status='processing'.
    6. Triggers a Celery task for background processing.
    7. Returns 202 Accepted immediately.

    Args:
        file: The image file stream.
        title: Optional title via form data.
        description: Optional description via form data.
        current_user: The authenticated user.
        db: Database session.

    Returns:
        The created Image object (with 'processing' status).
    """
    # 1. Basic validation
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # 2. Generate secure filename
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext:
        file_ext = "" # Should handle case with no extension
    
    storage_filename = f"{uuid.uuid4()}{file_ext}"
    storage_path = os.path.join(ORIGINALS_DIR, storage_filename)

    # 3. Save file to disk
    try:
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    # Calculate file size
    file_size = os.path.getsize(storage_path)

    # 4. Set default title
    final_title = title
    if not final_title:
        base_name = os.path.basename(file.filename)
        final_title, _ = os.path.splitext(base_name)

    # 5. Create DB record
    db_image = models.Image(
        user_id=current_user.id,
        original_filename=file.filename,
        storage_path=storage_path,
        mime_type=file.content_type,
        file_size=file_size,
        status="processing", # Initial status
        title=title,
        description=description
    )
    
    created_image = crud.create_image_placeholder(db=db, image=db_image)

    # 6. Trigger Celery Task
    # passing the ID of the newly created image record
    tasks.process_image_core.delay(created_image.id)

    return created_image

@router.get("/{image_id}/file")
async def get_image_file(
    image_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the original image file.
    """
    image = crud.get_image(db, image_id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this image")

    if not os.path.exists(image.storage_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(image.storage_path, media_type=image.mime_type)

@router.get("/{image_id}/thumbnail")
async def get_image_thumbnail(
    image_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the thumbnail file.
    """
    image = crud.get_image(db, image_id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this image")

    if not image.thumbnail_path or not os.path.exists(image.thumbnail_path):
        # Thumbnail is processing, or fails
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    return FileResponse(image.thumbnail_path, media_type="image/jpeg")

@router.get("", response_model=List[schemas.Image])
async def read_images(
    tags: Optional[List[str]] = Query(None, description="Filter by tag names"),
    status: Optional[str] = Query("active", description="Filter by status (processing, active, archived, failed, active_deleted, archived_deleted). Pass empty to see all."),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: str = "uploaded_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Search images with complex filters.
    Args:
        tags: List of tag names. Image must have all specified tags.
        start_date/end_date: Filter by capture time.
        sort_by: Field to sort by (e.g., 'taken_at', 'uploaded_at').
    Returns:
        A list of image metadata objects matching the search criteria,
        including their associated tags and status.
    """
    return crud.get_images(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        tags=tags,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
        status=status
    )

@router.post("/{image_id}/tags", status_code=status.HTTP_201_CREATED)
async def add_tag_to_image(
    image_id: int,
    tag: schemas.TagCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Add a custom user tag to an image.
    """
    # 1. Check ownership
    image = crud.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this image")
        
    # 2. Add tag
    crud.add_tag_to_image(db, image_id, tag.name, tag_type="user")
    
    return {"message": "Tag added successfully"}

@router.delete("/{image_id}/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_image(
    image_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Remove a tag from an image.
    """
    # 1. Check ownership
    image = crud.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this image")

    # 2. Remove tag
    crud.remove_tag_from_image(db, image_id, tag_id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)