#!/usr/bin/env python3
"""
Get YouTube transcript using yt-dlp (alternative to youtube-transcript-api)
Works in Railway environment
"""

import sys
import json
import tempfile
import os
import yt_dlp

def get_transcript_ytdlp(video_id, lang="ru"):
    """Get transcript for YouTube video using yt-dlp Python API"""
    try:
        print(f"🔍 Getting transcript for {video_id} using yt-dlp Python API...")
        
        # Configure yt-dlp options
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [lang, 'en'],
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
        }
        
        # Create yt-dlp object
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        
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
            print(f"✅ Successfully got transcript for {video_id}")
            print(f"Text length: {len(transcript_text)} chars")
            return transcript_text
        else:
            print(f"❌ No transcript found for video {video_id}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting transcript: {e}")
        return None

def download_and_parse_vtt(url):
    """Download and parse VTT subtitle file"""
    try:
        import requests
        
        # Download VTT file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        vtt_content = response.text
        
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
        
        return ' '.join(text_lines)
        
    except Exception as e:
        print(f"❌ Error parsing VTT: {e}")
        return None

def get_transcript(video_id, lang="ru"):
    """Main function - use only yt-dlp, no fallbacks"""
    try:
        # Use only yt-dlp
        transcript = get_transcript_ytdlp(video_id, lang)
        if transcript:
            return transcript
        else:
            print(f"❌ No transcript available for video {video_id}")
            return None
        
    except Exception as e:
        print(f"❌ Error in get_transcript: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_transcript_ytdlp.py <video_id> [language]")
        sys.exit(1)
    
    video_id = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "ru"
    
    transcript = get_transcript(video_id, lang)
    
    if transcript:
        print(f"\n📝 TRANSCRIPT:")
        print("=" * 50)
        print(transcript)
        print("=" * 50)
        
        # Save to file
        with open(f"transcript_{video_id}.txt", "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"\n💾 Transcript saved to transcript_{video_id}.txt")
    else:
        print("❌ Failed to get transcript") 