"""
Celery tasks for asynchronous image processing.

Handles CPU-bound image operations (thumbnails, EXIF extraction)
and updates the database state independently of the web server.
"""

import os
import logging
import json
from datetime import datetime
from PIL import Image, ExifTags, ImageOps

from .worker import celery_app
from .database import SessionLocal
from . import models, crud

# Setup logging
logger = logging.getLogger(__name__)

# Directory setup
UPLOAD_DIR = "/app/uploads"
THUMBNAILS_DIR = os.path.join(UPLOAD_DIR, "thumbnails")

# Ensure thumbnails directory exists
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

def get_db_session():
    """Helper to get a new database session for the task."""
    return SessionLocal()

def parse_exif_data(pil_image):
    """
    Extracts and sanitizes EXIF data from a PIL image.
    
    Returns:
        A tuple containing:
        - raw_exif_dict (dict): JSON-serializable dictionary of all EXIF tags.
        - taken_at (datetime | None): The parsed capture time.
        - resolution (tuple): (width, height) from headers or EXIF.
    """
    exif_data = {}
    taken_at = None
    
    # Basic resolution
    width, height = pil_image.size

    # Get raw EXIF object
    raw_exif = None
    if hasattr(pil_image, "_getexif"):
        try:
            raw_exif = pil_image._getexif()
        except Exception:
            pass

    # All types of date tags that we cares about
    date_tags = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]
    
    if raw_exif:
        for tag_id, value in raw_exif.items():
            # Get the human-readable tag name
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            
            # 1. Parse date_tags
            if tag_name in date_tags and not taken_at:
                try:
                    taken_at = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass

            # 2. Sanitize value for JSON storage
            # EXIF values can be bytes or complex objects; convert to string if needed
            if isinstance(value, (bytes, bytearray)):
                try:
                    value = value.decode()
                except UnicodeDecodeError:
                    value = "<binary data>"
            
            # Store with string keys for JSON serialization
            exif_data[str(tag_name)] = str(value)

    return exif_data, taken_at, (width, height)

def generate_time_tags(dt: datetime) -> list[str]:
    """Helper to convert datetime into discrete tags."""
    if not dt:
        return []
    
    tags = []
    # Year
    tags.append(f"{dt.year}年")
    
    # Month
    tags.append(f"{dt.month}月")
    
    # Season (only for Northern Hemisphere)
    month = dt.month
    if month in [3, 4, 5]:
        tags.append("春季")
    elif month in [6, 7, 8]:
        tags.append("夏季")
    elif month in [9, 10, 11]:
        tags.append("秋季")
    else:
        tags.append("冬季")
        
    # Time of day
    hour = dt.hour
    if 5 <= hour < 12:
        tags.append("上午")
    elif 12 <= hour < 18:
        tags.append("下午")
    else:
        tags.append("晚上")
        
    return tags

@celery_app.task(bind=True, max_retries=3)
def process_image_core(self, image_id: int):
    """
    Core asynchronous task for processing an uploaded image.
    
    Steps:
    1. Load image record from DB.
    2. Open file with Pillow.
    3. Extract EXIF & Generate thumbnail.
    4. Update DB record status to 'active'.
    
    Args:
        self: The task instance (for retry logic).
        image_id: The ID of the image record to process.
    """
    db = get_db_session()
    try:
        # 1. Load image record
        db_image = crud.get_image(db, image_id=image_id)
        if not db_image:
            logger.error(f"Image {image_id} not found in database.")
            return

        logger.info(f"Starting processing for Image {image_id}...")

        # 2. Open file with Pillow
        try:
            with Image.open(db_image.storage_path) as raw_img:
                # 3. Extract EXIF & Generate Thumbnail
                # We use .copy() to avoid modifying the open object if we need it later
                exif_dict, taken_at, _ = parse_exif_data(raw_img)
                img = ImageOps.exif_transpose(raw_img) # This will fix image rotation
                res_w, res_h = img.size
                thumb = img.copy()
                thumb.thumbnail((400, 400))
                
                # Construct thumbnail filename
                base_name = os.path.basename(db_image.storage_path)
                name_part, _ = os.path.splitext(base_name)
                thumb_filename = f"{name_part}_thumb.jpg"
                thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
                
                # Save thumbnail (convert to RGB to handle PNGs with transparency)
                if thumb.mode in ("RGBA", "P"):
                    thumb = thumb.convert("RGB")
                thumb.save(thumb_path, "JPEG", quality=80)

                # 4. Update DB Record
                db_image.thumbnail_path = thumb_path
                db_image.exif_data = exif_dict # Stores full raw EXIF as JSON
                db_image.taken_at = taken_at
                db_image.resolution_width = res_w
                db_image.resolution_height = res_h
                db_image.status = "active" # Mark as ready
                
                # Clear any previous errors
                db_image.processing_error = None
                
                db.commit()

                # Generate time tags after marking as 'active'
                # Status will remain 'active' even if this step fails
                try:
                    if db_image.taken_at:
                        time_tags = generate_time_tags(db_image.taken_at)
                        for tag_name in time_tags:
                            crud.add_tag_to_image(
                                db, 
                                image_id=image_id, 
                                tag_name=tag_name, 
                                tag_type="derived_time"
                            )
                            logger.info(f"Added time tag '{tag_name}' to Image {image_id}")
                except Exception as e:
                    logger.error(f"Failed to generate time tags for {image_id}: {e}")
                
                logger.info(f"Image {image_id} processed successfully. Status: active.")

                # Future: Trigger enhance tasks here (GPS, AI)
                # enrich_gps.delay(image_id)
                # enrich_ai_models.delay(image_id)

        except Exception as e:
            # Handle processing errors (e.g., corrupt file)
            logger.error(f"Error processing image {image_id}: {str(e)}")
            db.rollback()
            
            # Update status to failed
            crud.update_image_status(
                db, 
                image_id, 
                status="failed", 
                error=str(e)
            )
            # Re-raise to let Celery know (optional, depending on retry policy)
            # raise e

    finally:
        db.close()