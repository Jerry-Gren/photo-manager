"""
Celery tasks for asynchronous image processing.

Handles CPU-bound image operations (thumbnails, EXIF extraction)
and updates the database state independently of the web server.
Architecture: Core -> Fan-out (AI only) -> Periodic Indexing. "enrich_gps" is merged into "enrich_ai_models" to save API calls.
"""

import os
import io
import logging
import json
import base64
from datetime import datetime
import httpx
import rawpy
from PIL import Image, ExifTags, ImageOps
import reverse_geocoder as rg

import pillow_heif
pillow_heif.register_heif_opener()

import pillow_jxl

from .worker import celery_app
from .database import SessionLocal
from . import models, crud, ai

# Setup logging
logger = logging.getLogger(__name__)

# Directory setup
UPLOAD_DIR = "/app/uploads"
THUMBNAILS_DIR = os.path.join(UPLOAD_DIR, "thumbnails")

# Ensure thumbnails directory exists
os.makedirs(THUMBNAILS_DIR, exist_ok=True)

# Priority list for determining 'taken_at'
DATE_TAGS_PRIORITY = ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]

# Tags to explicitly exclude from DB storage (Binary data, offsets, legacy junk)
EXIF_BLOCKLIST = {
    "MakerNote", "UserComment",
    "PrintImageMatching",
    "XPTitle", "XPComment", "XPAuthor", "XPKeywords", "XPSubject",
    "TIFF/EPStandardID",
    
    "ExifOffset", "ExifIFDPointer", "GPSInfoIFDPointer", "InteroperabilityIFDPointer",
    "JPEGInterchangeFormat", "JPEGInterchangeFormatLength",
    "StripOffsets", "StripByteCounts", "RowsPerStrip",
    "TileWidth", "TileLength", "TileOffsets", "TileByteCounts",
    "ThumbnailOffset", "ThumbnailLength", "ExifInteroperabilityOffset",
    "ImageUniqueID", "BodySerialNumber",
    "NewSubfileType",
    
    "Orientation",
    "ExifImageWidth", "ExifImageHeight",
    "ImageWidth", "ImageLength",
    "ShutterSpeedValue", "ApertureValue", "MaxApertureValue",
    "DateTime", "DateTimeDigitized",
    "OffsetTime", "OffsetTimeOriginal", "OffsetTimeDigitized",
    "LensSpecification",
    
    "MeteringMode", "ExposureProgram", "LightSource", "SensingMethod",
    "SceneCaptureType", "FileSource", "SceneType", "CustomRendered",
    "GainControl", "Contrast", "Saturation", "Sharpness",
    "SubjectDistance", "SubjectDistanceRange",
    "ExposureMode", "WhiteBalance", "DigitalZoomRatio",
    "BrightnessValue", "Software", "ProcessingSoftware",
    "SubsecTime", "SubsecTimeOriginal", "SubsecTimeDigitized",
    "SensitivityType", "ExposureIndex", "RecommendedExposureIndex",

    "CFAPattern", "CFARepeatPatternDim",
    "SpectralSensitivity", "OECF", "SpatialFrequencyResponse",
    "DeviceSettingDescription", "SubjectArea", "SubjectLocation",
    "CompressedBitsPerPixel", "ComponentsConfiguration",
    "FlashPixVersion", "ExifVersion",
    "InteroperabilityIndex", "InteroperabilityVersion",
    "RelatedSoundFile", "ImageDepth",
    "ResolutionUnit", "XResolution", "YResolution",
    "FocalPlaneXResolution", "FocalPlaneYResolution", "FocalPlaneResolutionUnit",
    "WhitePoint", "PrimaryChromaticities", "YCbCrCoefficients",
    "YCbCrSubSampling", "YCbCrPositioning", "ReferenceBlackWhite",
    "TransferFunction", "ColorSpace", "PlanarConfiguration",
    "SampleFormat", "TransferRange",
    "GPSVersionID", "GPSInfo",
    "BitsPerSample", "Compression", "PhotometricInterpretation", "SamplesPerPixel"
}

