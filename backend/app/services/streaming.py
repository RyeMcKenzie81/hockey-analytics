from fastapi import Response, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, AsyncGenerator
import httpx
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class StreamingService:
    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client
    
    async def stream_video_segment(
        self,
        video_id: str,
        org_id: str,
        start_time: float = 0,
        end_time: Optional[float] = None,
        quality: str = "720p",
        range_header: Optional[str] = None
    ) -> StreamingResponse:
        """Stream video segment without loading entire file"""
        
        try:
            # Get video URL from Supabase
            video_url = self.supabase.storage.from_('videos').get_public_url(
                f"videos/{org_id}/{video_id}/original.mp4"
            )
            
            # Handle range requests for seeking
            headers = {}
            if range_header:
                headers['Range'] = range_header
            
            async def generate() -> AsyncGenerator[bytes, None]:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream('GET', video_url, headers=headers) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            yield chunk
            
            # Prepare response headers
            response_headers = {
                'Accept-Ranges': 'bytes',
                'Cache-Control': 'no-cache',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Range'
            }
            
            # Return streaming response
            return StreamingResponse(
                generate(),
                media_type="video/mp4",
                headers=response_headers
            )
            
        except Exception as e:
            logger.error(f"Error streaming video: {e}")
            raise HTTPException(status_code=500, detail="Error streaming video")
    
    async def get_hls_manifest(self, video_id: str, org_id: str, filename: str) -> Response:
        """Serve HLS manifest files"""
        
        try:
            # Get file from Supabase
            file_path = f"videos/{org_id}/{video_id}/hls/{filename}"
            
            # Determine content type
            if filename.endswith('.m3u8'):
                content_type = "application/x-mpegURL"
                cache_control = 'no-cache'  # Don't cache manifests during debugging
            elif filename.endswith('.ts'):
                content_type = "video/MP2T"
                cache_control = 'max-age=3600'  # Longer cache for segments
            else:
                content_type = "application/octet-stream"
                cache_control = 'max-age=3600'
            
            # Get file URL
            file_url = self.supabase.storage.from_('videos').get_public_url(file_path)
            
            # Proxy the file
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(file_url)
                response.raise_for_status()
                
                content = response.content
                
                # For m3u8 files, we might need to rewrite URLs if they're relative
                # But since we're serving through the same base path, relative URLs should work
                # Log the content for debugging
                if filename.endswith('.m3u8'):
                    logger.debug(f"M3U8 content for {filename}: {content[:500].decode('utf-8', errors='ignore')}")
                
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={
                        'Cache-Control': cache_control,
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, OPTIONS',
                        'Access-Control-Allow-Headers': 'Range',
                        'Content-Type': content_type  # Explicitly set Content-Type
                    }
                )
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail="File not found")
            else:
                logger.error(f"Error fetching HLS file: {e}")
                raise HTTPException(status_code=500, detail="Error fetching HLS file")
        except Exception as e:
            logger.error(f"Error serving HLS manifest: {e}")
            raise HTTPException(status_code=500, detail="Error serving HLS file")
    
    async def get_thumbnail(self, video_id: str, org_id: str, timestamp: float = 0) -> Response:
        """Generate or retrieve video thumbnail"""
        
        try:
            # Check if thumbnail exists
            thumbnail_path = f"videos/{org_id}/{video_id}/thumbnails/{int(timestamp)}.jpg"
            
            # Try to get existing thumbnail
            file_url = self.supabase.storage.from_('videos').get_public_url(thumbnail_path)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(file_url)
                if response.status_code == 200:
                    # Thumbnail exists, return it
                    content_response = await client.get(file_url)
                    return Response(
                        content=content_response.content,
                        media_type="image/jpeg",
                        headers={
                            'Cache-Control': 'max-age=86400',  # Cache for 1 day
                            'Access-Control-Allow-Origin': '*'
                        }
                    )
            
            # Thumbnail doesn't exist, return placeholder or generate
            # For now, return 404
            raise HTTPException(status_code=404, detail="Thumbnail not found")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting thumbnail: {e}")
            raise HTTPException(status_code=500, detail="Error retrieving thumbnail")