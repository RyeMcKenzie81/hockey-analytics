from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional
from uuid import UUID, uuid4
import logging
import json
import asyncio

from ..models import VideoResponse, ServiceResponse
from ..database import get_supabase
from ..services.video_processor import VideoProcessor
from ..services.streaming import StreamingService
from supabase import Client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[VideoResponse])
async def list_videos(
    org_id: Optional[UUID] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    supabase: Client = Depends(get_supabase)
):
    """List videos with optional filtering."""
    query = supabase.table('videos').select('*')
    
    if org_id:
        query = query.eq('organization_id', str(org_id))
    if status:
        query = query.eq('status', status)
    
    query = query.range(offset, offset + limit - 1)
    result = query.execute()
    
    return result.data


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    supabase: Client = Depends(get_supabase)
):
    """Get a specific video by ID."""
    result = supabase.table('videos').select('*').eq('id', str(video_id)).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return result.data[0]


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    org_id: str = "default",
    supabase: Client = Depends(get_supabase)
):
    """Upload video and queue for processing"""
    
    # Validate file
    if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        raise HTTPException(400, "Invalid video format")
    
    # Check file size (max 5GB)
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 5 * 1024 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5GB)")
    
    # Generate video ID
    video_id = str(uuid4())
    
    # Create video record in database
    video_data = {
        'id': video_id,
        'organization_id': org_id,
        'filename': file.filename,
        'file_size': file_size,
        'status': 'uploaded'
    }
    
    result = supabase.table('videos').insert(video_data).execute()
    
    # Process upload
    processor = VideoProcessor(supabase)
    try:
        result = await processor.process_upload(file, video_id, org_id)
        return {
            "video_id": video_id,
            "status": "processing",
            "message": "Video uploaded and queued for processing",
            "metadata": result['metadata']
        }
    except Exception as e:
        # Update status on error
        supabase.table('videos').update({'status': 'error'}).eq('id', video_id).execute()
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    start: float = 0,
    end: Optional[float] = None,
    quality: str = "720p",
    range: Optional[str] = Header(None),
    org_id: str = "default",
    supabase: Client = Depends(get_supabase)
):
    """Stream video segment"""
    
    # Verify video exists
    result = supabase.table('videos').select('*').eq('id', video_id).execute()
    if not result.data:
        raise HTTPException(404, "Video not found")
    
    video = result.data[0]
    if video['status'] != 'processed':
        raise HTTPException(400, f"Video is {video['status']}, not processed for streaming")
    
    streaming = StreamingService(supabase)
    return await streaming.stream_video_segment(
        video_id, org_id, start, end, quality, range
    )


@router.get("/{video_id}/hls/{filename:path}")
async def get_hls_file(
    video_id: str,
    filename: str,
    org_id: str = "default",
    supabase: Client = Depends(get_supabase)
):
    """Serve HLS manifest and segment files"""
    
    streaming = StreamingService(supabase)
    return await streaming.get_hls_manifest(video_id, org_id, filename)


@router.post("/upload/init")
async def init_chunked_upload(
    filename: str = Form(...),
    file_size: str = Form(...),
    total_chunks: str = Form(...),
    org_id: str = Form(default="default"),
    supabase: Client = Depends(get_supabase)
):
    """Initialize chunked upload session"""
    
    try:
        # Convert string parameters to correct types
        file_size_int = int(file_size)
        total_chunks_int = int(total_chunks)
    except ValueError:
        raise HTTPException(400, "file_size and total_chunks must be valid integers")
    
    # Generate session and video IDs
    session_id = str(uuid4())
    video_id = str(uuid4())
    
    # Create video record  
    storage_path = f"{org_id}/{video_id}/original.mp4"
    video_data = {
        'id': video_id,
        'organization_id': org_id,  # Keep as text for backwards compatibility
        'filename': filename,
        'original_filename': filename,
        'storage_path': storage_path,
        'file_size_bytes': file_size_int,  # Use correct column name
        'status': 'uploaded',
        'uploaded_at': 'now()',
        'metadata': {
            'session_id': session_id,
            'total_chunks': total_chunks_int,
            'uploaded_chunks': []
        }
    }
    
    supabase.table('videos').insert(video_data).execute()
    
    return {
        "session_id": session_id,
        "video_id": video_id,
        "message": "Upload session initialized"
    }


