#!/usr/bin/env python3
"""
Test YouTube Hybrid Processor
Tests both transcript API and yt-dlp functionality
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_hybrid import create_youtube_hybrid_processor


def test_youtube_hybrid_processor():
    """Test YouTube hybrid processor functionality"""
    
    print("🧪 Testing YouTube Hybrid Processor")
    print("=" * 50)
    
    # Create processor
    processor = create_youtube_hybrid_processor()
    
    print(f"📊 Processor Status:")
    print(f"  • Transcript API: {'✅ Available' if processor.transcript_api_available else '❌ Not available'}")
    print(f"  • yt-dlp: {'✅ Available' if processor.yt_dlp_available else '❌ Not available'}")
    print()
    
    # Test URL extraction
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
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
    
    # Test transcript API (if available)
    if processor.transcript_api_available:
        print("📝 Testing Transcript API:")
        test_video_id = "dQw4w9WgXcQ"  # Rick Roll - should have subtitles
        
        try:
            transcript_result = processor.get_transcript_via_api(test_video_id)
            if transcript_result:
                print(f"  ✅ Successfully got transcript for {test_video_id}")
                print(f"    Duration: {transcript_result['duration']}s")
                print(f"    Language: {transcript_result['language']}")
                print(f"    Text length: {len(transcript_result['text'])} chars")
                print(f"    Segments: {len(transcript_result['segments'])}")
            else:
                print(f"  ❌ Failed to get transcript for {test_video_id}")
        except Exception as e:
            print(f"  ❌ Error getting transcript: {e}")
        print()
    
    # Test yt-dlp (if available)
    if processor.yt_dlp_available:
        print("📥 Testing yt-dlp download:")
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        try:
            download_result = processor.download_video_via_ytdlp(test_url, max_duration=60)  # 1 minute max for testing
            if download_result:
                file_path, video_info = download_result
                print(f"  ✅ Successfully downloaded video")
                print(f"    Title: {video_info['title']}")
                print(f"    Duration: {video_info['duration']}s")
                print(f"    Uploader: {video_info['uploader']}")
                print(f"    File: {file_path}")
                
                # Clean up
                processor.cleanup_file(file_path)
                print(f"    ✅ Cleaned up file")
            else:
                print(f"  ❌ Failed to download video")
        except Exception as e:
            print(f"  ❌ Error downloading video: {e}")
        print()
    
    # Test hybrid processing
    print("🔄 Testing hybrid processing:")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        result = processor.process_youtube_video(test_url, prefer_transcript=True)
        print(f"  Result: {result['success']}")
        if result['success']:
            print(f"    Method: {result['method']}")
            print(f"    Video ID: {result['video_id']}")
            
            if result['method'] == 'transcript_api':
                print(f"    Duration: {result['duration']}s")
                print(f"    Language: {result['language']}")
                print(f"    Text length: {len(result['text'])} chars")
            elif result['method'] == 'yt_dlp':
                print(f"    Title: {result['video_info']['title']}")
                print(f"    Duration: {result['video_info']['duration']}s")
                print(f"    Needs Whisper: {result['needs_whisper']}")
                
                # Clean up if file was downloaded
                if 'file_path' in result:
                    processor.cleanup_file(result['file_path'])
                    print(f"    ✅ Cleaned up file")
        else:
            print(f"    Error: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"  ❌ Error in hybrid processing: {e}")
    
    print()
    print("✅ YouTube Hybrid Processor test completed!")


if __name__ == "__main__":
    test_youtube_hybrid_processor() 