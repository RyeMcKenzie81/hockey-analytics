from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID
import logging

from ..models import OrganizationResponse, OrganizationCreate
from ..database import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[OrganizationResponse])
async def list_organizations():
    """List all organizations."""
    # Will be implemented with Supabase integration
    return []


@router.post("/", response_model=OrganizationResponse)
async def create_organization(org: OrganizationCreate):
    """Create a new organization."""
    # Will be implemented with Supabase integration
    raise HTTPException(status_code=501, detail="Not implemented yet")