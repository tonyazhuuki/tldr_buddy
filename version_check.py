#!/usr/bin/env python3
"""
Version Check for Railway Deployment
Simple test to verify if the latest code is deployed
"""

import sys
import os

def check_version():
    """Check if we're running the latest version"""
    print("🔍 Version Check")
    print("=" * 30)
    
    # Check if MCP files exist
    mcp_files = [
        "mcp_youtube_real.py",
        "get_transcript.py"
    ]
    
    for file in mcp_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
    
    # Check if we can import MCP
    try:
        from mcp_youtube_real import create_real_mcp_youtube_processor
        print("✅ MCP import successful")
    except ImportError as e:
        print(f"❌ MCP import failed: {e}")
    
    # Check git commit
    try:
        import subprocess
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            commit_hash = result.stdout.strip()[:8]
            print(f"✅ Git commit: {commit_hash}")
        else:
            print("❌ Git commit check failed")
    except Exception as e:
        print(f"❌ Git check error: {e}")
    
    print("=" * 30)
    print("🎯 Version check complete")


if __name__ == "__main__":
    check_version() 