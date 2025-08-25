#!/usr/bin/env python3
"""
Debug MCP Bot Integration
Simulates the exact bot workflow to identify the issue
"""

import asyncio
import logging
from mcp_youtube_real import create_real_mcp_youtube_processor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_bot_workflow():
    """Debug the exact bot workflow"""
    print("🔍 Debugging Bot Workflow")
    print("=" * 50)
    
    # Simulate bot startup
    print("1. Bot startup simulation...")
    
    # Initialize MCP processor (like in bot startup)
    try:
        mcp_youtube_processor = create_real_mcp_youtube_processor()
        print(f"✅ MCP processor created: {mcp_youtube_processor is not None}")
        print(f"   Available: {mcp_youtube_processor.available if mcp_youtube_processor else False}")
    except Exception as e:
        print(f"❌ MCP processor creation failed: {e}")
        return
    
    # Test URL (the one that's not working)
    test_url = "https://www.youtube.com/watch?v=1vQ0RpfCqH0"
    user_id = "test_user"
    
    print(f"\n2. Testing with URL: {test_url}")
    
    # Simulate the exact bot logic
    if mcp_youtube_processor and mcp_youtube_processor.available:
        print("✅ MCP processor is available - should use MCP")
        
        # Simulate handle_youtube_url_mcp
        try:
            print("3. Calling MCP processor...")
            result = await mcp_youtube_processor.process_youtube_video(test_url, prefer_transcript=True)
            
            if result["success"]:
                print("✅ MCP processing successful!")
                print(f"   Video ID: {result['video_id']}")
                print(f"   Title: {result.get('title', 'N/A')}")
                print(f"   Language: {result.get('language', 'N/A')}")
                print(f"   Duration: {result.get('duration', 'N/A')} seconds")
                print(f"   Text length: {len(result.get('text', ''))} characters")
                
                # Simulate SummaryEngine call
                print("\n4. Simulating SummaryEngine call...")
                transcript = result.get('text', '')
                duration = result.get('duration', 0)
                
                if transcript and duration:
                    print("✅ Ready for SummaryEngine processing")
                    print(f"   Content Type: LONGFORM")
                    print(f"   Transcript length: {len(transcript)} characters")
                    
                    # Simulate bot response
                    print("\n5. Simulating bot response...")
                    youtube_summary = f"""🎥 **YouTube TLDR (MCP)**

**Видео:** {result.get('title', 'N/A')}
**ID:** {result['video_id']}
**Длительность:** {duration//60}:{duration%60:02d} минут
**Язык:** {result.get('language', 'N/A')}
**Метод:** MCP Transcript Service
**Транскрипт:** {len(transcript)} символов

📋 **TLDR content would be here**"""
                    
                    print("✅ Expected bot response:")
                    print("-" * 40)
                    print(youtube_summary)
                    print("-" * 40)
                else:
                    print("❌ No transcript or duration available")
            else:
                print("❌ MCP processing failed")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                print(f"   Method: {result.get('method', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Error in MCP processing: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ MCP processor not available - would fallback to regular YouTube processor")
    
    print("\n" + "=" * 50)
    print("🎯 Bot Workflow Debug Complete")


if __name__ == "__main__":
    asyncio.run(debug_bot_workflow()) 