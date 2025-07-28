#!/usr/bin/env python3
"""
Hybrid Audio Processor for Telegram Voice-to-Insight Pipeline
Implements format-aware processing with optimization for Telegram native formats
"""

import asyncio
import io
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import json

import aiofiles
import aiofiles.tempfile
from aiogram import Bot
from aiogram.types import File

logger = logging.getLogger(__name__)


@dataclass
class FileMetadata:
    """Metadata container for audio file analysis"""
    file_id: str
    size: int
    format: str
    codec: Optional[str] = None
    is_optimal: bool = False
    estimated_duration: float = 0.0
    file_path: Optional[str] = None


class FormatOptimizer:
    """Smart format detection and routing for optimal processing"""
    
    TELEGRAM_NATIVE_FORMATS = {
        'ogg': {'codec': 'opus', 'optimal': True},
        'oga': {'codec': 'opus', 'optimal': True},  # Alternative OGG extension
        'mp4': {'codec': 'aac', 'optimal': False},
        'mp3': {'codec': 'mp3', 'optimal': False},
        'wav': {'codec': 'pcm', 'optimal': False},
        'm4a': {'codec': 'aac', 'optimal': False}
    }
    
    def __init__(self, bot: Bot):
        self.bot = bot
        
    async def analyze_file_metadata(self, file_id: str) -> FileMetadata:
        """Fast metadata analysis without full download"""
        
        try:
            # Get Telegram file info
            tg_file: File = await self.bot.get_file(file_id)
            
            # Check if file has required info
            if not tg_file.file_path:
                raise ValueError(f"File {file_id} has no file_path")
            if not tg_file.file_size:
                raise ValueError(f"File {file_id} has no file_size")
            
            # Quick format detection from file path
            format_info = self._detect_format_from_path(tg_file.file_path)
            
            # Estimate duration based on file size (rough approximation)
            estimated_duration = self._estimate_duration(tg_file.file_size, format_info['format'])
            
            return FileMetadata(
                file_id=file_id,
                size=tg_file.file_size,
                format=format_info['format'],
                codec=format_info.get('codec'),
                is_optimal=format_info.get('optimal', False),
                estimated_duration=estimated_duration,
                file_path=tg_file.file_path
            )
            
        except Exception as e:
            logger.error(f"Failed to analyze file metadata for {file_id}: {e}")
            # Return minimal metadata for fallback processing
            return FileMetadata(
                file_id=file_id,
                size=0,
                format='unknown',
                is_optimal=False
            )
    
    def _detect_format_from_path(self, file_path: str) -> Dict[str, Any]:
        """Detect audio format from Telegram file path"""
        
        if not file_path:
            return {'format': 'unknown', 'optimal': False}
        
        # Extract extension from file path
        path_obj = Path(file_path)
        extension = path_obj.suffix.lower().lstrip('.')
        
        # Look up format information
        format_info = self.TELEGRAM_NATIVE_FORMATS.get(extension, {
            'format': extension or 'unknown',
            'optimal': False
        })
        
        # Add format field
        result = format_info.copy()
        result['format'] = extension or 'unknown'
        
        logger.debug(f"Detected format: {extension} -> {result}")
        return result
    
    def _estimate_duration(self, file_size: int, format_type: str) -> float:
        """Estimate audio duration based on file size and format"""
        
        if file_size <= 0:
            return 0.0
        
        # Rough estimates based on typical bitrates (in seconds)
        format_estimates = {
            'ogg': file_size / (64 * 1024 / 8),  # 64 kbps for Opus
            'mp3': file_size / (128 * 1024 / 8), # 128 kbps for MP3
            'mp4': file_size / (96 * 1024 / 8),  # 96 kbps for AAC
            'wav': file_size / (1411 * 1024 / 8), # 1411 kbps for 16-bit/44.1kHz PCM
        }
        
        estimated = format_estimates.get(format_type, file_size / (96 * 1024 / 8))
        return max(0.1, min(estimated, 600.0))  # Clamp between 0.1s and 10 minutes


class CacheManager:
    """Redis-based caching for audio processing results"""
    
    def __init__(self, redis_client=None, ttl: int = 3600):
        self.redis = redis_client
        self.ttl = ttl
        self.memory_cache = {}  # Fallback in-memory cache
        
    async def get(self, file_id: str) -> Optional[bytes]:
        """Get cached audio data"""
        
        cache_key = f"audio_cache:{file_id}"
        
        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.debug(f"Cache hit for {file_id}")
                    return cached_data
            except Exception as e:
                logger.warning(f"Redis cache get failed: {e}")
        
        # Fallback to memory cache
        if file_id in self.memory_cache:
            logger.debug(f"Memory cache hit for {file_id}")
            return self.memory_cache[file_id]
        
        return None
    
    async def set(self, file_id: str, audio_data: bytes, ttl: Optional[int] = None) -> None:
        """Cache audio data"""
        
        cache_key = f"audio_cache:{file_id}"
        cache_ttl = ttl or self.ttl
        
        if self.redis:
            try:
                await self.redis.setex(cache_key, cache_ttl, audio_data)
                logger.debug(f"Cached audio data for {file_id} (TTL: {cache_ttl}s)")
                return
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
        
        # Fallback to memory cache (with size limit)
        if len(self.memory_cache) < 10:  # Limit memory cache size
            self.memory_cache[file_id] = audio_data
            logger.debug(f"Memory cached audio data for {file_id}")


