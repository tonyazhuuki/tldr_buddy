#!/usr/bin/env python3
"""
Get YouTube transcript using yt-dlp (alternative to youtube-transcript-api)
Works in Railway environment
"""

import sys
import json
import tempfile
import os
import logging
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log environment info
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"yt-dlp version: {yt_dlp.version.__version__}")
try:
    import requests
    logger.info(f"requests version: {requests.__version__}")
except ImportError as e:
    logger.error(f"Failed to import requests: {e}")

def get_transcript_ytdlp(video_id, lang="ru"):
    """Get transcript for YouTube video using yt-dlp Python API"""
    try:
        logger.info(f"🔍 Getting transcript for {video_id} using yt-dlp Python API...")
        
        # Configure yt-dlp options
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang, 'en'],
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        logger.info(f"yt-dlp options: {ydl_opts}")
        
        # Create yt-dlp object
        logger.info("Creating yt-dlp object...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            logger.info(f"Extracting info for video {video_id}...")
            video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            logger.info("Video info extracted successfully")
        
        # Extract transcript
        transcript_text = ""
        
        # Try to get subtitles from video info
        if 'subtitles' in video_info:
            for lang_code, subtitles in video_info['subtitles'].items():
                if lang_code.startswith(lang) or lang_code == 'en':
                    for sub in subtitles:
                        if sub.get('ext') == 'vtt':
                            # Download and parse VTT
                            transcript_text = download_and_parse_vtt(sub['url'])
                            if transcript_text:
                                break
                    if transcript_text:
                        break
        
        # If no subtitles, try auto-generated
        if not transcript_text and 'automatic_captions' in video_info:
            for lang_code, captions in video_info['automatic_captions'].items():
                if lang_code.startswith(lang) or lang_code == 'en':
                    for cap in captions:
                        if cap.get('ext') == 'vtt':
                            transcript_text = download_and_parse_vtt(cap['url'])
                            if transcript_text:
                                break
                    if transcript_text:
                        break
        
        if transcript_text:
            logger.info(f"✅ Successfully got transcript for {video_id}")
            logger.info(f"Text length: {len(transcript_text)} chars")
            return transcript_text
        else:
            logger.warning(f"❌ No transcript found for video {video_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting transcript: {e}")
        logger.exception("Full error details:")
        return None

def download_and_parse_vtt(url):
    """Download and parse VTT subtitle file"""
    try:
        logger.info(f"Downloading VTT from {url}...")
        import requests
        
        # Download VTT file
        logger.info("Making HTTP request...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        logger.info("VTT file downloaded successfully")
        
        vtt_content = response.text
        logger.info(f"VTT content length: {len(vtt_content)} chars")
        
        # Simple VTT to text conversion
        lines = vtt_content.split('\n')
        text_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip VTT headers, timestamps, and empty lines
            if (line and 
                not line.startswith('WEBVTT') and
                not line.startswith('NOTE') and
                not '-->' in line and
                not line.isdigit()):
                text_lines.append(line)
        
        result = ' '.join(text_lines)
        logger.info(f"VTT parsed successfully, extracted text length: {len(result)} chars")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error parsing VTT: {e}")
        logger.exception("Full error details:")
        return None

def get_transcript(video_id, lang="ru"):
    """Main function - use only yt-dlp, no fallbacks"""
    try:
        logger.info(f"Getting transcript for video {video_id} using yt-dlp...")
        # Use only yt-dlp
        transcript = get_transcript_ytdlp(video_id, lang)
        if transcript:
            logger.info(f"✅ Successfully got transcript for video {video_id}")
            return transcript
        else:
            logger.warning(f"❌ No transcript available for video {video_id}")
            return None
        
    except Exception as e:
        logger.error(f"❌ Error in get_transcript: {e}")
        logger.exception("Full error details:")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python get_transcript_ytdlp.py <video_id> [language]")
        sys.exit(1)
    
    video_id = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "ru"
    
    logger.info(f"Running get_transcript_ytdlp.py with video_id={video_id}, lang={lang}")
    transcript = get_transcript(video_id, lang)
    
    if transcript:
        logger.info("\n📝 TRANSCRIPT:")
        logger.info("=" * 50)
        logger.info(transcript)
        logger.info("=" * 50)
        
        # Save to file
        try:
            with open(f"transcript_{video_id}.txt", "w", encoding="utf-8") as f:
                f.write(transcript)
            logger.info(f"💾 Transcript saved to transcript_{video_id}.txt")
        except Exception as e:
            logger.error(f"❌ Failed to save transcript: {e}")
            logger.exception("Full error details:")
    else:
        logger.error("❌ Failed to get transcript") 