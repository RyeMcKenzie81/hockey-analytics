import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
import aiofiles
import aiofiles.os
import subprocess
import shutil
from fastapi import UploadFile
from supabase import Client
import logging

logger = logging.getLogger(__name__)


class VideoProcessor:
    def __init__(self, supabase_client: Client, redis_client=None):
        self.supabase = supabase_client
        self.redis = redis_client
        self.chunk_duration = 10  # 10-second HLS chunks
        
    async def process_upload(self, file: UploadFile, video_id: str, org_id: str) -> dict:
        """Handle video upload and initiate processing"""
        
        # Create temp file for video processing
        temp_dir = Path(f"/tmp/videos/{video_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / "original.mp4"
        
        try:
            # Stream upload to temp file in chunks
            async with aiofiles.open(temp_path, 'wb') as tmp:
                chunk_size = 1024 * 1024  # 1MB chunks
                while content := await file.read(chunk_size):
                    await tmp.write(content)
            
            # Upload to Supabase Storage
            storage_path = f"videos/{org_id}/{video_id}/original.mp4"
            
            with open(temp_path, 'rb') as f:
                result = self.supabase.storage.from_('videos').upload(
                    storage_path,
                    f,
                    file_options={"content-type": "video/mp4", "upsert": "true"}
                )
            
            # Get video metadata using ffprobe
            metadata = await self.get_video_metadata(str(temp_path))
            
            # Queue for HLS conversion (if Redis available)
            if self.redis:
                await self.redis.lpush(
                    'video:processing:queue',
                    json.dumps({
                        'video_id': video_id,
                        'org_id': org_id,
                        'task': 'convert_hls',
                        'temp_path': str(temp_path),
                        'storage_path': storage_path,
                        'metadata': metadata
                    })
                )
            else:
                # Process immediately if no queue system
                await self.convert_to_hls(video_id, org_id, str(temp_path))
            
            return {
                'video_id': video_id,
                'status': 'processing',
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            # Clean up on error
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            raise
    
    async def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract video metadata using ffprobe"""
        
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"ffprobe failed: {stderr.decode()}")
        
        probe = json.loads(stdout.decode())
        
        # Extract relevant metadata
        video_stream = next(
            (s for s in probe.get('streams', []) if s.get('codec_type') == 'video'),
            {}
        )
        
        # Parse frame rate
        fps_str = video_stream.get('r_frame_rate', '0/1')
        try:
            fps_parts = fps_str.split('/')
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 0
        except:
            fps = 0
        
        metadata = {
            'duration': float(probe.get('format', {}).get('duration', 0)),
            'fps': fps,
            'resolution': f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
            'codec': video_stream.get('codec_name', 'unknown'),
            'bitrate': int(probe.get('format', {}).get('bit_rate', 0)),
            'size': int(probe.get('format', {}).get('size', 0))
        }
        
        return metadata
    
    async def convert_to_hls(self, video_id: str, org_id: str, input_path: str) -> List[str]:
        """Convert video to HLS format for streaming"""
        
        output_dir = Path(f"/tmp/hls/{video_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Quality presets for HLS conversion
            quality_presets = [
                {
                    'name': '1080p',
                    'resolution': '1920x1080',
                    'bitrate': '5000k',
                    'audio_bitrate': '128k',
                    'maxrate': '5350k',
                    'bufsize': '7500k'
                },
                {
                    'name': '720p',
                    'resolution': '1280x720',
                    'bitrate': '2500k',
                    'audio_bitrate': '128k',
                    'maxrate': '2675k',
                    'bufsize': '3750k'
                },
                {
                    'name': '480p',
                    'resolution': '854x480',
                    'bitrate': '1000k',
                    'audio_bitrate': '96k',
                    'maxrate': '1070k',
                    'bufsize': '1500k'
                }
            ]
            
            # Convert each quality level
            playlists = []
            for preset in quality_presets:
                output_name = preset['name']
                
                # Split resolution into width and height for FFmpeg filters
                width, height = preset['resolution'].split('x')
                
                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-vf', f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                    '-c:v', 'h264',
                    '-preset', 'fast',
                    '-b:v', preset['bitrate'],
                    '-maxrate', preset['maxrate'],
                    '-bufsize', preset['bufsize'],
                    '-c:a', 'aac',
                    '-b:a', preset['audio_bitrate'],
                    '-f', 'hls',
                    '-hls_time', str(self.chunk_duration),
                    '-hls_list_size', '0',
                    '-hls_segment_filename', str(output_dir / f'{output_name}_%03d.ts'),
                    str(output_dir / f'{output_name}.m3u8')
                ]
                
                logger.info(f"Converting to {output_name}...")
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"FFmpeg error for {output_name}: {stderr.decode()}")
                    # Continue with other qualities even if one fails
                    continue
                
                playlists.append({
                    'name': output_name,
                    'resolution': preset['resolution'],
                    'bandwidth': int(preset['bitrate'].rstrip('k')) * 1000 + 
                                 int(preset['audio_bitrate'].rstrip('k')) * 1000
                })
            
            # Create master playlist
            if playlists:
                master_content = "#EXTM3U\n#EXT-X-VERSION:3\n"
                for playlist in playlists:
                    width, height = playlist['resolution'].split('x')
                    master_content += f"#EXT-X-STREAM-INF:BANDWIDTH={playlist['bandwidth']},RESOLUTION={playlist['resolution']}\n"
                    master_content += f"{playlist['name']}.m3u8\n"
                
                master_path = output_dir / 'master.m3u8'
                with open(master_path, 'w') as f:
                    f.write(master_content)
                
                # Upload HLS files to Supabase
                hls_paths = await self.upload_hls_files(video_id, org_id, output_dir)
                
                # Update database with HLS URL
                await self.update_video_status(video_id, 'processed', {
                    'hls_manifest': f"videos/{org_id}/{video_id}/hls/master.m3u8"
                })
                
                return hls_paths
            else:
                raise Exception("No HLS streams were successfully created")
                
        finally:
            # Clean up temp files
            if output_dir.exists():
                shutil.rmtree(output_dir)
            
            # Clean up original temp file
            temp_dir = Path(f"/tmp/videos/{video_id}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    async def upload_hls_files(self, video_id: str, org_id: str, hls_dir: Path) -> List[str]:
        """Upload HLS files to Supabase Storage"""
        
        uploaded_paths = []
        
        for file_path in hls_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(hls_dir)
                storage_path = f"videos/{org_id}/{video_id}/hls/{relative_path}"
                
                # Determine content type
                content_type = self.get_content_type(file_path.suffix)
                
                with open(file_path, 'rb') as f:
                    result = self.supabase.storage.from_('videos').upload(
                        storage_path,
                        f,
                        file_options={"content-type": content_type, "upsert": "true"}
                    )
                
                uploaded_paths.append(storage_path)
                logger.info(f"Uploaded: {storage_path}")
        
        return uploaded_paths
    
    def get_content_type(self, suffix: str) -> str:
        """Get content type for file suffix"""
        content_types = {
            '.m3u8': 'application/x-mpegURL',
            '.ts': 'video/MP2T',
            '.mp4': 'video/mp4'
        }
        return content_types.get(suffix, 'application/octet-stream')
    
    async def update_video_status(self, video_id: str, status: str, metadata: dict = None):
        """Update video status in database"""
        
        update_data = {'status': status}
        if metadata:
            update_data['metadata'] = metadata
        
        try:
            # Update the videos table
            result = self.supabase.table('videos').update(update_data).eq('id', video_id).execute()
            
            # Send real-time update if Redis available
            if self.redis:
                await self.redis.publish(
                    f'video:{video_id}:updates',
                    json.dumps({
                        'video_id': video_id,
                        'status': status,
                        'metadata': metadata
                    })
                )
        except Exception as e:
            logger.error(f"Failed to update video status: {e}")