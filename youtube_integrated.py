#!/usr/bin/env python3
"""
Integrated YouTube Processor
Combines Data API v3, Dual Fetcher, and SummaryEngine for robust YouTube processing
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from youtube_api_v3 import YouTubeDataAPI, YouTubeMetadata
from youtube_dual_fetcher import YouTubeDualFetcher, FetchResult, CircuitType

logger = logging.getLogger(__name__)


@dataclass
class YouTubeProcessingResult:
    """Complete YouTube processing result"""
    success: bool
    video_id: str
    metadata: Optional[YouTubeMetadata] = None
    content: Optional[FetchResult] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    circuit_used: Optional[CircuitType] = None
    method: str = "unknown"


class YouTubeIntegratedProcessor:
    """Integrated YouTube processor with metadata, content fetching, and summarization"""
    
    def __init__(self, summary_engine=None):
        self.data_api = YouTubeDataAPI()
        self.dual_fetcher = YouTubeDualFetcher()
        self.summary_engine = summary_engine
        
        # Processing statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'metadata_only': 0,
            'full_processing': 0,
            'circuit_a_usage': 0,
            'circuit_b_usage': 0,
            'cache_hits': 0
        }
        
        logger.info("YouTube Integrated Processor initialized")
        logger.info(f"  Data API: {'✅ Available' if self.data_api.available else '❌ Not available'}")
        logger.info(f"  Dual Fetcher: {'✅ Available' if self.dual_fetcher.circuit_a_available else '❌ Not available'}")
        logger.info(f"  Summary Engine: {'✅ Available' if self.summary_engine else '❌ Not available'}")
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        return self.dual_fetcher._extract_video_id(url)
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video"""
        return self.extract_video_id(url) is not None
    
    async def process_youtube_video(self, url: str, generate_summary: bool = True) -> YouTubeProcessingResult:
        """
        Process YouTube video with full pipeline
        
        Args:
            url: YouTube URL
            generate_summary: Whether to generate TLDR summary
            
        Returns:
            Complete processing result
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        video_id = self.extract_video_id(url)
        if not video_id:
            return YouTubeProcessingResult(
                success=False,
                video_id="",
                error="Invalid YouTube URL"
            )
        
        logger.info(f"Processing YouTube video: {video_id}")
        
        # Step 1: Get metadata from Data API v3
        metadata = None
        if self.data_api.available:
            try:
                metadata = self.data_api.get_video_metadata(video_id)
                if metadata:
                    logger.info(f"Got metadata: {metadata.title} ({metadata.duration}s)")
                else:
                    logger.warning(f"Failed to get metadata for {video_id}")
            except Exception as e:
                logger.error(f"Metadata fetch error: {e}")
        
        # Step 2: Fetch content using dual-circuit approach
        content = None
        if self.dual_fetcher.circuit_a_available or self.dual_fetcher.circuit_b_available:
            try:
                content = self.dual_fetcher.fetch_youtube_content(url, prefer_transcript=True)
                
                if content.success:
                    if content.circuit_used == CircuitType.CLOUD:
                        self.stats['circuit_a_usage'] += 1
                    else:
                        self.stats['circuit_b_usage'] += 1
                    
                    logger.info(f"Content fetched via {content.circuit_used.value}: {content.method}")
                else:
                    logger.warning(f"Content fetch failed: {content.error}")
                    
            except Exception as e:
                logger.error(f"Content fetch error: {e}")
        
        # Step 3: Generate summary if requested and content available
        summary = None
        if generate_summary and content and content.success and self.summary_engine:
            try:
                # Determine content type based on duration
                from summary_engine import ContentType
                content_type = ContentType.LONGFORM if content.duration and content.duration > 300 else ContentType.CHAT
                
                # Use text from transcript or prepare for Whisper
                if content.text:
                    summary_result = await self.summary_engine.process_summary(
                        text=content.text,
                        content_type=content_type,
                        duration=content.duration
                    )
                    
                    if summary_result.success:
                        summary = summary_result.summary
                        self.stats['full_processing'] += 1
                        logger.info("Summary generated successfully")
                    else:
                        logger.warning(f"Summary generation failed: {summary_result.error}")
                
            except Exception as e:
                logger.error(f"Summary generation error: {e}")
        
        # Determine success and method
        success = bool(content and content.success)
        method = content.method if content else "metadata_only"
        
        if success:
            self.stats['successful_requests'] += 1
        elif metadata:
            self.stats['metadata_only'] += 1
        
        processing_time = time.time() - start_time
        
        result = YouTubeProcessingResult(
            success=success,
            video_id=video_id,
            metadata=metadata,
            content=content,
            summary=summary,
            processing_time=processing_time,
            circuit_used=content.circuit_used if content else None,
            method=method
        )
        
        logger.info(f"YouTube processing completed: {method} in {processing_time:.2f}s")
        return result
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        fetcher_stats = self.dual_fetcher.get_stats()
        return {
            **self.stats,
            'fetcher_stats': fetcher_stats,
            'data_api_available': self.data_api.available,
            'dual_fetcher_available': self.dual_fetcher.circuit_a_available or self.dual_fetcher.circuit_b_available,
            'summary_engine_available': bool(self.summary_engine)
        }
    
    def cleanup_files(self, result: YouTubeProcessingResult):
        """Clean up any temporary files from processing"""
        if result.content and result.content.file_path:
            self.dual_fetcher.cleanup_file(result.content.file_path)
    
    def format_result_for_bot(self, result: YouTubeProcessingResult) -> str:
        """Format processing result for Telegram bot response"""
        if not result.success:
            return f"""❌ **Ошибка обработки YouTube видео**

