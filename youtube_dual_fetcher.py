#!/usr/bin/env python3
"""
Dual-Circuit YouTube Fetcher
Circuit A: Cloud worker (default)
Circuit B: Residential exit (fallback)
"""

import os
import time
import logging
import random
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests not available")

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api.formatters import TextFormatter
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False
    logging.warning("YouTube Transcript API not available")

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False
    logging.warning("yt-dlp not available")

logger = logging.getLogger(__name__)


class CircuitType(Enum):
    """Circuit types for fetching"""
    CLOUD = "cloud"      # Circuit A: Cloud worker (Railway, etc.)
    RESIDENTIAL = "residential"  # Circuit B: Residential exit


@dataclass
class FetchResult:
    """Result of YouTube content fetching"""
    success: bool
    circuit_used: CircuitType
    method: str  # "transcript_api", "yt_dlp", "metadata_only"
    video_id: str
    text: Optional[str] = None
    duration: Optional[int] = None
    language: Optional[str] = None
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0


class YouTubeDualFetcher:
    """Dual-circuit YouTube fetcher with automatic failover"""
    
    def __init__(self, 
                 residential_proxy: Optional[str] = None,
                 cloud_proxy: Optional[str] = None,
                 max_retries: int = 3,
                 backoff_base: float = 2.0):
        
        self.residential_proxy = residential_proxy or os.getenv('RESIDENTIAL_PROXY')
        self.cloud_proxy = cloud_proxy or os.getenv('CLOUD_PROXY')
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        
        # Circuit availability
        self.circuit_a_available = YOUTUBE_TRANSCRIPT_AVAILABLE or YT_DLP_AVAILABLE
        self.circuit_b_available = bool(self.residential_proxy)
        
        # Rate limiting and backoff
        self.request_history = {}
        self.circuit_failures = {CircuitType.CLOUD: 0, CircuitType.RESIDENTIAL: 0}
        
        # Cache for fetched content
        self.content_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        logger.info(f"YouTube Dual Fetcher initialized:")
        logger.info(f"  Circuit A (Cloud): {'✅ Available' if self.circuit_a_available else '❌ Not available'}")
        logger.info(f"  Circuit B (Residential): {'✅ Available' if self.circuit_b_available else '❌ Not available'}")
    
    def _get_cache_key(self, video_id: str, circuit: CircuitType) -> str:
        """Generate cache key for video and circuit"""
        return f"youtube_content_{video_id}_{circuit.value}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached content is still valid"""
        if cache_key not in self.content_cache:
            return False
        
        cached_time = self.content_cache[cache_key]['timestamp']
        return time.time() - cached_time < self.cache_ttl
    
    def _should_retry(self, error: str) -> bool:
        """Determine if error is retryable"""
        retryable_errors = [
            '403', '429', 'captcha', 'player_error', 'blocked',
            'timeout', 'connection', 'network'
        ]
        return any(err in error.lower() for err in retryable_errors)
    
    def _exponential_backoff(self, retry_count: int) -> float:
        """Calculate backoff delay with jitter"""
        delay = self.backoff_base ** retry_count
        jitter = random.uniform(0, 0.1 * delay)  # 10% jitter
        return delay + jitter
    
    def _extract_video_id(self, url: str) -> Optional[str]:
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
    
    def _fetch_transcript_cloud(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Fetch transcript using Circuit A (cloud)"""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            return None
        
        try:
            transcript_api = YouTubeTranscriptApi()
            transcript_result = transcript_api.fetch(video_id, languages=['ru', 'en', 'auto'])
            
            if not transcript_result or not transcript_result.snippets:
                return None
            
            # Format transcript
            snippets = transcript_result.snippets
            formatted_text = "\n".join(snippet.text for snippet in snippets)
            
            # Calculate duration
            duration = 0
            if snippets:
                last_snippet = snippets[-1]
                duration = int(last_snippet.start + last_snippet.duration)
            
            return {
                'text': formatted_text,
                'duration': duration,
                'language': transcript_result.language_code or 'unknown',
                'segments': len(snippets)
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            if self._should_retry(error_msg):
                raise e  # Re-raise for retry logic
            logger.warning(f"Non-retryable transcript error: {e}")
            return None
    
    def _fetch_video_cloud(self, url: str, max_duration: int = 600) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Download video using Circuit A (cloud)"""
        if not YT_DLP_AVAILABLE:
            return None
        
        import tempfile
        import os
        
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'best[height<=720]',
                'outtmpl': temp_path,
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Add proxy if configured
            if self.cloud_proxy:
                ydl_opts['proxy'] = self.cloud_proxy
            
            # Download video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                    
                    return temp_path, video_info
                else:
                    logger.error("Downloaded file is empty or missing")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    return None
                    
        except Exception as e:
            error_msg = str(e).lower()
            if self._should_retry(error_msg):
                raise e  # Re-raise for retry logic
            logger.warning(f"Non-retryable download error: {e}")
            return None
    
    def _fetch_residential(self, video_id: str, url: str) -> Optional[Dict[str, Any]]:
        """Fetch using Circuit B (residential proxy)"""
        if not self.residential_proxy:
            return None
        
        try:
            # Use residential proxy for transcript API
            if YOUTUBE_TRANSCRIPT_AVAILABLE:
                # This would require modifying YouTubeTranscriptApi to use proxies
                # For now, we'll use a simple HTTP request approach
                pass
            
            # Use residential proxy for yt-dlp
            if YT_DLP_AVAILABLE:
                import tempfile
                import os
                
                temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
                temp_path = temp_file.name
                temp_file.close()
                
                ydl_opts = {
                    'format': 'best[height<=720]',
                    'outtmpl': temp_path,
                    'quiet': True,
                    'no_warnings': True,
                    'proxy': self.residential_proxy,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    duration = info.get('duration', 0)
                    
                    if duration > 600:  # 10 minutes max
                        os.unlink(temp_path)
                        return None
                    
                    ydl.download([url])
                    
                    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                        return {
                            'method': 'yt_dlp_residential',
                            'file_path': temp_path,
                            'video_info': {
                                'title': info.get('title', 'Unknown'),
                                'duration': duration,
                                'uploader': info.get('uploader', 'Unknown'),
                            }
                        }
                    else:
                        if os.path.exists(temp_path):
                            os.unlink(temp_path)
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"Residential circuit error: {e}")
            return None
    
    def fetch_youtube_content(self, url: str, prefer_transcript: bool = True) -> FetchResult:
        """
        Fetch YouTube content using dual-circuit approach
        
        Args:
            url: YouTube URL
            prefer_transcript: If True, try transcript first, then video download
            
        Returns:
            FetchResult with content and metadata
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            return FetchResult(
                success=False,
                circuit_used=CircuitType.CLOUD,
                method="invalid_url",
                video_id="",
                error="Invalid YouTube URL"
            )
        
        # Check cache first
        cache_key_a = self._get_cache_key(video_id, CircuitType.CLOUD)
        if self._is_cache_valid(cache_key_a):
            cached_data = self.content_cache[cache_key_a]['data']
            return FetchResult(
                success=True,
                circuit_used=CircuitType.CLOUD,
                method=cached_data['method'],
                video_id=video_id,
                text=cached_data.get('text'),
                duration=cached_data.get('duration'),
                language=cached_data.get('language'),
                file_path=cached_data.get('file_path'),
                metadata=cached_data.get('metadata')
            )
        
        # Try Circuit A (Cloud) first
        for retry in range(self.max_retries):
            try:
                logger.info(f"Trying Circuit A (Cloud) for {video_id}, attempt {retry + 1}")
                
                # Try transcript first if preferred
                if prefer_transcript and YOUTUBE_TRANSCRIPT_AVAILABLE:
                    transcript_result = self._fetch_transcript_cloud(video_id)
                    if transcript_result:
                        result = FetchResult(
                            success=True,
                            circuit_used=CircuitType.CLOUD,
                            method="transcript_api",
                            video_id=video_id,
                            text=transcript_result['text'],
                            duration=transcript_result['duration'],
                            language=transcript_result['language'],
                            retry_count=retry
                        )
                        
                        # Cache the result
                        self.content_cache[cache_key_a] = {
                            'data': {
                                'method': result.method,
                                'text': result.text,
                                'duration': result.duration,
                                'language': result.language
                            },
                            'timestamp': time.time()
                        }
                        
                        return result
                
                # Try video download
                if YT_DLP_AVAILABLE:
                    download_result = self._fetch_video_cloud(url)
                    if download_result:
                        file_path, video_info = download_result
                        result = FetchResult(
                            success=True,
                            circuit_used=CircuitType.CLOUD,
                            method="yt_dlp",
                            video_id=video_id,
                            file_path=file_path,
                            metadata=video_info,
                            duration=video_info['duration'],
                            retry_count=retry
                        )
                        
                        # Cache the result
                        self.content_cache[cache_key_a] = {
                            'data': {
                                'method': result.method,
                                'file_path': result.file_path,
                                'metadata': result.metadata,
                                'duration': result.duration
                            },
                            'timestamp': time.time()
                        }
                        
                        return result
                
                # If we get here, Circuit A failed
                self.circuit_failures[CircuitType.CLOUD] += 1
                break
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Circuit A attempt {retry + 1} failed: {error_msg}")
                
                if not self._should_retry(error_msg):
                    break
                
                if retry < self.max_retries - 1:
                    delay = self._exponential_backoff(retry)
                    logger.info(f"Waiting {delay:.2f}s before retry")
                    time.sleep(delay)
        
        # Circuit A failed, try Circuit B (Residential)
        if self.circuit_b_available:
            logger.info(f"Circuit A failed, trying Circuit B (Residential) for {video_id}")
            
            try:
                residential_result = self._fetch_residential(video_id, url)
                if residential_result:
                    result = FetchResult(
                        success=True,
                        circuit_used=CircuitType.RESIDENTIAL,
                        method=residential_result['method'],
                        video_id=video_id,
                        file_path=residential_result.get('file_path'),
                        metadata=residential_result.get('video_info'),
                        duration=residential_result.get('video_info', {}).get('duration'),
                        retry_count=0
                    )
                    
                    # Cache the result
                    cache_key_b = self._get_cache_key(video_id, CircuitType.RESIDENTIAL)
                    self.content_cache[cache_key_b] = {
                        'data': {
                            'method': result.method,
                            'file_path': result.file_path,
                            'metadata': result.metadata,
                            'duration': result.duration
                        },
                        'timestamp': time.time()
                    }
                    
                    return result
                    
            except Exception as e:
                logger.error(f"Circuit B failed: {e}")
                self.circuit_failures[CircuitType.RESIDENTIAL] += 1
        
        # Both circuits failed
        return FetchResult(
            success=False,
            circuit_used=CircuitType.CLOUD,
            method="failed",
            video_id=video_id,
            error="Both circuits failed - YouTube blocking detected",
            retry_count=self.max_retries
        )
    
    def cleanup_file(self, file_path: str):
        """Clean up downloaded file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.error(f"Error cleaning up file {file_path}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fetcher statistics"""
        return {
            'circuit_failures': self.circuit_failures,
            'cache_size': len(self.content_cache),
            'circuit_a_available': self.circuit_a_available,
            'circuit_b_available': self.circuit_b_available
        }


def create_youtube_dual_fetcher() -> YouTubeDualFetcher:
    """Create YouTube dual fetcher instance"""
    return YouTubeDualFetcher() 