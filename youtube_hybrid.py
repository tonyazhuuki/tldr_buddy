#!/usr/bin/env python3
"""
Hybrid YouTube Processor
Uses both YouTube Transcript API and yt-dlp for maximum compatibility
"""

import os
import tempfile
import logging
from typing import Optional, Tuple, Dict
from pathlib import Path

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logging.warning("yt-dlp not available")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    logging.warning("YouTube Transcript API not available")
except AttributeError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    logging.warning("YouTube Transcript API import error")

logger = logging.getLogger(__name__)


class YouTubeHybridProcessor:
    """Hybrid YouTube processor - uses both Transcript API and yt-dlp"""
    
    def __init__(self):
        self.yt_dlp_available = YT_DLP_AVAILABLE
        self.transcript_api_available = YOUTUBE_TRANSCRIPT_AVAILABLE
        self.formatter = TextFormatter() if YOUTUBE_TRANSCRIPT_AVAILABLE else None
        
        logger.info(f"YouTube Hybrid Processor: yt-dlp={self.yt_dlp_available}, transcript_api={self.transcript_api_available}")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        import re
        
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
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video"""
        return self.extract_video_id(url) is not None
    
    def get_transcript_via_api(self, video_id: str) -> Optional[Dict]:
        """Get transcript using YouTube Transcript API"""
        if not self.transcript_api_available:
            return None
        
        try:
            # Try to get transcript
            transcript_api = YouTubeTranscriptApi()
            transcript_result = transcript_api.fetch(video_id, languages=['ru', 'en', 'auto'])
            
            if not transcript_result or not transcript_result.snippets:
                return None
            
            # Get snippets and convert to list format for formatter
            snippets = transcript_result.snippets
            transcript_list = []
            for snippet in snippets:
                transcript_list.append({
                    'text': snippet.text,
                    'start': snippet.start,
                    'duration': snippet.duration
                })
            
            # Format transcript - use snippets directly
            formatted_text = "\n".join(snippet.text for snippet in snippets)
            
            # Calculate duration
            duration = 0
            if transcript_list:
                last_segment = transcript_list[-1]
                duration = last_segment['start'] + last_segment['duration']
            
            # Detect language
            language = transcript_result.language_code if transcript_result.language_code else 'unknown'
            
            return {
                'success': True,
                'text': formatted_text,
                'language': language,
                'duration': int(duration),
                'segments': transcript_list,
                'method': 'transcript_api'
            }
            
        except Exception as e:
            logger.warning(f"Transcript API failed for video {video_id}: {e}")
            return None
    
    def download_video_via_ytdlp(self, url: str, max_duration: int = 600) -> Optional[Tuple[str, dict]]:
        """Download video using yt-dlp"""
        if not self.yt_dlp_available:
            return None
        
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[height<=720]',  # Max 720p for processing
                'outtmpl': temp_path,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading YouTube video: {url}")
                
                # Get video info first
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                
                # Check duration limit
                if duration > max_duration:
                    logger.warning(f"Video too long: {duration}s > {max_duration}s")
                    os.unlink(temp_path)
                    return None
                
                # Download video
                ydl.download([url])
                
                # Verify file exists and has content
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    video_info = {
                        'title': info.get('title', 'Unknown'),
                        'duration': duration,
                        'uploader': info.get('uploader', 'Unknown'),
                        'view_count': info.get('view_count', 0),
                        'upload_date': info.get('upload_date', 'Unknown'),
                        'description': info.get('description', '')[:500] + '...' if info.get('description') else ''
                    }
                    
                    logger.info(f"Successfully downloaded: {video_info['title']} ({duration}s)")
                    return temp_path, video_info
                else:
                    logger.error("Downloaded file is empty or missing")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading YouTube video: {e}")
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
    
    def process_youtube_video(self, url: str, prefer_transcript: bool = True) -> Dict:
        """
        Process YouTube video with hybrid approach
        
        Args:
            url: YouTube URL
            prefer_transcript: If True, try transcript API first, then yt-dlp
            
        Returns:
            Processing result dictionary
        """
        video_id = self.extract_video_id(url)
        if not video_id:
            return {
                "success": False,
                "error": "Invalid YouTube URL"
            }
        
        # Try transcript API first if preferred
        if prefer_transcript and self.transcript_api_available:
            transcript_result = self.get_transcript_via_api(video_id)
            if transcript_result:
                logger.info(f"Successfully got transcript via API for video {video_id}")
                return {
                    "success": True,
                    "video_id": video_id,
                    "method": "transcript_api",
                    "text": transcript_result['text'],
                    "duration": transcript_result['duration'],
                    "language": transcript_result['language'],
                    "segments": transcript_result['segments']
                }
        
        # Fallback to yt-dlp download
        if self.yt_dlp_available:
            download_result = self.download_video_via_ytdlp(url)
            if download_result:
                file_path, video_info = download_result
                logger.info(f"Successfully downloaded video via yt-dlp for video {video_id}")
                return {
                    "success": True,
                    "video_id": video_id,
                    "method": "yt_dlp",
                    "file_path": file_path,
                    "video_info": video_info,
                    "needs_whisper": True  # Flag to indicate Whisper processing needed
                }
        
        # Both methods failed
        return {
            "success": False,
            "video_id": video_id,
            "error": "Both transcript API and yt-dlp failed"
        }
    
    def cleanup_file(self, file_path: str):
        """Clean up downloaded file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")


def create_youtube_hybrid_processor() -> YouTubeHybridProcessor:
    """Create YouTube hybrid processor instance"""
    return YouTubeHybridProcessor() 