def get_db_session():
    """Helper to get a new database session for the task."""
    return SessionLocal()

# Helper Functions for EXIF
def _format_rational(value, digits=2):
    """
    Helper to handle Pillow's IFDRational or tuple (num, den).
    Returns a float.
    """
    try:
        # Pillow's IFDRational has .numerator and .denominator
        if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
            if value.denominator == 0: return 0.0
            return value.numerator / value.denominator
        # Handle tuple/list
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            n, d = float(value[0]), float(value[1])
            if d == 0: return 0.0
            return n / d
        # Handle simple number
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def _clean_for_json(value):
    """
    Recursively sanitizes values to ensure JSON serializability.
    Converts IFDRational, bytes, and complex tuples to simple types.
    """
    # 1. Handle Pillow IFDRational
    if hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        return float(value.numerator) / float(value.denominator) if value.denominator != 0 else 0.0
    # 2. Handle Bytes (decode or placeholder)
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode('utf-8').strip('\x00')
        except UnicodeDecodeError:
            return "<binary>"
    # 3. Handle Tuples/Lists (Recursion)
    if isinstance(value, (tuple, list)):
        return [_clean_for_json(item) for item in value]
    # 4. Handle Dictionaries (Recursion)
    if isinstance(value, dict):
        return {str(k): _clean_for_json(v) for k, v in value.items()}
    # 5. Passthrough for simple types
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    # 6. Fallback
    return str(value)

def _format_shutter_speed(value):
    """Format exposure time (e.g., 0.0166 -> '1/60')."""
    val = _format_rational(value)
    if val <= 0: return str(value)
    
    if val >= 1:
        # Long exposure, e.g., 2.5 -> "2.5s"
        return f"{val}s"
    else:
        # Fraction, e.g., 0.0166 -> "1/60"
        denominator = int(round(1.0 / val))
        return f"1/{denominator}"

def _format_aperture(value):
    """Format aperture (e.g., 1.777 -> 'f/1.8')."""
    val = _format_rational(value)
    if val <= 0: return str(value)
    return f"f/{round(val, 1)}"

def _format_focal_length(value):
    """Format focal length (e.g., 24.0 -> '24mm')."""
    val = _format_rational(value)
    if val <= 0: return str(value)
    return f"{int(round(val))}mm"

def _format_flash(value):
    """Parse Flash bitmask to simple status."""
    # Flash values are integers/tuples. 
    # Bit 0 indicates if flash fired.
    try:
        val = int(value)
        if val & 1:
            return "Fired"
        return "Did not fire"
    except:
        return str(value)

def _convert_to_degrees(value):
    """Helper to convert EXIF GPS (DMS) to decimal degrees."""
    try:
        # After _clean_for_json, value is likely a list of floats: [deg, min, sec]
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        # Fallback for single values (though rare for standard DMS)
        return float(value)
    except Exception:
        return 0.0

def get_lat_lon(exif_data):
    """Returns (lat, lon) from raw EXIF data if available."""
    gps_info = exif_data.get("GPSInfo")
    if not gps_info or not isinstance(gps_info, dict):
        return None, None

    # GPS Tag IDs:
    # 1: LatitudeRef, 2: Latitude, 3: LongitudeRef, 4: Longitude
    # Note: Keys are strings because _clean_for_json converted them.
    lat_ref = gps_info.get("1") or gps_info.get(1)
    lat_val = gps_info.get("2") or gps_info.get(2)
    lon_ref = gps_info.get("3") or gps_info.get(3)
    lon_val = gps_info.get("4") or gps_info.get(4)

    if lat_val and lat_ref and lon_val and lon_ref:
        lat = _convert_to_degrees(lat_val)
        if lat_ref != "N": lat = -lat
        lon = _convert_to_degrees(lon_val)
        if lon_ref != "E": lon = -lon
        return lat, lon
    return None, None

