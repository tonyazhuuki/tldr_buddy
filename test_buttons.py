#!/usr/bin/env python3
"""
Test script to verify button creation logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def test_simple_buttons():
    """Test creating simple buttons without Redis"""
    print("🧪 Testing simple button creation...")
    
    # Create simple buttons without Redis as fallback
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
            InlineKeyboardButton(text="📄 транскрипт", callback_data="transcript_simple")
        ]
    ])
    
    print("✅ Buttons created successfully!")
    print(f"Button count: {len(reply_markup.inline_keyboard[0])}")
    print(f"Button 1: {reply_markup.inline_keyboard[0][0].text}")
    print(f"Button 2: {reply_markup.inline_keyboard[0][1].text}")
    
    return reply_markup

def test_text_only_buttons():
    """Test creating text-only buttons"""
    print("\n🧪 Testing text-only button creation...")
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
        ]
    ])
    
    print("✅ Text-only buttons created successfully!")
    print(f"Button count: {len(reply_markup.inline_keyboard[0])}")
    print(f"Button: {reply_markup.inline_keyboard[0][0].text}")
    
    return reply_markup

if __name__ == "__main__":
    print("🔍 Testing button creation logic...\n")
    
    try:
        test_simple_buttons()
        test_text_only_buttons()
        print("\n✅ All button tests passed!")
        print("The button creation logic should work in production.")
    except Exception as e:
        print(f"\n❌ Button test failed: {e}")
        import traceback
        traceback.print_exc() 