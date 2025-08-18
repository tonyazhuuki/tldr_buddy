#!/usr/bin/env python3
"""
YouTube Video Downloader
Integrates with existing speech pipeline for YouTube video processing
"""

import os
import tempfile
import logging
from typing import Optional, Tuple
from pathlib import Path

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logging.warning("yt-dlp not available")

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """Download YouTube videos for processing with existing speech pipeline"""
    
    def __init__(self):
        self.available = YT_DLP_AVAILABLE
        if not self.available:
            logger.error("yt-dlp not available - YouTube processing disabled")
    
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
    
    def download_video(self, url: str, max_duration: int = 600) -> Optional[Tuple[str, dict]]:
        """
        Download YouTube video for processing
        
        Args:
            url: YouTube URL
            max_duration: Maximum duration in seconds (default: 10 minutes)
            
        Returns:
            Tuple of (file_path, video_info) or None if failed
        """
        if not self.available:
            logger.error("yt-dlp not available")
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
    
    def cleanup_file(self, file_path: str):
        """Clean up downloaded file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")


def create_youtube_downloader() -> YouTubeDownloader:
    """Create YouTube downloader instance"""
    return YouTubeDownloader() 