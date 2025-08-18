#!/usr/bin/env python3
"""
Test script to verify that buttons are removed from main.py
"""

import re

def test_no_buttons_in_main():
    """Test that main.py doesn't contain button creation code"""
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for button creation patterns
    button_patterns = [
        r'InlineKeyboardMarkup\(',
        r'InlineKeyboardButton\(',
        r'create_transcript_buttons\(',
        r'reply_markup=.*create_transcript_buttons',
    ]
    
    found_buttons = []
    for pattern in button_patterns:
        matches = re.findall(pattern, content)
        if matches:
            found_buttons.append(f"Pattern '{pattern}' found: {len(matches)} matches")
    
    # Check for command footer
    has_command_footer = 'create_command_footer()' in content
    
    print("=== Button Removal Test ===")
    
    if found_buttons:
        print("❌ BUTTONS STILL FOUND:")
        for item in found_buttons:
            print(f"  - {item}")
        return False
    else:
        print("✅ NO BUTTONS FOUND")
    
    if has_command_footer:
        print("✅ COMMAND FOOTER FOUND")
    else:
        print("❌ COMMAND FOOTER NOT FOUND")
        return False
    
    # Check for YouTube support
    has_youtube = 'extract_youtube_url' in content and 'handle_youtube_url' in content
    
    if has_youtube:
        print("✅ YOUTUBE SUPPORT FOUND")
    else:
        print("❌ YOUTUBE SUPPORT NOT FOUND")
        return False
    
    print("✅ ALL TESTS PASSED - Buttons removed successfully!")
    return True

if __name__ == "__main__":
    test_no_buttons_in_main() 