#!/usr/bin/env python3
"""
Test Integrated YouTube Processor
Tests the complete YouTube processing pipeline
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_integrated import create_youtube_integrated_processor
from youtube_api_v3 import create_youtube_data_api
from youtube_dual_fetcher import create_youtube_dual_fetcher


async def test_youtube_integrated_processor():
    """Test the complete YouTube processing pipeline"""
    
    print("🧪 Testing Integrated YouTube Processor")
    print("=" * 60)
    
    # Create processor
    processor = create_youtube_integrated_processor()
    
    print(f"📊 Processor Status:")
    print(f"  • Data API: {'✅ Available' if processor.data_api.available else '❌ Not available'}")
    print(f"  • Dual Fetcher: {'✅ Available' if processor.dual_fetcher.circuit_a_available else '❌ Not available'}")
    print(f"  • Summary Engine: {'✅ Available' if processor.summary_engine else '❌ Not available'}")
    print()
    
    # Test URL extraction
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://example.com/not-youtube"
    ]
    
    print("🔍 Testing URL extraction:")
    for url in test_urls:
        video_id = processor.extract_video_id(url)
        is_youtube = processor.is_youtube_url(url)
        print(f"  • {url}")
        print(f"    Video ID: {video_id}")
        print(f"    Is YouTube: {is_youtube}")
        print()
    
    # Test Data API (if available)
    if processor.data_api.available:
        print("📊 Testing Data API:")
        test_video_id = "dQw4w9WgXcQ"
        
        try:
            metadata = processor.data_api.get_video_metadata(test_video_id)
            if metadata:
                print(f"  ✅ Successfully got metadata for {test_video_id}")
                print(f"    Title: {metadata.title}")
                print(f"    Duration: {metadata.duration}s")
                print(f"    Channel: {metadata.channel_title}")
                print(f"    Views: {metadata.view_count:,}")
                print(f"    Has Captions: {metadata.has_captions}")
            else:
                print(f"  ❌ Failed to get metadata for {test_video_id}")
        except Exception as e:
            print(f"  ❌ Error getting metadata: {e}")
        print()
    
    # Test Dual Fetcher
    if processor.dual_fetcher.circuit_a_available:
        print("🔄 Testing Dual Fetcher:")
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        try:
            result = processor.dual_fetcher.fetch_youtube_content(test_url, prefer_transcript=True)
            print(f"  Result: {result.success}")
            if result.success:
                print(f"    Circuit: {result.circuit_used.value}")
                print(f"    Method: {result.method}")
                print(f"    Duration: {result.duration}s")
                if result.text:
                    print(f"    Text length: {len(result.text)} chars")
                if result.file_path:
                    print(f"    File: {result.file_path}")
                    # Clean up
                    processor.dual_fetcher.cleanup_file(result.file_path)
                    print(f"    ✅ Cleaned up file")
            else:
                print(f"    Error: {result.error}")
        except Exception as e:
            print(f"  ❌ Error in dual fetcher: {e}")
        print()
    
    # Test integrated processing
    print("🎯 Testing Integrated Processing:")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        result = await processor.process_youtube_video(test_url, generate_summary=False)
        print(f"  Success: {result.success}")
        print(f"  Method: {result.method}")
        print(f"  Circuit: {result.circuit_used.value if result.circuit_used else 'None'}")
        print(f"  Processing time: {result.processing_time:.2f}s")
        
        if result.metadata:
            print(f"  Metadata: {result.metadata.title}")
        
        if result.content and result.content.text:
            print(f"  Content: {len(result.content.text)} chars")
        
        # Clean up any files
        processor.cleanup_files(result)
        
    except Exception as e:
        print(f"  ❌ Error in integrated processing: {e}")
    
    print()
    
    # Show statistics
    print("📈 Processing Statistics:")
    stats = processor.get_processing_stats()
    for key, value in stats.items():
        if key != 'fetcher_stats':
            print(f"  • {key}: {value}")
    
    if 'fetcher_stats' in stats:
        print("  • Fetcher Stats:")
        for key, value in stats['fetcher_stats'].items():
            print(f"    - {key}: {value}")
    
    print()
    print("✅ Integrated YouTube Processor test completed!")


if __name__ == "__main__":
    asyncio.run(test_youtube_integrated_processor()) 