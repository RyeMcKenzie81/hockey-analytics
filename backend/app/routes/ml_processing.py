from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from uuid import UUID, uuid4
import os
import logging
from pathlib import Path

from ..models import (
    MLProcessingRequest,
    MLProcessingResponse,
    EventDetectionResult,
    BatchEventCreate,
    EventCreate,
    EventResponse,
    ServiceResponse
)
from ..database import get_supabase
from ..services.ml_detector import HockeyDetector, EventDetection
from ..services.gemini_analyzer import GeminiAnalyzer
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ml", tags=["ML Processing"])

# Initialize ML services (singleton pattern)
_ml_detector = None
_gemini_analyzer = None

def get_ml_detector() -> HockeyDetector:
    """Get or create ML detector instance"""
    global _ml_detector
    if _ml_detector is None:
        _ml_detector = HockeyDetector()
    return _ml_detector

def get_gemini_analyzer() -> Optional[GeminiAnalyzer]:
    """Get or create Gemini analyzer instance"""
    global _gemini_analyzer
    if _gemini_analyzer is None and settings.GEMINI_API_KEY:
        _gemini_analyzer = GeminiAnalyzer(settings.GEMINI_API_KEY)
    return _gemini_analyzer


@router.post("/process", response_model=MLProcessingResponse)
async def start_ml_processing(
    request: MLProcessingRequest,
    background_tasks: BackgroundTasks,
    supabase=Depends(get_supabase)
):
    """Start ML processing for a video"""
    
    try:
        # Log the incoming request for debugging
        logger.info(f"ML processing request: video_id={request.video_id}, org_id={request.org_id}")
        
        # Verify video exists
        video_result = supabase.table('videos').select('*').eq('id', str(request.video_id)).single().execute()
        
        if not video_result.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        video = video_result.data
        
        # Verify video is processed (HLS ready)
        if video['status'] != 'processed':
            raise HTTPException(
                status_code=400, 
                detail=f"Video must be processed first. Current status: {video['status']}"
            )
        
        # Generate processing ID
        processing_id = str(uuid4())
        logger.info(f"Starting ML processing with ID: {processing_id}")
        
        # Start background processing
        background_tasks.add_task(
            process_video_ml,
            video_id=request.video_id,
            org_id=request.org_id,
            processing_id=processing_id,
            start_time=request.start_time,
            end_time=request.end_time,
            use_gemini=request.use_gemini
        )
        
        return MLProcessingResponse(
            video_id=request.video_id,
            processing_id=processing_id,
            status="started",
            message="ML processing started in background"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting ML processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_video_ml(
    video_id: UUID,
    org_id: UUID,
    processing_id: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    use_gemini: bool = True
):
    """Background task to process video with ML"""
    
    logger.info(f"Starting ML processing for video {video_id} (processing_id: {processing_id})")
    
    try:
        # Get video details from database
        supabase = get_supabase()
        video_result = supabase.table('videos').select('*').eq('id', str(video_id)).single().execute()
        video = video_result.data
        
        # Get video file path
        video_path = video['storage_path']
        
        # If it's a Supabase storage path, download it locally first
        if video_path.startswith('videos/'):
            # Download from Supabase storage
            local_path = await download_video_from_storage(video_id, video_path)
            video_path = local_path
        
        # Set processing bounds
        if start_time is None:
            start_time = 0.0
        if end_time is None:
            end_time = video.get('duration_seconds', 60.0)
        
        # Initialize ML detector
        ml_detector = get_ml_detector()
        await ml_detector.load_models()
        
        # Process video segment
        ml_events = await ml_detector.process_video_segment(
            video_id=str(video_id),
            video_path=video_path,
            start_time=start_time,
            end_time=end_time,
            fps=video.get('fps', 30.0)
        )
        
        logger.info(f"ML detection found {len(ml_events)} events")
        
        # Enhance with Gemini if enabled
        if use_gemini and settings.GEMINI_API_KEY:
            gemini_analyzer = get_gemini_analyzer()
            if gemini_analyzer:
                logger.info("Enhancing detections with Gemini...")
                
                # Extract frames for Gemini analysis
                frames = await ml_detector.extract_frames(
                    video_path,
                    start_time,
                    end_time,
                    video.get('fps', 30.0)
                )
                
                # Analyze with Gemini
                gemini_analysis = await gemini_analyzer.analyze_segment(
                    frames=frames,
                    existing_detections=ml_events,
                    segment_info={
                        'start_time': start_time,
                        'end_time': end_time,
                        'video_id': str(video_id)
                    }
                )
                
                # Enhance events with Gemini analysis
                ml_events = await gemini_analyzer.enhance_detections(
                    ml_events,
                    gemini_analysis
                )
                
                logger.info(f"Gemini enhanced to {len(ml_events)} total events")
        
        # Store events in database
        await store_detected_events(
            video_id=video_id,
            org_id=org_id,
            events=ml_events,
            processing_id=processing_id
        )
        
        logger.info(f"ML processing complete for video {video_id}")
        
    except Exception as e:
        logger.error(f"Error in ML processing: {e}")
        # TODO: Update processing status in database to 'failed'


async def download_video_from_storage(video_id: UUID, storage_path: str) -> str:
    """Download video from Supabase storage to local temp file"""
    
    # Create temp directory if not exists
    temp_dir = Path("/tmp/hockey_ml")
    temp_dir.mkdir(exist_ok=True)
    
    local_path = temp_dir / f"{video_id}.mp4"
    
    # Check if already downloaded
    if local_path.exists():
        return str(local_path)
    
    try:
        supabase = get_supabase()
        
        # Download from Supabase storage
        response = supabase.storage.from_('videos').download(storage_path)
        
        # Save to local file
        with open(local_path, 'wb') as f:
            f.write(response)
        
        logger.info(f"Downloaded video to {local_path}")
        return str(local_path)
        
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        raise


async def store_detected_events(
    video_id: UUID,
    org_id: UUID,
    events: List[EventDetection],
    processing_id: str
):
    """Store detected events in database"""
    
    supabase = get_supabase()
    
    # Convert events to database format
    event_records = []
    for event in events:
        event_record = {
            'video_id': str(video_id),
            'org_id': str(org_id),
            'event_type': event.event_type,
            'timestamp_seconds': event.timestamp,
            'confidence_score': event.confidence_score,
            'detection_method': event.metadata.get('source', 'ml'),
            'frame_data': {
                'frame_number': event.frame_number,
                'bounding_boxes': event.bounding_boxes
            },
            'metadata': {
                **event.metadata,
                'processing_id': processing_id
            },
            'verified': False
        }
        event_records.append(event_record)
    
    # Batch insert events
    if event_records:
        result = supabase.table('events').insert(event_records).execute()
        logger.info(f"Stored {len(event_records)} events in database")
    else:
        logger.info("No events to store")


@router.get("/events/{video_id}", response_model=List[EventResponse])
async def get_video_events(
    video_id: UUID,
    confidence_threshold: float = 0.5,
    event_types: Optional[str] = None,
    supabase=Depends(get_supabase)
):
    """Get detected events for a video"""
    
    try:
        # Build query
        query = supabase.table('events').select('*').eq('video_id', str(video_id))
        
        # Apply confidence filter
        query = query.gte('confidence_score', confidence_threshold)
        
        # Apply event type filter if provided
        if event_types:
            types = event_types.split(',')
            query = query.in_('event_type', types)
        
        # Order by timestamp
        query = query.order('timestamp_seconds')
        
        result = query.execute()
        
        if result.data:
            events = []
            for event in result.data:
                try:
                    # Handle org_id that might be string 'default' from old data
                    if event.get('org_id') == 'default':
                        event['org_id'] = '00000000-0000-0000-0000-000000000000'
                    events.append(EventResponse(**event))
                except Exception as e:
                    logger.warning(f"Skipping invalid event: {e}")
                    continue
            return events
        return []
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error fetching events: {error_msg}")
        
        # If it's the infinite recursion error, we need to fix the RLS
        if "infinite recursion" in error_msg:
            logger.error("RLS policy issue detected. Events table needs migration.")
            logger.error("Run the fix_events_rls.sql migration in Supabase")
            return []  # Return empty for now
        
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/verify/{event_id}")
async def verify_event(
    event_id: UUID,
    verified: bool,
    supabase=Depends(get_supabase)
):
    """Mark an event as verified or not verified"""
    
    try:
        # Update event verification status
        result = supabase.table('events').update({
            'verified': verified
        }).eq('id', str(event_id)).execute()
        
        if result.data:
            return ServiceResponse(
                success=True,
                data=result.data[0],
                message=f"Event {'verified' if verified else 'unverified'} successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Event not found")
            
    except Exception as e:
        logger.error(f"Error verifying event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(
    event_id: UUID,
    supabase=Depends(get_supabase)
):
    """Delete a detected event"""
    
    try:
        # Delete event
        result = supabase.table('events').delete().eq('id', str(event_id)).execute()
        
        return ServiceResponse(
            success=True,
            message="Event deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/events/batch", response_model=ServiceResponse)
async def create_batch_events(
    batch: BatchEventCreate,
    supabase=Depends(get_supabase)
):
    """Create multiple events at once"""
    
    try:
        # Convert to database format
        event_records = []
        for event in batch.events:
            event_record = {
                'video_id': str(batch.video_id),
                'org_id': str(batch.org_id),
                'event_type': event.event_type,
                'timestamp_seconds': event.timestamp,
                'confidence_score': event.confidence_score,
                'detection_method': event.source,
                'frame_data': {
                    'frame_number': event.frame_number,
                    'bounding_boxes': event.bounding_boxes
                },
                'metadata': {
                    **event.metadata,
                    'processing_id': batch.processing_id
                },
                'verified': False
            }
            event_records.append(event_record)
        
        # Batch insert
        if event_records:
            result = supabase.table('events').insert(event_records).execute()
            
            return ServiceResponse(
                success=True,
                data={'events_created': len(event_records)},
                message=f"Created {len(event_records)} events"
            )
        else:
            return ServiceResponse(
                success=True,
                data={'events_created': 0},
                message="No events to create"
            )
            
    except Exception as e:
        logger.error(f"Error creating batch events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{processing_id}")
async def get_processing_status(
    processing_id: str,
    supabase=Depends(get_supabase)
):
    """Get status of ML processing job"""
    
    try:
        # Check if any events exist with this processing_id
        result = supabase.table('events').select('count').eq('metadata->>processing_id', processing_id).execute()
        
        if result.data and result.data[0]['count'] > 0:
            return {
                'processing_id': processing_id,
                'status': 'completed',
                'events_detected': result.data[0]['count']
            }
        else:
            # Check if processing is still running (simplified check)
            return {
                'processing_id': processing_id,
                'status': 'processing',
                'events_detected': 0
            }
            
    except Exception as e:
        logger.error(f"Error checking processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))