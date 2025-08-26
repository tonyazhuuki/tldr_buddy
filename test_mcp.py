#!/usr/bin/env python3
"""
Test MCP YouTube processor
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_processor():
    """Test MCP YouTube processor"""
    
    logger.info("🧪 Testing MCP YouTube processor...")
    
    # Test 1: Import get_transcript_ytdlp
    logger.info("Test 1: Importing get_transcript_ytdlp...")
    try:
        from get_transcript_ytdlp import get_transcript
        logger.info("✅ get_transcript_ytdlp imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import get_transcript_ytdlp: {e}")
        return False
    
    # Test 2: Import MCP processor
    logger.info("Test 2: Importing MCP processor...")
    try:
        from mcp_youtube_real import create_real_mcp_youtube_processor
        logger.info("✅ MCP processor imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import MCP processor: {e}")
        return False
    
    # Test 3: Create MCP processor
    logger.info("Test 3: Creating MCP processor...")
    try:
        mcp_processor = create_real_mcp_youtube_processor()
        logger.info(f"✅ MCP processor created: available={mcp_processor.available}")
        
        if not mcp_processor.available:
            logger.error("❌ MCP processor not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to create MCP processor: {e}")
        return False
    
    # Test 4: Test video ID extraction
    logger.info("Test 4: Testing video ID extraction...")
    test_url = "https://www.youtube.com/watch?v=1vQ0RpfCqH0"
    video_id = mcp_processor.extract_video_id(test_url)
    logger.info(f"✅ Video ID extracted: {video_id}")
    
    if video_id != "1vQ0RpfCqH0":
        logger.error(f"❌ Wrong video ID: {video_id}")
        return False
    
    # Test 5: Test get_transcript function directly
    logger.info("Test 5: Testing get_transcript function...")
    try:
        transcript = get_transcript("1vQ0RpfCqH0", "ru")
        if transcript:
            logger.info(f"✅ get_transcript works: {len(transcript)} chars")
        else:
            logger.warning("⚠️ get_transcript returned None (video might not have transcript)")
    except Exception as e:
        logger.error(f"❌ get_transcript failed: {e}")
        return False
    
    logger.info("🎉 All MCP tests passed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_mcp_processor())
    if result:
        print("✅ MCP processor is working correctly")
    else:
        print("❌ MCP processor has issues") 