def parse_exif_data(pil_image):
    """
    Extracts and sanitizes EXIF data using modern Pillow APIs.
    Supports JPG, PNG, WebP etc.
    
    Returns:
        A tuple containing:
        - raw_exif_dict (dict): JSON-serializable dictionary of all EXIF tags.
        - taken_at (datetime | None): The parsed capture time.
        - raw_exif (dict | None): The raw PIL EXIF object (for GPS extraction).
    """
    exif_data = {}
    taken_at = None

    # Get raw EXIF object
    # getexif() works for JPG, PNG, WebP in newer Pillow versions
    raw_exif = pil_image.getexif()
    
    if raw_exif:
        for tag_id, value in raw_exif.items():
            # Get the human-readable tag name
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            tag_str = str(tag_name)
            
            # 1. Handle GPSInfo separately
            if tag_str == "GPSInfo":
                try:
                    gps_ifd = raw_exif.get_ifd(tag_id)
                    exif_data["GPSInfo"] = _clean_for_json({k: v for k, v in gps_ifd.items()})
                except Exception:
                    pass
                continue
            
            # 2. Skip unknown or blocklisted tags
            if isinstance(tag_name, int) or tag_str in EXIF_BLOCKLIST:
                continue
            
            # 3. Format specific values
            fmt_val = value
            if tag_str in ["FNumber", "ApertureValue"]:
                fmt_val = _format_aperture(value)
            elif tag_str == "ExposureTime":
                fmt_val = _format_shutter_speed(value)
            elif tag_str in ["FocalLength", "FocalLengthIn35mmFilm"]:
                fmt_val = _format_focal_length(value)
            elif tag_str == "Flash":
                fmt_val = _format_flash(value)
            
            # 4. Sanitize encoding (Binary -> String placeholder)
            if isinstance(fmt_val, (bytes, bytearray)):
                try:
                    # Try simple decode
                    if fmt_val.startswith(b'ASCII\x00\x00\x00'):
                        fmt_val = fmt_val[8:].decode('utf-8').strip('\x00')
                    else:
                        fmt_val = fmt_val.decode('utf-8').strip('\x00')
                except UnicodeDecodeError:
                    fmt_val = "<binary>"
            
            if not isinstance(fmt_val, (str, int, float, bool, type(None))):
                fmt_val = str(fmt_val)

            exif_data[tag_str] = fmt_val

        # 5. Parse Date (Priority Logic)
        for date_tag in DATE_TAGS_PRIORITY:
            if date_tag in exif_data:
                date_str = exif_data[date_tag]
                try:
                    # Clean up common garbage chars
                    clean_str = str(date_str).replace('\x00', '').strip()
                    # Standard EXIF: "YYYY:MM:DD HH:MM:SS"
                    taken_at = datetime.strptime(clean_str, "%Y:%m:%d %H:%M:%S")
                    break # Stop once we find the highest priority valid date
                except ValueError:
                    continue

    return exif_data, taken_at, raw_exif

def generate_time_tags(dt: datetime) -> list[str]:
    """Helper to convert datetime into discrete tags."""
    if not dt:
        return []
    
    tags = []
    # Year & Month
    tags.append(f"{dt.year}年")
    tags.append(f"{dt.month}月")
    
    # Season (only for Northern Hemisphere)
    month = dt.month
    if month in [3, 4, 5]: tags.append("春季")
    elif month in [6, 7, 8]: tags.append("夏季")
    elif month in [9, 10, 11]: tags.append("秋季")
    else: tags.append("冬季")
        
    # Time of day
    hour = dt.hour
    if 5 <= hour < 12: tags.append("上午")
    elif 12 <= hour < 18: tags.append("下午")
    else: tags.append("晚上")
        
    return tags

