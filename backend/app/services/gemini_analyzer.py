import google.generativeai as genai
import json
import numpy as np
import cv2
import base64
from typing import List, Dict, Optional, Any
from io import BytesIO
from PIL import Image
import logging
import asyncio
from dataclasses import dataclass

from .ml_detector import EventDetection

logger = logging.getLogger(__name__)

@dataclass
class GeminiAnalysis:
    """Result from Gemini analysis"""
    verified_events: List[Dict]
    missed_events: List[Dict]
    false_positives: List[str]
    game_context: Dict[str, Any]
    confidence_adjustments: Dict[str, float]

class GeminiAnalyzer:
    """Gemini-powered video analysis for enhancing ML detections"""
    
    def __init__(self, api_key: str):
        """Initialize Gemini analyzer with API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("Initialized Gemini analyzer with Flash 2.0 model")
    
    async def analyze_segment(
        self,
        frames: List[np.ndarray],
        existing_detections: List[EventDetection],
        segment_info: Dict[str, Any]
    ) -> GeminiAnalysis:
        """Analyze video segment using Gemini to enhance ML detections"""
        
        logger.info(f"Analyzing segment with Gemini: {segment_info.get('start_time')}s - {segment_info.get('end_time')}s")
        
        try:
            # Sample frames to reduce token usage
            sampled_frames = self.sample_frames(frames, num_samples=10)
            
            # Convert frames to base64 for Gemini
            frame_images = await self.prepare_frames_for_gemini(sampled_frames)
            
            # Build analysis prompt
            prompt = self.build_analysis_prompt(existing_detections, segment_info)
            
            # Send to Gemini for analysis
            response = await self.call_gemini(prompt, frame_images)
            
            # Parse Gemini response
            analysis = self.parse_gemini_response(response)
            
            logger.info(f"Gemini analysis complete: {len(analysis.verified_events)} verified, {len(analysis.missed_events)} missed")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            # Return empty analysis on error
            return GeminiAnalysis(
                verified_events=[],
                missed_events=[],
                false_positives=[],
                game_context={},
                confidence_adjustments={}
            )
    
    def sample_frames(self, frames: List[np.ndarray], num_samples: int = 10) -> List[np.ndarray]:
        """Sample frames evenly from the segment to reduce processing"""
        if len(frames) <= num_samples:
            return frames
        
        # Calculate indices for even sampling
        indices = np.linspace(0, len(frames) - 1, num_samples, dtype=int)
        return [frames[i] for i in indices]
    
    async def prepare_frames_for_gemini(self, frames: List[np.ndarray]) -> List[Image.Image]:
        """Convert OpenCV frames to PIL Images for Gemini"""
        images = []
        
        for frame in frames:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to reduce token usage (max 720p)
            height, width = rgb_frame.shape[:2]
            if width > 1280:
                scale = 1280 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                rgb_frame = cv2.resize(rgb_frame, (new_width, new_height))
            
            # Convert to PIL Image
            pil_image = Image.fromarray(rgb_frame)
            images.append(pil_image)
        
        return images
    
    def build_analysis_prompt(
        self, 
        existing_detections: List[EventDetection],
        segment_info: Dict[str, Any]
    ) -> str:
        """Build prompt for Gemini analysis"""
        
        # Convert detections to JSON-serializable format
        detections_data = [d.dict() for d in existing_detections]
        
        prompt = f"""You are analyzing hockey game footage. Your task is to verify ML-detected events and identify any missed events.

Video Segment Information:
- Start Time: {segment_info.get('start_time', 0)}s
- End Time: {segment_info.get('end_time', 0)}s
- Duration: {segment_info.get('end_time', 0) - segment_info.get('start_time', 0)}s

Current ML Detections:
{json.dumps(detections_data, indent=2)}

Please analyze the provided frames and:

1. **Verify ML Detections**: For each detected event, determine if it's correct or a false positive
2. **Identify Missed Events**: Look for any hockey events the ML system missed
3. **Provide Game Context**: Describe the game situation (power play, even strength, etc.)
4. **Note Referee Signals**: Identify any referee arm signals or gestures

Focus on these key events:
- **Goals**: Referee points to net, players celebrate, puck in net, center ice faceoff follows
- **Penalties**: Referee raises arm, player goes to penalty box
- **Shots**: Puck directed at goal, goalie makes movement
- **Saves**: Goalie stops the puck
- **Hits**: Player body checks opponent
- **Faceoffs**: Players lined up in circle, referee drops puck
- **Offsides**: Referee raises arm horizontally, play stops
- **Icing**: Referee raises arm, waves it off or calls it

Return your analysis as a JSON object with this structure:
```json
{{
  "verified_events": [
    {{
      "event_type": "goal",
      "timestamp": 15.5,
      "confidence": 0.95,
      "verification_notes": "Clear goal - referee pointing to net, players celebrating"
    }}
  ],
  "missed_events": [
    {{
      "event_type": "shot",
      "timestamp": 12.3,
      "confidence": 0.7,
      "description": "Wrist shot from point, saved by goalie"
    }}
  ],
  "false_positives": ["event_id_1", "event_id_2"],
  "game_context": {{
    "period": "2nd",
    "game_situation": "even_strength",
    "possession_team": "home",
    "notable_players": ["#91 in white jersey", "#30 goalie"]
  }},
  "confidence_adjustments": {{
    "goal_at_15.5": 0.95,
    "penalty_at_22.0": 0.3
  }}
}}
```

