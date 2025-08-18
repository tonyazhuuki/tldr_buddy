#!/usr/bin/env python3
"""
YouTube Video Processor
Handles YouTube video analysis and TLDR generation
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    logging.warning("YouTube Transcript API not available")

logger = logging.getLogger(__name__)


@dataclass
class YouTubeVideoInfo:
    """YouTube video information"""
    video_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    upload_date: Optional[str] = None
    channel: Optional[str] = None


@dataclass
class YouTubeTranscript:
    """YouTube transcript data"""
    text: str
    language: str
    duration: int
    segments: List[Dict]
    success: bool
    error_message: Optional[str] = None


class YouTubeProcessor:
    """Process YouTube videos for TLDR generation"""
    
    def __init__(self):
        self.formatter = TextFormatter() if YOUTUBE_TRANSCRIPT_AVAILABLE else None
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_transcript(self, video_id: str, languages: List[str] = None) -> YouTubeTranscript:
        """Get transcript for YouTube video"""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            return YouTubeTranscript(
                text="",
                language="",
                duration=0,
                segments=[],
                success=False,
                error_message="YouTube Transcript API not available"
            )
        
        if languages is None:
            languages = ['ru', 'en', 'auto']
        
        try:
            # Try to get transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            
            if not transcript_list:
                return YouTubeTranscript(
                    text="",
                    language="",
                    duration=0,
                    segments=[],
                    success=False,
                    error_message="No transcript available"
                )
            
            # Format transcript
            formatted_text = self.formatter.format_transcript(transcript_list)
            
            # Calculate duration
            duration = 0
            if transcript_list:
                last_segment = transcript_list[-1]
                duration = last_segment.get('start', 0) + last_segment.get('duration', 0)
            
            # Detect language
            language = transcript_list[0].get('language', 'unknown') if transcript_list else 'unknown'
            
            return YouTubeTranscript(
                text=formatted_text,
                language=language,
                duration=int(duration),
                segments=transcript_list,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error getting transcript for video {video_id}: {e}")
            return YouTubeTranscript(
                text="",
                language="",
                duration=0,
                segments=[],
                success=False,
                error_message=str(e)
            )
    
    def get_video_info(self, video_id: str) -> YouTubeVideoInfo:
        """Get basic video information"""
        # For now, return basic info
        # In future, can use yt-dlp for more detailed info
        return YouTubeVideoInfo(
            video_id=video_id,
            title=f"YouTube Video {video_id}",
            description="Video description not available",
            duration=None,
            view_count=None,
            upload_date=None,
            channel=None
        )
    
    def process_youtube_video(self, url: str) -> Dict:
        """Process YouTube video and return TLDR data"""
        video_id = self.extract_video_id(url)
        if not video_id:
            return {
                "success": False,
                "error": "Invalid YouTube URL"
            }
        
        # Get video info
        video_info = self.get_video_info(video_id)
        
        # Get transcript
        transcript = self.get_transcript(video_id)
        
        if not transcript.success:
            return {
                "success": False,
                "video_id": video_id,
                "video_info": video_info,
                "transcript": transcript,
                "error": transcript.error_message
            }
        
        return {
            "success": True,
            "video_id": video_id,
            "video_info": video_info,
            "transcript": transcript,
            "text": transcript.text,
            "duration": transcript.duration,
            "language": transcript.language
        }


def create_youtube_processor() -> YouTubeProcessor:
    """Create YouTube processor instance"""
    return YouTubeProcessor() 