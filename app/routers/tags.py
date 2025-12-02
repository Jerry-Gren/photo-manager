"""
API router for tag-related endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/tags",
    tags=["Tags"],
)

@router.get("", response_model=List[schemas.Tag])
async def read_tags(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Get all available tags in the system.
    Used for frontend autocomplete/filter dropdowns.
    This only returns tags that are currently linked to the user's own images.
    """
    return crud.get_tags_by_user(db, user_id=current_user.id)