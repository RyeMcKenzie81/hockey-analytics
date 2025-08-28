from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from uuid import UUID
import logging

from ..models import EventResponse, EventCreate
from ..database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[EventResponse])
async def list_events(
    video_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    verified: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """List events with optional filtering."""
    # Will be implemented with Supabase integration
    return []


@router.post("/", response_model=EventResponse)
async def create_event(event: EventCreate):
    """Create a new event."""
    # Will be implemented with Supabase integration
    raise HTTPException(status_code=501, detail="Not implemented yet")