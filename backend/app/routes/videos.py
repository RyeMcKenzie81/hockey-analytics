from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from uuid import UUID
import logging

from ..models import VideoResponse, ServiceResponse
from ..database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    org_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List videos with optional filtering."""
    # Will be implemented with Supabase integration
    return []


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(video_id: UUID):
    """Get a specific video by ID."""
    # Will be implemented with Supabase integration
    raise HTTPException(status_code=404, detail="Video not found")