Be precise with timestamps and provide confidence scores between 0 and 1."""
        
        return prompt
    
    async def call_gemini(self, prompt: str, images: List[Image.Image]) -> str:
        """Call Gemini API with prompt and images"""
        try:
            # Prepare content list with prompt and images
            content = [prompt] + images
            
            # Generate response
            response = self.model.generate_content(
                content,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,  # Lower temperature for more consistent analysis
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            raise
    
    def parse_gemini_response(self, response_text: str) -> GeminiAnalysis:
        """Parse Gemini response into structured analysis"""
        try:
            # Extract JSON from response
            # Handle case where Gemini includes markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                json_str = response_text.strip()
            
            # Parse JSON
            data = json.loads(json_str)
            
            return GeminiAnalysis(
                verified_events=data.get('verified_events', []),
                missed_events=data.get('missed_events', []),
                false_positives=data.get('false_positives', []),
                game_context=data.get('game_context', {}),
                confidence_adjustments=data.get('confidence_adjustments', {})
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            
            # Return empty analysis on parse error
            return GeminiAnalysis(
                verified_events=[],
                missed_events=[],
                false_positives=[],
                game_context={},
                confidence_adjustments={}
            )
    
    async def enhance_detections(
        self,
        ml_detections: List[EventDetection],
        gemini_analysis: GeminiAnalysis
    ) -> List[EventDetection]:
        """Combine ML detections with Gemini analysis for enhanced results"""
        
        enhanced_events = []
        
        # Update confidence scores based on Gemini verification
        for detection in ml_detections:
            event_key = f"{detection.event_type}_at_{detection.timestamp}"
            
            # Check if Gemini verified this event
            is_verified = any(
                v['timestamp'] == detection.timestamp and v['event_type'] == detection.event_type
                for v in gemini_analysis.verified_events
            )
            
            # Check if marked as false positive
            is_false_positive = event_key in gemini_analysis.false_positives
            
            if is_false_positive:
                # Skip false positives
                logger.info(f"Removing false positive: {event_key}")
                continue
            
            # Adjust confidence based on Gemini analysis
            if event_key in gemini_analysis.confidence_adjustments:
                detection.confidence_score = gemini_analysis.confidence_adjustments[event_key]
            elif is_verified:
                # Boost confidence for verified events
                detection.confidence_score = min(1.0, detection.confidence_score * 1.2)
            
            # Add Gemini verification to metadata
            detection.metadata['gemini_verified'] = is_verified
            
            enhanced_events.append(detection)
        
        # Add missed events detected by Gemini
        for missed in gemini_analysis.missed_events:
            new_event = EventDetection(
                event_type=missed['event_type'],
                timestamp=missed['timestamp'],
                confidence_score=missed.get('confidence', 0.6),
                frame_number=int(missed['timestamp'] * 30),  # Estimate frame number
                metadata={
                    'source': 'gemini',
                    'description': missed.get('description', ''),
                    'gemini_detected': True
                }
            )
            enhanced_events.append(new_event)
        
        # Sort events by timestamp
        enhanced_events.sort(key=lambda e: e.timestamp)
        
        logger.info(f"Enhanced detections: {len(enhanced_events)} total events")
        
        return enhanced_events
    
    async def analyze_full_video(
        self,
        video_id: str,
        video_path: str,
        ml_detections: List[EventDetection],
        segment_duration: float = 30.0
    ) -> List[EventDetection]:
        """Analyze full video by processing segments"""
        
        logger.info(f"Starting full video analysis for {video_id}")
        
        all_enhanced_events = []
        
        # Group detections by segment
        segments = self.group_detections_by_segment(ml_detections, segment_duration)
        
        for segment_start, segment_detections in segments.items():
            segment_end = segment_start + segment_duration
            
            # Extract frames for this segment
            frames = await self.extract_segment_frames(
                video_path, 
                segment_start, 
                segment_end
            )
            
            if not frames:
                continue
            
            # Analyze segment with Gemini
            segment_info = {
                'start_time': segment_start,
                'end_time': segment_end,
                'video_id': video_id
            }
            
            analysis = await self.analyze_segment(
                frames,
                segment_detections,
                segment_info
            )
            
            # Enhance detections with Gemini analysis
            enhanced = await self.enhance_detections(
                segment_detections,
                analysis
            )
            
            all_enhanced_events.extend(enhanced)
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(1)
        
        logger.info(f"Full video analysis complete: {len(all_enhanced_events)} total events")
        
        return all_enhanced_events
    
    def group_detections_by_segment(
        self,
        detections: List[EventDetection],
        segment_duration: float
    ) -> Dict[float, List[EventDetection]]:
        """Group detections into time segments"""
        segments = {}
        
        for detection in detections:
            segment_start = (detection.timestamp // segment_duration) * segment_duration
            
            if segment_start not in segments:
                segments[segment_start] = []
            
            segments[segment_start].append(detection)
        
        return segments
    
    async def extract_segment_frames(
        self,
        video_path: str,
        start_time: float,
        end_time: float,
        fps: float = 30.0
    ) -> List[np.ndarray]:
        """Extract frames from video segment"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Set position to start time
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            # Read frames until end time
            current_time = start_time
            while current_time < end_time:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frames.append(frame)
                current_time += 1.0 / fps
            
            cap.release()
            
        except Exception as e:
            logger.error(f"Error extracting segment frames: {e}")
        
        return frames