**Видео ID:** {result.video_id}
**Ошибка:** {result.error or 'Неизвестная ошибка'}

**Статистика обработки:**
• Время: {result.processing_time:.2f}с
• Метод: {result.method}"""

        # Format successful result
        lines = []
        
        # Header with circuit info
        circuit_name = "Cloud" if result.circuit_used == CircuitType.CLOUD else "Residential"
        lines.append(f"🎥 **YouTube TLDR ({circuit_name})**")
        lines.append("")
        
        # Metadata section
        if result.metadata:
            lines.append(f"**Видео:** {result.metadata.title}")
            lines.append(f"**Автор:** {result.metadata.channel_title}")
            lines.append(f"**Длительность:** {result.metadata.duration//60}:{result.metadata.duration%60:02d} минут")
            lines.append(f"**Просмотры:** {result.metadata.view_count:,}")
        else:
            lines.append(f"**Видео ID:** {result.video_id}")
            if result.content and result.content.duration:
                lines.append(f"**Длительность:** {result.content.duration//60}:{result.content.duration%60:02d} минут")
        
        # Content method
        if result.content:
            method_display = {
                "transcript_api": "Transcript API",
                "yt_dlp": "yt-dlp + Whisper",
                "yt_dlp_residential": "yt-dlp (Residential)"
            }.get(result.content.method, result.content.method)
            
            lines.append(f"**Метод:** {method_display}")
            
            if result.content.text:
                lines.append(f"**Транскрипт:** {len(result.content.text)} символов")
            elif result.content.language:
                lines.append(f"**Язык:** {result.content.language}")
        
        lines.append("")
        
        # Summary section
        if result.summary:
            lines.append(result.summary)
        else:
            lines.append("📝 **Транскрипт получен**")
            lines.append("Используйте команды для детального анализа")
        
        lines.append("")
        lines.append(f"⏱️ Обработано за {result.processing_time:.2f}с")
        
        return "\n".join(lines)


def create_youtube_integrated_processor(summary_engine=None) -> YouTubeIntegratedProcessor:
    """Create integrated YouTube processor instance"""
    return YouTubeIntegratedProcessor(summary_engine) 