@router.post("/upload/chunk")
async def upload_chunk(
    session_id: str = Form(...),
    chunk_index: str = Form(...),
    chunk: UploadFile = File(...),
    supabase: Client = Depends(get_supabase)
):
    """Upload a video chunk"""
    
    try:
        chunk_index_int = int(chunk_index)
    except ValueError:
        raise HTTPException(400, "chunk_index must be a valid integer")
    
    # Find video by session ID
    result = supabase.table('videos').select('*').eq('metadata->>session_id', session_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Upload session not found")
    
    video = result.data[0]
    video_id = video['id']
    org_id = video['organization_id']
    
    # Save chunk to temp storage
    chunk_path = f"{org_id}/{video_id}/chunks/chunk_{chunk_index_int:04d}.tmp"
    
    # Upload chunk to Supabase
    chunk_data = await chunk.read()
    supabase.storage.from_('videos').upload(
        chunk_path,
        chunk_data,
        file_options={"content-type": "application/octet-stream", "upsert": "true"}
    )
    
    # Update metadata
    metadata = video.get('metadata', {})
    uploaded_chunks = metadata.get('uploaded_chunks', [])
    uploaded_chunks.append(chunk_index_int)
    metadata['uploaded_chunks'] = uploaded_chunks
    
    supabase.table('videos').update({'metadata': metadata}).eq('id', video_id).execute()
    
    return {"message": f"Chunk {chunk_index_int} uploaded successfully"}


@router.post("/upload/complete")
async def complete_upload(
    session_id: str = Form(...),
    supabase: Client = Depends(get_supabase)
):
    """Complete chunked upload and assemble video"""
    
    # Find video by session ID
    result = supabase.table('videos').select('*').eq('metadata->>session_id', session_id).execute()
    
    if not result.data:
        raise HTTPException(404, "Upload session not found")
    
    video = result.data[0]
    video_id = video['id']
    org_id = video['organization_id']
    metadata = video.get('metadata', {})
    
    # Verify all chunks uploaded
    total_chunks = metadata.get('total_chunks', 0)
    uploaded_chunks = metadata.get('uploaded_chunks', [])
    
    if len(uploaded_chunks) != total_chunks:
        raise HTTPException(400, f"Missing chunks: {total_chunks - len(uploaded_chunks)} chunks not uploaded")
    
    # Assemble chunks into complete video
    processor = VideoProcessor(supabase)
    
    try:
        # Create temp directory for assembly
        import tempfile
        import os
        from pathlib import Path
        
        temp_dir = Path(f"/tmp/videos/{video_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        assembled_path = temp_dir / "assembled.mp4"
        
        # Download and concatenate chunks
        with open(assembled_path, 'wb') as output:
            for i in range(total_chunks):
                chunk_path = f"{org_id}/{video_id}/chunks/chunk_{i:04d}.tmp"
                
                # Download chunk from Supabase
                chunk_data = supabase.storage.from_('videos').download(chunk_path)
                output.write(chunk_data)
        
        # Upload assembled video in smaller parts if it's large
        storage_path = f"{org_id}/{video_id}/original.mp4"
        file_size = assembled_path.stat().st_size
        
        # If file is larger than 50MB, keep it chunked
        if file_size > 50 * 1024 * 1024:
            # For large files, we'll process directly from chunks
            # Mark as ready for processing without re-uploading
            logger.info(f"Large file ({file_size / 1024 / 1024:.2f}MB) - keeping chunked for processing")
            
            # Store metadata about chunks for later processing
            metadata['assembly_complete'] = True
            metadata['file_size'] = file_size
            metadata['storage_type'] = 'chunked'
            metadata['total_chunks'] = total_chunks
            
            # Don't delete chunks - we'll need them for streaming
        else:
            # Small enough to upload directly
            with open(assembled_path, 'rb') as f:
                supabase.storage.from_('videos').upload(
                    storage_path,
                    f,
                    file_options={"content-type": "video/mp4", "upsert": "true"}
                )
            metadata['storage_type'] = 'single'
            
            # Clean up chunks after successful upload
            for i in range(total_chunks):
                chunk_path = f"{org_id}/{video_id}/chunks/chunk_{i:04d}.tmp"
                try:
                    supabase.storage.from_('videos').remove([chunk_path])
                except:
                    pass  # Ignore cleanup errors
        
        # Update status and metadata
        try:
            video_metadata = await processor.get_video_metadata(str(assembled_path))
            metadata.update(video_metadata)  # Merge with existing metadata
        except Exception as e:
            logger.warning(f"Could not extract video metadata: {e}")
            # Provide fallback metadata
            metadata.update({
                'duration': 0,
                'fps': 30,
                'resolution': 'unknown',
                'codec': 'unknown',
                'bitrate': 0,
                'size': file_size
            })
        
        supabase.table('videos').update({
            'status': 'processing',
            'metadata': metadata
        }).eq('id', video_id).execute()
        
        # Process video for HLS only if it's a single file
        if metadata.get('storage_type') == 'single':
            await processor.convert_to_hls(video_id, org_id, str(assembled_path))
        else:
            # For chunked storage, we'll need a different processing approach
            logger.info(f"Video {video_id} stored as chunks - HLS conversion from chunks not yet implemented")
            supabase.table('videos').update({
                'status': 'processed',  # Changed from 'ready' to valid status
                'metadata': metadata
            }).eq('id', video_id).execute()
        
    except Exception as e:
        logger.error(f"Failed to assemble chunks: {e}")
        supabase.table('videos').update({'status': 'failed'}).eq('id', video_id).execute()
        raise HTTPException(500, f"Failed to assemble video: {str(e)}")
    
    return {
        "video_id": video_id,
        "status": "processing",
        "message": "Upload complete, video queued for processing"
    }


@router.websocket("/ws/{video_id}")
async def video_websocket(
    websocket: WebSocket,
    video_id: str
):
    """WebSocket for real-time video processing updates"""
    
    await websocket.accept()
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "video_id": video_id
        })
        
        # In production, this would subscribe to Redis pubsub
        # For now, simulate updates
        while True:
            # Wait for messages or send periodic status
            await asyncio.sleep(5)
            await websocket.send_json({
                "type": "status",
                "video_id": video_id,
                "status": "processing"
            })
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for video {video_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()