def load_visual_image(path):
    """
    Load image for visual tasks (Thumbnails, AI).
    Handles RAW (NEF, ARW, DNG) via rawpy, others via Pillow.
    Returns: Pillow Image Object (RGB)
    """
    ext = os.path.splitext(path)[1].lower()
    
    # List of RAW formats to process with rawpy
    raw_exts = {'.nef', '.arw', '.dng', '.cr2', '.cr3', '.raf', '.orf', '.rw2'}
    
    if ext in raw_exts:
        try:
            logger.info(f"Developing RAW image: {path}")
            with rawpy.imread(path) as raw:
                # Postprocess: Demosaic, White Balance, Color Space conversion -> Numpy Array
                # use_camera_wb=True uses the WB shot by camera
                rgb_array = raw.postprocess(use_camera_wb=True, no_auto_bright=False, bright=1.0)
                return Image.fromarray(rgb_array)
        except Exception as e:
            logger.error(f"Rawpy failed for {path}, falling back to Pillow: {e}")
            # Fallback to Pillow (might look dark or be a low-res preview)
            return Image.open(path)
    else:
        # JPG, PNG, HEIC, JXL, etc.
        return Image.open(path)

@celery_app.task(bind=True, max_retries=3)
def process_image_core(self, image_id: int):
    """
    Core asynchronous task for processing an uploaded image.
    
    Steps:
    1. Load image record from DB.
    2. Open file with Pillow.
    3. Extract EXIF & Generate thumbnail.
    4. Update DB record status to 'active'.
    5. Fan-Out Enhance tasks.
    
    Args:
        self: The task instance.
        image_id: The ID of the image record.
    """
    db = get_db_session()
    try:
        # 1. Load image record
        db_image = crud.get_image(db, image_id=image_id)
        if not db_image:
            logger.error(f"Image {image_id} not found in database.")
            return

        logger.info(f"[Core] Processing Image {image_id}...")

        # 1. Parse EXIF
        # Note: Pillow can read metadata from RAW files even if visual is bad
        try:
            with Image.open(db_image.storage_path) as meta_img:
                exif_dict, taken_at, _ = parse_exif_data(meta_img)
                lat, lon = get_lat_lon(exif_dict)
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
            exif_dict, taken_at, lat, lon = {}, None, None, None
        
        # 2. Load Visual Image
        with load_visual_image(db_image.storage_path) as img:
            # Fix Orientation
            if hasattr(img, 'getexif'): # Check if it's a standard Pillow image
                img = ImageOps.exif_transpose(img)
            res_w, res_h = img.size
            
            # Thumbnail
            MAX_SIZE = (800, 800)
            thumb = img.copy()
            thumb.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Handle Transparency
            base_name = os.path.basename(db_image.storage_path)
            name_part, _ = os.path.splitext(base_name)

            has_transparency = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
            
            if has_transparency:
                thumb_filename = f"{name_part}_thumb.png"
                thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
                thumb.save(thumb_path, "PNG", optimize=True)
            else:
                if thumb.mode != 'RGB': thumb = thumb.convert('RGB')
                thumb_filename = f"{name_part}_thumb.jpg"
                thumb_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
                thumb.save(thumb_path, "JPEG", quality=85, optimize=True)

            # 4. Update DB Record
            db_image.thumbnail_path = thumb_path
            db_image.exif_data = exif_dict # Stores full raw EXIF as JSON
            db_image.taken_at = taken_at
            db_image.resolution_width = res_w
            db_image.resolution_height = res_h
            db_image.status = "active" # Mark as ready
            
            # Clear any previous errors
            db_image.processing_error = None

            # Try to use EXIF ImageDescription if no description specified
            # If both fails, enrich_ai_models will generate one
            current_desc = db_image.description
            if not current_desc and "ImageDescription" in exif_dict:
                desc_from_exif = exif_dict["ImageDescription"].strip()
                if desc_from_exif and desc_from_exif.lower() != "string":
                    db_image.description = desc_from_exif
                    logger.info(f"Using EXIF ImageDescription for Image {image_id}")
                
            db.commit()

            # Generate time tags
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
            
            logger.info(f"[Core] Image {image_id} processed successfully. Status: active.")

            # 5. Fan-Out Enhance Tasks
            enrich_ai_models.delay(image_id, lat, lon)

    except Exception as e:
        # Handle processing errors (e.g., corrupt file)
        logger.error(f"[Core] Error processing image {image_id}: {str(e)}")
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

