import torch
from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import asyncio
from pathlib import Path
import logging
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class EventDetection:
    """Represents a detected event in the video"""
    event_type: str
    timestamp: float
    confidence_score: float
    frame_number: int
    metadata: Dict[str, Any]
    bounding_boxes: Optional[List[Dict]] = None
    
    def dict(self):
        return {
            'event_type': self.event_type,
            'timestamp': self.timestamp,
            'confidence_score': self.confidence_score,
            'frame_number': self.frame_number,
            'metadata': self.metadata,
            'bounding_boxes': self.bounding_boxes
        }

class HockeyDetector:
    """ML detector for hockey game events using hockey-specific YOLO models"""
    
    def __init__(self):
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Initializing HockeyDetector with device: {self.device}")
        
        # Hockey-specific models
        self.hockey_model = None  # Will try to load SimulaMet HockeyAI model
        self.person_model = None  # Fallback to generic YOLOv8
        self.jersey_ocr = None  # TrOCR or EasyOCR for jersey numbers
        
        # Hockey class mappings for SimulaMet model
        self.hockey_classes = {
            'player': 0,
            'puck': 1,
            'referee': 2,
            'goalie': 3
        }
        
        # Event detection patterns
        self.event_patterns = {
            'goal': self.detect_goal_pattern,
            'penalty': self.detect_penalty_pattern,
            'faceoff': self.detect_faceoff_pattern,
            'shot': self.detect_shot_pattern,
            'save': self.detect_save_pattern,
            'hit': self.detect_hit_pattern
        }
        
        # Initialize models lazily
        self._models_loaded = False
    
    async def load_models(self):
        """Load ML models asynchronously"""
        if self._models_loaded:
            return
        
        try:
            logger.info("Loading YOLO models...")
            
            # Try to load hockey-specific model first
            hockey_model_path = Path('models/hockey_yolo.pt')
            if hockey_model_path.exists():
                logger.info("Loading hockey-specific YOLO model...")
                self.hockey_model = YOLO(str(hockey_model_path))
                self.hockey_model.to(self.device)
                logger.info("Hockey-specific model loaded successfully")
            else:
                # Fallback to generic YOLOv8 for person detection
                logger.info("Hockey model not found, using generic YOLOv8x...")
                self.person_model = YOLO('yolov8x.pt')
                self.person_model.to(self.device)
                logger.info("Note: For better results, download hockey-specific model from:")
                logger.info("https://huggingface.co/datasets/SimulaMet-HOST/HockeyAI")
            
            self._models_loaded = True
            logger.info("Models loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    async def process_video_segment(
        self, 
        video_id: str,
        video_path: str,
        start_time: float,
        end_time: float,
        fps: float = 30.0
    ) -> List[EventDetection]:
        """Process a video segment for event detection"""
        
        # Ensure models are loaded
        await self.load_models()
        
        logger.info(f"Processing video segment {video_id}: {start_time}s - {end_time}s")
        
        try:
            # Extract frames from video segment
            frames = await self.extract_frames(video_path, start_time, end_time, fps)
            events = []
            
            # Process frames in batches for efficiency
            batch_size = 30  # Process 1 second at a time for 30fps
            for batch_idx, batch_start in enumerate(range(0, len(frames), batch_size)):
                batch_end = min(batch_start + batch_size, len(frames))
                batch_frames = frames[batch_start:batch_end]
                
                # Calculate timestamp for this batch
                batch_time = start_time + (batch_start / fps)
                
                # Detect players, refs, and objects in batch
                detections = await self.detect_people(batch_frames)
                
                # Detect referee signals
                ref_signals = await self.detect_referee_signals(detections)
                
                # Check for event patterns
                for event_type, detector_func in self.event_patterns.items():
                    event = await detector_func(
                        detections, 
                        ref_signals, 
                        batch_time,
                        batch_start
                    )
                    if event:
                        events.append(event)
                
                # Log progress
                if batch_idx % 10 == 0:
                    logger.info(f"Processed {batch_end}/{len(frames)} frames")
            
            logger.info(f"Detected {len(events)} events in segment")
            return events
            
        except Exception as e:
            logger.error(f"Error processing video segment: {e}")
            raise
    
    async def extract_frames(
        self, 
        video_path: str, 
        start_time: float, 
        end_time: float,
        fps: float
    ) -> List[np.ndarray]:
        """Extract frames from video file"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            # Set video position to start time
            cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
            
            # Calculate frame range
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            total_frames = end_frame - start_frame
            
            frame_count = 0
            while frame_count < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frames.append(frame)
                frame_count += 1
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video")
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            raise
        
        return frames
    
    async def detect_people(self, frames: List[np.ndarray]) -> List[Dict]:
        """Detect players, referees, and pucks in frames"""
        detections = []
        
        # Use hockey model if available, otherwise fallback to person model
        model = self.hockey_model if self.hockey_model else self.person_model
        if not model:
            return detections
        
        try:
            # Run inference on batch
            results = model(frames, stream=True)
            
            for idx, result in enumerate(results):
                frame_detections = {
                    'frame_idx': idx,
                    'players': [],
                    'referees': [],
                    'goalies': []
                }
                
                # Process detections
                if result.boxes is not None:
                    for box in result.boxes:
                        bbox = box.xyxy[0].tolist()
                        confidence = box.conf[0].item()
                        class_id = int(box.cls[0].item())
                        
                        # Map classes based on model type
                        if self.hockey_model:
                            # Hockey-specific model classes
                            if class_id == self.hockey_classes.get('player', 0):
                                person_type = 'player'
                            elif class_id == self.hockey_classes.get('puck', 1):
                                person_type = 'puck'
                            elif class_id == self.hockey_classes.get('referee', 2):
                                person_type = 'referee'
                            elif class_id == self.hockey_classes.get('goalie', 3):
                                person_type = 'goalie'
                            else:
                                person_type = 'unknown'
                        else:
                            # Generic model - only detects persons
                            if class_id == 0:  # Person class in COCO
                                # Try to classify based on appearance
                                person_type = await self.classify_person(
                                    frames[idx], 
                                    bbox
                                )
                            else:
                                continue
                        
                        detection = {
                            'bbox': bbox,
                            'confidence': confidence,
                            'type': person_type,
                            'class_id': class_id
                        }
                        
                        # Organize detections by type
                        if person_type == 'referee':
                            frame_detections['referees'].append(detection)
                        elif person_type == 'goalie':
                            frame_detections['goalies'].append(detection)
                        elif person_type == 'puck':
                            if 'pucks' not in frame_detections:
                                frame_detections['pucks'] = []
                            frame_detections['pucks'].append(detection)
                        elif person_type == 'player':
                            frame_detections['players'].append(detection)
                        else:
                            continue
                
                detections.append(frame_detections)
        
        except Exception as e:
            logger.error(f"Error detecting people: {e}")
        
        return detections
    
    async def classify_person(self, frame: np.ndarray, bbox: List[float]) -> str:
        """Classify detected person as player, referee, or goalie"""
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        person_roi = frame[y1:y2, x1:x2]
        
        # Check for referee (striped jersey)
        if self.is_referee_jersey(person_roi):
            return 'referee'
        
        # Check for goalie (near goal, different equipment)
        if self.is_goalie_position(bbox, frame.shape):
            return 'goalie'
        
        return 'player'
    
    def is_referee_jersey(self, roi: np.ndarray) -> bool:
        """Detect referee by striped jersey pattern"""
        if roi.size == 0:
            return False
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Apply edge detection to find stripes
            edges = cv2.Canny(gray, 50, 150)
            
            # Look for horizontal lines (stripes)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=30)
            
            if lines is not None and len(lines) > 5:
                # Multiple horizontal lines suggest striped pattern
                horizontal_lines = 0
                for line in lines:
                    rho, theta = line[0]
                    # Check if line is mostly horizontal
                    if abs(theta - np.pi/2) < 0.3:
                        horizontal_lines += 1
                
                return horizontal_lines > 3
        
        except Exception as e:
            logger.debug(f"Error checking referee jersey: {e}")
        
        return False
    
    def is_goalie_position(self, bbox: List[float], frame_shape: Tuple) -> bool:
        """Check if person is in goalie position"""
        x1, y1, x2, y2 = bbox
        frame_height, frame_width = frame_shape[:2]
        
        # Check if near edges (goals are typically at frame edges)
        person_center_x = (x1 + x2) / 2
        
        # Goalie typically near left or right edge
        near_left = person_center_x < frame_width * 0.15
        near_right = person_center_x > frame_width * 0.85
        
        # Goalie equipment makes them appear larger
        person_area = (x2 - x1) * (y2 - y1)
        frame_area = frame_width * frame_height
        relative_size = person_area / frame_area
        
        return (near_left or near_right) and relative_size > 0.02
    
    async def detect_referee_signals(self, detections: List[Dict]) -> List[Dict]:
        """Detect referee arm signals and gestures"""
        signals = []
        
        for frame_detection in detections:
            for referee in frame_detection.get('referees', []):
                # Analyze referee pose for signals
                signal = await self.analyze_referee_pose(referee)
                if signal:
                    signals.append({
                        'frame_idx': frame_detection['frame_idx'],
                        'type': signal['type'],
                        'confidence': signal['confidence'],
                        'referee_bbox': referee['bbox']
                    })
        
        return signals
    
    async def analyze_referee_pose(self, referee: Dict) -> Optional[Dict]:
        """Analyze referee pose for specific signals"""
        # TODO: Implement pose detection for referee signals
        # - Arm raised: Penalty
        # - Pointing to net: Goal
        # - Arms crossed: Washout/no goal
        # - Horizontal arms: Offside
        
        # Placeholder implementation
        return None
    
    async def detect_goal_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect goal scoring pattern using multiple signals"""
        
        signals = {
            'referee_pointing_to_net': False,
            'players_celebrating': False,
            'goalie_reaction': False,
            'puck_in_net': False
        }
        
        # Check for referee pointing to net
        for signal in ref_signals:
            if signal.get('type') == 'pointing_to_net':
                signals['referee_pointing_to_net'] = True
                break
        
        # Check for player celebrations
        if await self.detect_celebration(detections):
            signals['players_celebrating'] = True
        
        # Check goalie reaction
        if await self.detect_goalie_reaction(detections):
            signals['goalie_reaction'] = True
        
        # Calculate confidence based on detected signals
        detected_signals = sum(signals.values())
        confidence = detected_signals / len(signals)
        
        # Need at least 2 signals to confirm goal
        if confidence >= 0.5:
            return EventDetection(
                event_type='goal',
                timestamp=timestamp,
                confidence_score=confidence,
                frame_number=frame_offset,
                metadata={'signals': signals}
            )
        
        return None
    
    async def detect_celebration(self, detections: List[Dict]) -> bool:
        """Detect player celebration patterns"""
        for frame_detection in detections:
            players = frame_detection.get('players', [])
            
            # Look for grouping of players (celebration huddle)
            if len(players) >= 3:
                # Check if players are clustered
                bboxes = [p['bbox'] for p in players]
                if self.are_players_clustered(bboxes):
                    return True
        
        return False
    
    def are_players_clustered(self, bboxes: List[List[float]]) -> bool:
        """Check if players are clustered together"""
        if len(bboxes) < 3:
            return False
        
        # Calculate center points
        centers = []
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            centers.append((center_x, center_y))
        
        # Calculate average distance between players
        total_distance = 0
        count = 0
        
        for i in range(len(centers)):
            for j in range(i + 1, len(centers)):
                dist = np.sqrt(
                    (centers[i][0] - centers[j][0])**2 + 
                    (centers[i][1] - centers[j][1])**2
                )
                total_distance += dist
                count += 1
        
        avg_distance = total_distance / count if count > 0 else float('inf')
        
        # Players are clustered if average distance is small
        return avg_distance < 200  # Threshold in pixels
    
    async def detect_goalie_reaction(self, detections: List[Dict]) -> bool:
        """Detect goalie reaction after goal"""
        for frame_detection in detections:
            goalies = frame_detection.get('goalies', [])
            
            for goalie in goalies:
                # TODO: Implement goalie reaction detection
                # Look for goalie looking back at net, head down, etc.
                pass
        
        return False
    
    async def detect_penalty_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect penalty calls"""
        
        # Look for referee with raised arm
        for signal in ref_signals:
            if signal.get('type') == 'arm_raised':
                return EventDetection(
                    event_type='penalty',
                    timestamp=timestamp,
                    confidence_score=signal.get('confidence', 0.7),
                    frame_number=frame_offset,
                    metadata={'signal': 'referee_arm_raised'}
                )
        
        return None
    
    async def detect_faceoff_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect faceoff events"""
        
        # Look for players in faceoff formation
        for frame_detection in detections:
            players = frame_detection.get('players', [])
            
            if self.is_faceoff_formation(players):
                return EventDetection(
                    event_type='faceoff',
                    timestamp=timestamp,
                    confidence_score=0.6,
                    frame_number=frame_offset,
                    metadata={'formation': 'faceoff_circle'}
                )
        
        return None
    
    def is_faceoff_formation(self, players: List[Dict]) -> bool:
        """Check if players are in faceoff formation"""
        if len(players) < 6:  # Need at least 6 players for faceoff
            return False
        
        # TODO: Implement faceoff formation detection
        # Look for circular arrangement of players
        
        return False
    
    async def detect_shot_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect shot on goal"""
        
        # TODO: Implement shot detection
        # Look for puck trajectory toward goal
        
        return None
    
    async def detect_save_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect goalie save"""
        
        # TODO: Implement save detection
        # Look for goalie movement + puck deflection
        
        return None
    
    async def detect_hit_pattern(
        self, 
        detections: List[Dict], 
        ref_signals: List[Dict],
        timestamp: float,
        frame_offset: int
    ) -> Optional[EventDetection]:
        """Detect body check/hit"""
        
        # TODO: Implement hit detection
        # Look for player collision and fall
        
        return None
    
    def batch_frames(self, frames: List[np.ndarray], batch_size: int):
        """Generator to batch frames for processing"""
        for i in range(0, len(frames), batch_size):
            yield frames[i:i + batch_size]