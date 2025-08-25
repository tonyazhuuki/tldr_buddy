#!/usr/bin/env python3
"""
Get YouTube transcript using yt-dlp (alternative to youtube-transcript-api)
Works in Railway environment
"""

import sys
import json
import subprocess
import tempfile
import os

def get_transcript_ytdlp(video_id, lang="ru"):
    """Get transcript for YouTube video using yt-dlp"""
    try:
        print(f"🔍 Getting transcript for {video_id} using yt-dlp...")
        
        # Use yt-dlp to get transcript
        cmd = [
            "yt-dlp",
            "--write-sub",
            "--write-auto-sub", 
            "--sub-lang", lang,
            "--skip-download",
            "--dump-json",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Run yt-dlp command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"❌ yt-dlp failed: {result.stderr}")
            return None
        
        # Parse JSON output
        try:
            video_info = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("❌ Failed to parse yt-dlp JSON output")
            return None
        
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
            
    except subprocess.TimeoutExpired:
        print(f"❌ yt-dlp timeout for video {video_id}")
        return None
    except Exception as e:
        print(f"❌ Error getting transcript: {e}")
        return None

def download_and_parse_vtt(url):
    """Download and parse VTT subtitle file"""
    try:
        # Download VTT file
        result = subprocess.run(
            ["curl", "-s", url],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        vtt_content = result.stdout
        
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
    """Main function - try yt-dlp first, fallback to youtube-transcript-api"""
    try:
        # Try yt-dlp first
        transcript = get_transcript_ytdlp(video_id, lang)
        if transcript:
            return transcript
        
        # Fallback to youtube-transcript-api if available
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            result = api.fetch(video_id, languages=[lang, 'en', 'auto'])
            
            if result and result.snippets:
                formatted_text = "\n".join(snippet.text for snippet in result.snippets)
                print(f"✅ Got transcript via youtube-transcript-api")
                return formatted_text
        except ImportError:
            print("youtube-transcript-api not available")
        except Exception as e:
            print(f"youtube-transcript-api failed: {e}")
        
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