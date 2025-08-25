#!/usr/bin/env python3
"""
YouTube Data API v3 Integration
Handles metadata fetching, caching, and rate limiting
"""

import os
import time
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logging.warning("requests not available")

logger = logging.getLogger(__name__)


@dataclass
class YouTubeMetadata:
    """YouTube video metadata from Data API v3"""
    video_id: str
    title: str
    description: str
    duration: int  # seconds
    channel_id: str
    channel_title: str
    published_at: str
    view_count: int
    like_count: int
    category_id: str
    tags: list
    default_language: Optional[str]
    default_audio_language: Optional[str]
    has_captions: bool
    caption_tracks: list
    thumbnail_url: str
    fetched_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'YouTubeMetadata':
        return cls(**data)


class YouTubeDataAPI:
    """YouTube Data API v3 client with caching and rate limiting"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache
        self.rate_limit = {
            'quota_per_day': 10000,
            'quota_used': 0,
            'last_reset': datetime.now().date(),
            'requests_per_second': 1,
            'last_request': 0
        }
        
        if not self.api_key:
            logger.warning("YouTube API key not provided - metadata fetching disabled")
            self.available = False
        else:
            self.available = True
            logger.info("YouTube Data API v3 initialized")
    
    def _get_cache_key(self, video_id: str) -> str:
        """Generate cache key for video"""
        return f"youtube_metadata_{video_id}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key]['timestamp']
        return time.time() - cached_time < self.cache_ttl
    
    def _rate_limit_check(self) -> bool:
        """Check rate limits and wait if necessary"""
        now = time.time()
        
        # Reset daily quota if new day
        if datetime.now().date() > self.rate_limit['last_reset']:
            self.rate_limit['quota_used'] = 0
            self.rate_limit['last_reset'] = datetime.now().date()
        
        # Check daily quota
        if self.rate_limit['quota_used'] >= self.rate_limit['quota_per_day']:
            logger.warning("Daily YouTube API quota exceeded")
            return False
        
        # Rate limiting - max 1 request per second
        time_since_last = now - self.rate_limit['last_request']
        if time_since_last < 1.0:
            time.sleep(1.0 - time_since_last)
        
        self.rate_limit['last_request'] = time.time()
        return True
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make API request with error handling"""
        if not self.available:
            return None
        
        if not self._rate_limit_check():
            return None
        
        try:
            params['key'] = self.api_key
            response = requests.get(f"{self.base_url}/{endpoint}", params=params, timeout=10)
            
            if response.status_code == 200:
                self.rate_limit['quota_used'] += 1  # Estimate quota usage
                return response.json()
            elif response.status_code == 403:
                logger.error("YouTube API quota exceeded or invalid key")
                return None
            elif response.status_code == 404:
                logger.warning(f"Video not found: {params.get('id', 'unknown')}")
                return None
            else:
                logger.error(f"YouTube API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"YouTube API request failed: {e}")
            return None
    
    def get_video_metadata(self, video_id: str) -> Optional[YouTubeMetadata]:
        """Get video metadata from YouTube Data API v3"""
        cache_key = self._get_cache_key(video_id)
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            logger.info(f"Returning cached metadata for {video_id}")
            return YouTubeMetadata.from_dict(self.cache[cache_key]['data'])
        
        # Fetch from API
        logger.info(f"Fetching metadata for video {video_id}")
        
        # Get video details
        video_data = self._make_request('videos', {
            'part': 'snippet,contentDetails,statistics',
            'id': video_id
        })
        
        if not video_data or 'items' not in video_data or not video_data['items']:
            return None
        
        video_info = video_data['items'][0]
        snippet = video_info.get('snippet', {})
        content_details = video_info.get('contentDetails', {})
        statistics = video_info.get('statistics', {})
        
        # Parse duration (ISO 8601 format)
        duration_str = content_details.get('duration', 'PT0S')
        duration = self._parse_duration(duration_str)
        
        # Get caption tracks
        caption_data = self._make_request('captions', {
            'part': 'snippet',
            'videoId': video_id
        })
        
        caption_tracks = []
        if caption_data and 'items' in caption_data:
            caption_tracks = [
                {
                    'language': item['snippet'].get('language', 'unknown'),
                    'trackKind': item['snippet'].get('trackKind', 'unknown')
                }
                for item in caption_data['items']
            ]
        
        # Create metadata object
        metadata = YouTubeMetadata(
            video_id=video_id,
            title=snippet.get('title', 'Unknown'),
            description=snippet.get('description', ''),
            duration=duration,
            channel_id=snippet.get('channelId', ''),
            channel_title=snippet.get('channelTitle', 'Unknown'),
            published_at=snippet.get('publishedAt', ''),
            view_count=int(statistics.get('viewCount', 0)),
            like_count=int(statistics.get('likeCount', 0)),
            category_id=snippet.get('categoryId', ''),
            tags=snippet.get('tags', []),
            default_language=snippet.get('defaultLanguage'),
            default_audio_language=snippet.get('defaultAudioLanguage'),
            has_captions=len(caption_tracks) > 0,
            caption_tracks=caption_tracks,
            thumbnail_url=snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
            fetched_at=datetime.now().isoformat()
        )
        
        # Cache the result
        self.cache[cache_key] = {
            'data': metadata.to_dict(),
            'timestamp': time.time()
        }
        
        logger.info(f"Successfully fetched metadata for {video_id}: {metadata.title}")
        return metadata
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration string to seconds"""
        import re
        
        # Parse PT1H2M3S format
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        return self._make_request('channels', {
            'part': 'snippet,statistics',
            'id': channel_id
        })
    
    def search_videos(self, query: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
        """Search for videos"""
        return self._make_request('search', {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results
        })


def create_youtube_data_api() -> YouTubeDataAPI:
    """Create YouTube Data API v3 instance"""
    return YouTubeDataAPI() 