# Fan-out Tasks
@celery_app.task(bind=True, max_retries=3)
def enrich_ai_models(self, image_id: int, lat: float = None, lon: float = None):
    """
    Enhance Task 2: AI Vision Analysis.
    Calls GPT-4o (Vision). This is a combined task:
        1. Offline Reverse Geocoding (Rough location).
        2. AI Vision Analysis (Refined location + Caption + Tags).
    
    Args:
        self: The task instance.
        image_id: The ID of the image record.
    """
    db = get_db_session()
    try:
        image = crud.get_image(db, image_id)
        if not image: return

        logger.info(f"[AI] Analyzing Image {image_id} (GPS: {lat}, {lon})...")

        # 1. Offline Reverse Geocoding
        rough_location = "Unknown"
        if lat is not None and lon is not None:
            try:
                # mode=1 single thread to prevent Celery crash
                results = rg.search((lat, lon), mode=1)
                if results:
                    data = results[0]
                    # e.g. "Hangzhou, Zhejiang, CN"
                    rough_location = f"{data.get('name')}, {data.get('admin1')}, {data.get('cc')}"
                    logger.info(f"[AI] Rough location found: {rough_location}")
            except Exception as e:
                logger.warning(f"[AI] Rough geocoding failed: {e}")

        # 2. AI Vision Analysis
        # 2.1. Encode image to base64
        with load_visual_image(image.storage_path) as image_file:
            if image_file.mode != 'RGB':
                image_file = image_file.convert('RGB')
            if max(image_file.size) > 2048:
                image_file.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            image_file.save(buffer, format="JPEG", quality=85)
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 2.2. generate rough location constraint
        location_context = "Empty."
        if lat is not None:
            location_context = (
                f"GPS Coordinates: ({lat}, {lon}). "
                f"Rough Administrative Location: '{rough_location}'. "
                "Use this to identify the specific landmark or precise address in Chinese."
            )
        logger.info(f"location_context: {location_context}")

        # 2.3. Synchronously call LLM vision API
        headers = {
            "Authorization": f"Bearer {ai.LLM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Analyze this image. The original filename is "{image.original_filename}".
        Location Context: {location_context}

        Tasks:
        1. **caption**: A short description in Simplified Chinese (简体中文). You are encouraged to use "，" to make the caption clear and coherent.
        2. **tags**: 3-5 keywords in Simplified Chinese (简体中文) describing the objects or scene. Any location/administrative name must be excluded from tags.
        3. **location_zh**: Based on the visual scene and the provided GPS/Rough Location, identify the precise location name in Simplified Chinese (e.g., "杭州市西湖区雷峰塔"). If uncertain, use the administrative name (e.g., "日本大阪"). Keep this field empty only if no location context is provided.
        
        Return JSON format ONLY:
        {{
            "caption": "公园草地上，有一只可爱的狗在奔跑",
            "tags": ["狗", "公园", "草地", "奔跑"],
            "location_zh": "..."
        }}
        """
        
        payload = {
            "model": ai.LLM_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "max_tokens": 500,
            "response_format": { "type": "json_object" }
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{ai.LLM_API_BASE}/chat/completions", 
                json=payload, 
                headers=headers
            )
            resp.raise_for_status()
            result_str = resp.json()["choices"][0]["message"]["content"]

            if result_str.startswith("```"):
                lines = result_str.split("\n")
                if len(lines) > 2:
                    result_str = "\n".join(lines[1:-1])
            
            result_json = json.loads(result_str)

        # 4. Update DB
        image.ai_analysis = result_json

        # 4.1. Autofill description
        current_desc = image.description.strip() if image.description else ""
        if not current_desc:
            image.description = result_json.get("caption", "")
            logger.info(f"[AI] Auto-filled description for Image {image_id}")
        else:
            logger.info(f"[AI] Keeping user description for Image {image_id}")
        
        # 4.2. Add tegs
        for tag in result_json.get("tags", []):
            crud.add_tag_to_image(db, image_id, tag, "ai_generated")
            logger.info(f"[AI] Tags added for Image {image_id}")

        # 4.3 Update Location
        loc_zh = result_json.get("location_zh")
        if loc_zh:
            image.location_name = loc_zh
            crud.add_tag_to_image(db, image_id, loc_zh, "exif_location")
            logger.info(f"[AI] Location refined to: {loc_zh}")
        elif rough_location != "Unknown":
            # Fallback to rough location if AI failed to identify
            image.location_name = rough_location
            crud.add_tag_to_image(db, image_id, rough_location, "exif_location")
            logger.info(f"[AI] Fall back to use rough location: {rough_location}")
            
        db.commit()
        logger.info(f"[AI] Analysis complete. Caption: {result_json.get('caption')}. Tags: {result_json.get('tags')}. Location: {result_json.get('location_zh')}")

    except Exception as e:
        logger.error(f"[AI] Analysis failed for {image_id}: {e}")
        try:
            raise self.retry(exc=e, countdown=60)
        except Exception:
            pass
    finally:
        db.close()

# Periodic RAG Indexing
@celery_app.task
def build_rag_index():
    """
    Scans for active images that are not yet indexed in RAG.
    Scheduled by Celery Beat to run periodically.
    """
    db = get_db_session()
    try:
        # Find candidates (active & not indexed)
        # Limit to 10 per run to avoid long blocking
        candidates = db.query(models.Image).filter(
            models.Image.status == 'active', 
            models.Image.rag_indexed == False,
            models.Image.ai_analysis.isnot(None)
        ).limit(10).all()

        if not candidates:
            return

        logger.info(f"[Indexer] Found {len(candidates)} images to index.")
        collection = ai.get_chroma_collection()

        for image in candidates:
            try:
                # Construct RAG Source Text
                tag_names = [t.name for t in image.tags]
                
                parts = []
                if image.title: 
                    parts.append(f"标题: {image.title}")
                if image.original_filename:
                    parts.append(f"文件名: {image.original_filename}")
                if image.taken_at: 
                    parts.append(f"时间: {image.taken_at.strftime('%Y-%m-%d')}")
                if image.location_name: 
                    parts.append(f"地点: {image.location_name}")
                if tag_names: 
                    parts.append(f"标签: {', '.join(tag_names)}")
                if image.description: 
                    parts.append(f"描述: {image.description}")
                
                rag_text = "。".join(parts)
                if not rag_text: 
                    rag_text = "图片"

                # Generate Embedding
                embedding = ai.generate_embedding_sync(rag_text)

                # Upsert to ChromaDB
                collection.upsert(
                    ids=[str(image.id)],
                    embeddings=[embedding],
                    metadatas=[{
                        "image_id": image.id,
                        "user_id": image.user_id,
                        "thumbnail_url": f"/api/v1/images/{image.id}/thumbnail",
                        "text": rag_text
                    }]
                )

                # Mark as indexed
                image.rag_indexed = True
                db.commit()
                logger.info(f"[Indexer] Indexed Image {image.id}")
            
            except Exception as e:
                logger.error(f"[Indexer] Failed Image {image.id}: {e}")
                db.rollback()

    finally:
        db.close()