class MemoryOptimizedProcessor:
    """Memory-efficient audio processing for containerized deployment"""
    
    MAX_MEMORY_MB = 256  # Container memory limit
    CHUNK_SIZE_MB = 32   # Processing chunk size
    
    def __init__(self, bot: Bot):
        self.bot = bot
        
    async def download_direct(self, file_id: str) -> bytes:
        """Direct download for optimal formats"""
        
        try:
            # Get file info first
            file_info = await self.bot.get_file(file_id)
            
            if not file_info.file_path:
                raise ValueError(f"File {file_id} has no file_path")
            
            # Download file to memory
            file_data = io.BytesIO()
            await self.bot.download_file(file_info.file_path, file_data)
            
            audio_bytes = file_data.getvalue()
            logger.info(f"Downloaded {len(audio_bytes)} bytes for {file_id}")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Direct download failed for {file_id}: {e}")
            raise
    
    async def stream_convert(self, file_id: str, target_format: str = "wav", 
                           sample_rate: int = 16000) -> bytes:
        """Memory-efficient streaming conversion"""
        
        try:
            # Get file info first
            file_info = await self.bot.get_file(file_id)
            
            if not file_info.file_path:
                raise ValueError(f"File {file_id} has no file_path")
            
            # Create temporary file for processing
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as temp_input:
                temp_input_path = temp_input.name
                
                # Download to temporary file
                await self.bot.download_file(file_info.file_path, temp_input_path)
                
            # Convert using ffmpeg (would need ffmpeg-python integration)
            # For now, return the original file data
            # TODO: Implement actual format conversion with ffmpeg
            
            async with aiofiles.open(temp_input_path, 'rb') as f:
                converted_data = await f.read()
            
            # Cleanup temporary file
            try:
                if isinstance(temp_input_path, str):
                    os.unlink(temp_input_path)
            except OSError:
                pass
            
            logger.info(f"Converted {len(converted_data)} bytes for {file_id}")
            return converted_data
            
        except Exception as e:
            logger.error(f"Stream conversion failed for {file_id}: {e}")
            raise


class HybridAudioProcessor:
    """
    Main audio processor implementing hybrid approach with format optimization
    """
    
    def __init__(self, bot: Bot, redis_client=None):
        self.bot = bot
        self.format_optimizer = FormatOptimizer(bot)
        self.cache_manager = CacheManager(redis_client)
        self.memory_processor = MemoryOptimizedProcessor(bot)
        
    async def process_audio(self, file_id: str) -> bytes:
        """
        Main processing entry point implementing hybrid algorithm
        """
        
        start_time = time.time()
        
        try:
            # 1. Quick file analysis (50-100ms)
            file_meta = await self.format_optimizer.analyze_file_metadata(file_id)
            logger.info(f"Analyzed file {file_id}: {file_meta.format}, "
                       f"{file_meta.size} bytes, optimal: {file_meta.is_optimal}")
            
            # 2. Check cache
            cached_result = await self.cache_manager.get(file_id)
            if cached_result:
                logger.info(f"Cache hit for {file_id}")
                return cached_result
            
            # 3. Route to optimal processing path
            if file_meta.is_optimal:
                audio_data = await self._fast_path_process(file_id, file_meta)
            else:
                audio_data = await self._conversion_path_process(file_id, file_meta)
            
            # 4. Cache result
            await self.cache_manager.set(file_id, audio_data, ttl=3600)
            
            processing_time = time.time() - start_time
            logger.info(f"Audio processing completed for {file_id} in {processing_time:.2f}s")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Audio processing failed for {file_id}: {e}")
            raise AudioProcessingError(f"Failed to process audio: {str(e)}")
    
    async def _fast_path_process(self, file_id: str, meta: FileMetadata) -> bytes:
        """Optimized processing for Telegram native formats"""
        
        logger.debug(f"Using fast path for {file_id} ({meta.format})")
        
        # Direct download - no conversion needed
        audio_data = await self.memory_processor.download_direct(file_id)
        
        return audio_data
    
    async def _conversion_path_process(self, file_id: str, meta: FileMetadata) -> bytes:
        """Processing with real-time conversion"""
        
        logger.debug(f"Using conversion path for {file_id} ({meta.format})")
        
        # Stream download with conversion
        converted_audio = await self.memory_processor.stream_convert(
            file_id, 
            target_format="wav",
            sample_rate=16000
        )
        
        return converted_audio


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass


# Example usage and testing
async def main():
    """Test function for development"""
    
    # This would normally be initialized with actual bot and Redis
    # bot = Bot(token="YOUR_TOKEN")
    # processor = HybridAudioProcessor(bot)
    
    print("HybridAudioProcessor module loaded successfully")
    print("Key components:")
    print("- FormatOptimizer: Smart format detection")
    print("- CacheManager: Redis-based result caching")
    print("- MemoryOptimizedProcessor: Efficient audio handling")
    print("- HybridAudioProcessor: Main processing coordinator")


if __name__ == "__main__":
    asyncio.run(main()) 