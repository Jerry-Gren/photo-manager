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
from sqlalchemy.orm import Session
from PIL import Image as PILImage, ImageOps

from .. import auth, crud, models, schemas, ai
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
        raise HTTPException(status_code=400, detail="只能上传图片格式的文件")

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
        raise HTTPException(status_code=500, detail=f"文件保存失败: {e}")
    
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
    Uses Nginx X-Accel-Redirect.
    """
    image = crud.get_image(db, image_id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    if image.status in ["active_deleted", "archived_deleted"]:
        raise HTTPException(status_code=404, detail="图片已被删除")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权访问该图片")

    relative_path = os.path.relpath(image.storage_path, "/app/uploads")
    nginx_redirect_path = f"/protected_uploads/{relative_path}"

    return Response(
        content=None,
        status_code=200,
        headers={
            "X-Accel-Redirect": nginx_redirect_path,
            "Content-Type": image.mime_type,
            "Cache-Control": "no-cache"
        }
    )

@router.get("/{image_id}/thumbnail")
async def get_image_thumbnail(
    image_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the thumbnail file.
    Uses Nginx X-Accel-Redirect.
    """
    image = crud.get_image(db, image_id=image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
    
    if image.status in ["active_deleted", "archived_deleted"]:
        raise HTTPException(status_code=404, detail="图片已被删除")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权访问该图片")

    if not image.thumbnail_path:
        # Thumbnail is processing, or fails
        raise HTTPException(status_code=404, detail="缩略图尚未生成或生成失败")

    relative_path = os.path.relpath(image.thumbnail_path, "/app/uploads")
    nginx_redirect_path = f"/protected_uploads/{relative_path}"

    return Response(
        content=None,
        status_code=200,
        headers={
            "X-Accel-Redirect": nginx_redirect_path,
            "Content-Type": "image/jpeg",
            "Cache-Control": "no-cache"
        }
    )

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
        raise HTTPException(status_code=404, detail="图片不存在")
    
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权编辑该图片")
        
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
        raise HTTPException(status_code=404, detail="图片不存在")
        
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权编辑该图片")

    # 2. Remove tag
    crud.remove_tag_from_image(db, image_id, tag_id)
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{image_id}/edit", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Image)
async def edit_image(
    image_id: int,
    edit_req: schemas.ImageEditRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs non-destructive editing on an image.

    Flow:
    1. Validate ownership.
    2. Load original image from disk.
    3. Apply Crop/Filter using Pillow.
    4. Save as a new file.
    5. Archive the old DB record (status='archived').
    6. Remove old record from ChromaDB (to prevent searching outdated content).
    7. Create a new DB record (status='processing', parent=old_id).
    8. Trigger Celery task for the new image.
    """
    # 1. Validation
    original_db_image = crud.get_image(db, image_id)
    if not original_db_image:
        raise HTTPException(status_code=404, detail="图片不存在")
    if original_db_image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权编辑该图片")
    
    if not os.path.exists(original_db_image.storage_path):
        raise HTTPException(status_code=404, detail="原始图片文件丢失")

    # 2. Process Image
    try:
        with PILImage.open(original_db_image.storage_path) as img:
            # Handle orientation first to ensure crop coordinates match visual
            img = ImageOps.exif_transpose(img)
            
            # Apply Crop
            if edit_req.crop:
                c = edit_req.crop
                # Pillow crop: (left, top, right, bottom)
                # Ensure coordinates are within bounds
                left = max(0, c.x)
                top = max(0, c.y)
                right = min(img.width, c.x + c.width)
                bottom = min(img.height, c.y + c.height)
                
                if right > left and bottom > top:
                    img = img.crop((left, top, right, bottom))
            
            # Apply Simple Filters
            if edit_req.filter == "grayscale":
                img = ImageOps.grayscale(img)
            # Add more filters here if needed
            
            # 3. Save New File
            file_ext = os.path.splitext(original_db_image.original_filename)[1]
            if not file_ext: file_ext = ".jpg"
            
            new_filename = f"{uuid.uuid4()}{file_ext}"
            new_storage_path = os.path.join(ORIGINALS_DIR, new_filename)
            
            # Save
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(new_storage_path, quality=95)
            
            new_file_size = os.path.getsize(new_storage_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片处理失败: {e}")

    # 4. Database Transaction
    try:
        # Archive old image
        original_db_image.status = "archived"
        original_db_image.rag_indexed = False
        
        # Create new image record
        new_image = models.Image(
            user_id=current_user.id,
            original_filename=original_db_image.original_filename, # Keep original name
            storage_path=new_storage_path,
            mime_type="image/jpeg",
            file_size=new_file_size,
            status="processing",
            parent_image_id=original_db_image.id,
            root_image_id=original_db_image.root_image_id, # Inherit root
            
            # Inherit metadata
            title=original_db_image.title,
            description=original_db_image.description,
            # taken_at, location will be re-parsed by Celery from EXIF (if preserved)
        )
        
        # Save to DB
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        # 5. Clean up Vector DB
        try:
            collection = ai.get_chroma_collection()
            collection.delete(ids=[str(original_db_image.id)])
            print(f"Removed Image {original_db_image.id} from RAG index.")
        except Exception as e:
            print(f"Warning: Failed to remove old vector: {e}")

        # 6. Trigger Celery Task for new image
        tasks.process_image_core.delay(new_image.id)
        
        return new_image

    except Exception as e:
        db.rollback()
        # Clean up the new file if DB failed
        if os.path.exists(new_storage_path):
            os.remove(new_storage_path)
        raise HTTPException(status_code=500, detail=f"数据库错误: {e}")

@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Soft deletes an image.

    Flow:
    1. Mark status as 'active_deleted' (or 'archived_deleted').
    2. Remove from ChromaDB.
    """
    image = crud.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="图片不存在")
        
    if image.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="您无权删除该图片")

    # 1. Update Status
    previous_status = image.status
    if previous_status == 'active':
        image.status = 'active_deleted'
    elif previous_status == 'archived':
        image.status = 'archived_deleted'
    else:
        image.status = 'active_deleted'
    
    image.rag_indexed = False
    db.commit()

    # 2. Remove from Vector DB
    try:
        collection = ai.get_chroma_collection()
        collection.delete(ids=[str(image_id)])
        print(f"Removed Image {image_id} from RAG index.")
    except Exception as e:
        # Don't fail the request just because Chroma failed, but log it
        print(f"Warning: Failed to delete vector for {image_id}: {e}")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)