#!/usr/bin/env python3
"""
Debug MCP YouTube processor for Railway
"""

import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_mcp_processor():
    """Debug MCP YouTube processor step by step"""
    
    logger.info("🔍 Starting MCP processor debug...")
    
    # Step 1: Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Step 2: Check if yt-dlp is available
    logger.info("Step 1: Checking yt-dlp availability...")
    try:
        import yt_dlp
        logger.info(f"✅ yt-dlp imported successfully: {yt_dlp.version.__version__}")
    except ImportError as e:
        logger.error(f"❌ yt-dlp import failed: {e}")
        return False
    
    # Step 3: Check if requests is available
    logger.info("Step 2: Checking requests availability...")
    try:
        import requests
        logger.info(f"✅ requests imported successfully: {requests.__version__}")
    except ImportError as e:
        logger.error(f"❌ requests import failed: {e}")
        return False
    
    # Step 4: Check if get_transcript_ytdlp can be imported
    logger.info("Step 3: Checking get_transcript_ytdlp import...")
    try:
        from get_transcript_ytdlp import get_transcript
        logger.info("✅ get_transcript_ytdlp imported successfully")
    except ImportError as e:
        logger.error(f"❌ get_transcript_ytdlp import failed: {e}")
        return False
    
    # Step 5: Check if mcp_youtube_real can be imported
    logger.info("Step 4: Checking mcp_youtube_real import...")
    try:
        from mcp_youtube_real import create_real_mcp_youtube_processor
        logger.info("✅ mcp_youtube_real imported successfully")
    except ImportError as e:
        logger.error(f"❌ mcp_youtube_real import failed: {e}")
        return False
    
    # Step 6: Create MCP processor
    logger.info("Step 5: Creating MCP processor...")
    try:
        mcp_processor = create_real_mcp_youtube_processor()
        logger.info(f"✅ MCP processor created: available={mcp_processor.available}")
        
        if not mcp_processor.available:
            logger.error("❌ MCP processor not available")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to create MCP processor: {e}")
        logger.exception("Full error details:")
        return False
    
    # Step 7: Test video ID extraction
    logger.info("Step 6: Testing video ID extraction...")
    try:
        test_url = "https://www.youtube.com/watch?v=1vQ0RpfCqH0"
        video_id = mcp_processor.extract_video_id(test_url)
        logger.info(f"✅ Video ID extracted: {video_id}")
        
        if video_id != "1vQ0RpfCqH0":
            logger.error(f"❌ Wrong video ID: {video_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Video ID extraction failed: {e}")
        return False
    
    logger.info("🎉 All MCP debug tests passed!")
    return True

if __name__ == "__main__":
    success = debug_mcp_processor()
    if success:
        print("✅ MCP processor debug completed successfully")
        sys.exit(0)
    else:
        print("❌ MCP processor debug failed")
        sys.exit(1) 