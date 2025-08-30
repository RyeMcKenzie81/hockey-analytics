from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class EventType(str, Enum):
    GOAL = "goal"
    PENALTY = "penalty"
    SHOT = "shot"
    SAVE = "save"
    FACEOFF = "faceoff"
    OFFSIDE = "offside"
    ICING = "icing"
    HIT = "hit"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"


class ServiceResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoUpload(BaseModel):
    filename: str
    org_id: UUID
    metadata: Optional[Dict[str, Any]] = None


class VideoResponse(BaseModel):
    id: UUID
    org_id: Optional[str] = None  # Allow None values from database
    filename: str
    storage_path: str
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    fps: Optional[int] = None
    resolution: Optional[str] = None
    status: VideoStatus
    hls_manifest_url: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class EventCreate(BaseModel):
    video_id: UUID
    event_type: EventType
    timestamp_seconds: float = Field(ge=0)
    confidence_score: float = Field(ge=0, le=1, default=0.0)
    detection_method: Optional[str] = None
    frame_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    id: UUID
    org_id: str  # Changed from UUID to str to handle "default" organization
    video_id: UUID
    event_type: EventType
    timestamp_seconds: float
    confidence_score: float
    detection_method: Optional[str] = None
    verified: bool
    verified_by: Optional[UUID] = None
    frame_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime
    settings: Optional[Dict[str, Any]] = None


class MLProcessingRequest(BaseModel):
    video_id: UUID
    org_id: UUID
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    detection_types: Optional[List[EventType]] = None
    use_gemini: bool = True


class MLProcessingResponse(BaseModel):
    video_id: UUID
    processing_id: str
    status: str
    message: str
    events_detected: Optional[int] = None


class EventDetectionResult(BaseModel):
    event_type: EventType
    timestamp: float
    confidence_score: float = Field(ge=0, le=1)
    frame_number: int
    metadata: Dict[str, Any]
    bounding_boxes: Optional[List[Dict[str, Any]]] = None
    source: str = Field(default="ml", description="Detection source: ml, gemini, or manual")
    
    
class BatchEventCreate(BaseModel):
    video_id: UUID
    org_id: UUID
    events: List[EventDetectionResult]
    processing_id: Optional[str] = None