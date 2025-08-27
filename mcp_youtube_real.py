#!/usr/bin/env python3
"""
Real MCP YouTube Integration for Telegram Bot
Uses actual get_transcript service
"""

import asyncio
import logging
import os
import sys
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Add retry decorator
def with_retry(max_retries=3, delay=1):
    """Decorator for retrying functions with delay"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
            logger.error(f"All {max_retries} attempts failed. Last error: {last_error}")
            raise last_error
        return wrapper
    return decorator

# Import the actual get_transcript function (yt-dlp version only)
try:
    # Log Python path for debugging
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info("Attempting to import get_transcript_ytdlp...")
    
    from get_transcript_ytdlp import get_transcript
    logger.info("✅ Using get_transcript_ytdlp (yt-dlp version)")
except ImportError as e:
    logger.error(f"❌ get_transcript_ytdlp not available: {e}")
    logger.error("Files in current directory:")
    try:
        files = os.listdir('.')
        for f in files:
            logger.error(f"- {f}")
    except Exception as list_error:
        logger.error(f"Failed to list files: {list_error}")
    get_transcript = None


@dataclass
class MCPTranscriptResult:
    """Result of MCP transcript processing"""
    success: bool
    video_id: str
    title: str
    transcript: str
    language: str = "ru"
    error: Optional[str] = None


class RealMCPYouTubeProcessor:
    """Real MCP YouTube processor using get_transcript service"""
    
    def __init__(self):
        logger.info("Initializing RealMCPYouTubeProcessor...")
        try:
            # Check if get_transcript is available
            logger.info("Checking get_transcript availability...")
            if get_transcript is None:
                logger.error("❌ get_transcript is None")
                self.available = False
                return
                
            # Try to import required modules
            logger.info("Importing required modules...")
            import yt_dlp
            import requests
            logger.info(f"✅ Required modules imported: yt-dlp {yt_dlp.version.__version__}, requests {requests.__version__}")
            
            # Set availability
            self.available = True
            logger.info("✅ RealMCPYouTubeProcessor initialized successfully")
        except ImportError as e:
            logger.error(f"❌ Failed to import required modules: {e}")
            self.available = False
        except Exception as e:
            logger.error(f"❌ Error during initialization: {e}")
            logger.exception("Full error details:")
            self.available = False
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)',
            r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video"""
        return self.extract_video_id(url) is not None
    
    async def get_transcript_via_mcp(self, url: str, lang: str = "ru") -> MCPTranscriptResult:
        """
        Get transcript using real get_transcript service
        
        Args:
            url: YouTube URL
            lang: Language preference
            
        Returns:
            MCPTranscriptResult with transcript data
        """
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return MCPTranscriptResult(
                    success=False,
                    video_id="",
                    title="",
                    transcript="",
                    error="Invalid YouTube URL"
                )
            
            logger.info(f"Requesting transcript for video {video_id} via get_transcript service")
            
            # Call the real get_transcript service
            transcript_text = await self._call_real_get_transcript_service(video_id, lang)
            
            if transcript_text:
                return MCPTranscriptResult(
                    success=True,
                    video_id=video_id,
                    title=f"YouTube Video {video_id}",
                    transcript=transcript_text,
                    language=lang
                )
            else:
                return MCPTranscriptResult(
                    success=False,
                    video_id=video_id,
                    title="",
                    transcript="",
                    error="No transcript available via get_transcript service"
                )
                
        except Exception as e:
            logger.error(f"Real get_transcript service error: {e}")
            return MCPTranscriptResult(
                success=False,
                video_id=video_id if 'video_id' in locals() else "",
                title="",
                transcript="",
                error=f"get_transcript service error: {str(e)}"
            )
    
    async def _call_real_get_transcript_service(self, video_id: str, lang: str) -> Optional[str]:
        """
        Call real get_transcript service
        
        This integrates with the actual get_transcript function
        """
        if get_transcript is None:
            logger.error("get_transcript function not available")
            return None
            
        try:
            logger.info(f"Calling get_transcript service for video: {video_id}, lang: {lang}")
            
            # Run get_transcript in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            transcript_text = await loop.run_in_executor(
                None, 
                get_transcript, 
                video_id, 
                lang
            )
            
            if transcript_text:
                logger.info(f"Successfully got transcript for {video_id}, length: {len(transcript_text)} chars")
                return transcript_text
            else:
                logger.warning(f"No transcript returned for {video_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling get_transcript service: {e}")
            return None
    
    async def process_youtube_video(self, url: str, prefer_transcript: bool = True) -> Dict[str, Any]:
        """
        Process YouTube video using real get_transcript service
        
        Args:
            url: YouTube URL
            prefer_transcript: Always True for MCP approach
            
        Returns:
            Dictionary with processing result
        """
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return {
                    "success": False,
                    "error": "Invalid YouTube URL",
                    "method": "get_transcript_failed"
                }
            
            logger.info(f"Processing YouTube video {video_id} via get_transcript service")
            
            # Get transcript via get_transcript service
            transcript_result = await self.get_transcript_via_mcp(url)
            
            if transcript_result.success:
                return {
                    "success": True,
                    "method": "get_transcript_service",
                    "video_id": video_id,
                    "title": transcript_result.title,
                    "text": transcript_result.transcript,
                    "language": transcript_result.language,
                    "duration": self._estimate_duration_from_transcript(transcript_result.transcript)
                }
            else:
                return {
                    "success": False,
                    "error": transcript_result.error,
                    "method": "get_transcript_failed",
                    "video_id": video_id
                }
                
        except Exception as e:
            logger.error(f"Error processing YouTube video via get_transcript service: {e}")
            return {
                "success": False,
                "error": f"get_transcript service processing error: {str(e)}",
                "method": "get_transcript_error"
            }
    
    def _estimate_duration_from_transcript(self, transcript: str) -> int:
        """Estimate video duration from transcript length"""
        # Rough estimation: ~150 words per minute
        words = len(transcript.split())
        estimated_minutes = words / 150
        return int(estimated_minutes * 60)


def create_real_mcp_youtube_processor() -> RealMCPYouTubeProcessor:
    """Create real MCP YouTube processor instance"""
    logger.info("Creating RealMCPYouTubeProcessor...")
    try:
        processor = RealMCPYouTubeProcessor()
        if processor.available:
            logger.info("✅ RealMCPYouTubeProcessor created successfully")
            return processor
        else:
            logger.error("❌ RealMCPYouTubeProcessor created but not available")
            return processor
    except Exception as e:
        logger.error(f"❌ Failed to create RealMCPYouTubeProcessor: {e}")
        logger.exception("Full error details:")
        return None


# Test function
async def test_real_mcp_integration():
    """Test the real MCP integration with get_transcript service"""
    print("🧪 Testing Real MCP Integration with get_transcript service")
    print("=" * 60)
    
    processor = create_real_mcp_youtube_processor()
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=2VtBULINCTc"
    
    print(f"Testing URL: {test_url}")
    
    try:
        result = await processor.process_youtube_video(test_url)
        
        print(f"Processing result: {result}")
        
        if result["success"]:
            print("✅ Real MCP processing successful!")
            print(f"  Method: {result['method']}")
            print(f"  Video ID: {result['video_id']}")
            print(f"  Title: {result.get('title', 'N/A')}")
            print(f"  Language: {result.get('language', 'N/A')}")
            print(f"  Duration: {result.get('duration', 'N/A')} seconds")
            print(f"  Text length: {len(result.get('text', ''))} characters")
            
            # Show first 200 characters of transcript
            transcript = result.get('text', '')
            if transcript:
                print(f"\n📝 First 200 characters of transcript:")
                print("-" * 40)
                print(transcript[:200] + "..." if len(transcript) > 200 else transcript)
                print("-" * 40)
        else:
            print("❌ Real MCP processing failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Method: {result.get('method', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error during real MCP processing: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Real MCP Integration Test Complete")


if __name__ == "__main__":
    # Test the real MCP processor
    asyncio.run(test_real_mcp_integration()) 