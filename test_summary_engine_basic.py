#!/usr/bin/env python3
"""
Basic test script for SummaryEngine functionality (no API key required)
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from summary_engine import (
    SummaryEngine, 
    SummaryMode, 
    ContentType, 
    create_summary_engine
)


def test_summary_engine_basic():
    """Test SummaryEngine basic functionality without API calls"""
    print("🧪 Testing SummaryEngine basic functionality...")
    
    # Create summary engine
    summary_engine = create_summary_engine()
    
    # Test 1: Mode determination
    print("\n📋 Test 1: Mode determination")
    
    # Test content type routing
    test_cases = [
        (ContentType.TELEGRAM_VOICE, "Короткое голосовое сообщение", 30),
        (ContentType.TELEGRAM_VIDEO_NOTE, "Видео заметка", 45),
        (ContentType.TELEGRAM_DOCUMENT, "Длинный документ с много текста", None),
        (ContentType.TELEGRAM_VIDEO, "Видео файл", 720),  # 12 minutes
        (ContentType.UPLOADED_URL, "Внешняя ссылка на контент", None),
    ]
    
    for content_type, description, duration in test_cases:
        mode = summary_engine.determine_mode(content_type, description, duration)
        print(f"  {content_type.value}: {description} ({duration}s) → {mode.value}")
    
    # Test 2: Long text heuristic
    print("\n📋 Test 2: Long text heuristic")
    long_text = "Это очень длинный текст " * 100  # ~2000 words
    mode = summary_engine.determine_mode(ContentType.TEXT_INPUT, long_text)
    print(f"  Long text ({len(long_text.split())} words) → {mode.value}")
    
    # Test 3: Dialog style heuristic
    print("\n📋 Test 3: Dialog style heuristic")
    dialog_text = "Я думаю, что ты прав. Мы должны это сделать. Он сказал, что она согласна. Вы понимаете?"
    mode = summary_engine.determine_mode(ContentType.UPLOADED_URL, dialog_text)
    print(f"  Dialog text → {mode.value}")
    
    # Test 4: Configuration
    print("\n📋 Test 4: Configuration")
    chat_config = summary_engine.configs[SummaryMode.CHAT]
    longform_config = summary_engine.configs[SummaryMode.LONGFORM]
    
    print(f"  CHAT mode: {chat_config.model}, {chat_config.max_tokens} tokens")
    print(f"  LONGFORM mode: {longform_config.model}, {longform_config.max_tokens} tokens")
    
    # Test 5: Fallback responses
    print("\n📋 Test 5: Fallback responses")
    
    fallback_cases = [
        ("", "Empty text"),
        ("шум и музыка", "Noise text"),
        ("Обычный текст для анализа", "Normal text"),
    ]
    
    for text, description in fallback_cases:
        fallback = summary_engine.get_fallback_response(text)
        print(f"  {description}: {fallback[:50]}...")
    
    # Test 6: Feature flag
    print("\n📋 Test 6: Feature flag")
    print(f"  SummaryEngine enabled: {summary_engine.enabled}")
    
    # Test 7: System prompts
    print("\n📋 Test 7: System prompts")
    chat_prompt = summary_engine.system_prompts[SummaryMode.CHAT]
    longform_prompt = summary_engine.system_prompts[SummaryMode.LONGFORM]
    
    print(f"  CHAT prompt length: {len(chat_prompt)} characters")
    print(f"  LONGFORM prompt length: {len(longform_prompt)} characters")
    print(f"  CHAT prompt preview: {chat_prompt[:100]}...")
    print(f"  LONGFORM prompt preview: {longform_prompt[:100]}...")
    
    # Test 8: Configuration updates
    print("\n📋 Test 8: Configuration updates")
    original_tokens = chat_config.max_tokens
    summary_engine.update_config(SummaryMode.CHAT, max_tokens=1200)
    print(f"  Updated CHAT max_tokens: {original_tokens} → {chat_config.max_tokens}")
    
    # Test 9: Enable/disable
    print("\n📋 Test 9: Enable/disable")
    print(f"  Initial state: {summary_engine.enabled}")
    summary_engine.disable()
    print(f"  After disable: {summary_engine.enabled}")
    summary_engine.enable()
    print(f"  After enable: {summary_engine.enabled}")
    
    print("\n✅ SummaryEngine basic tests completed!")


def test_integration_points():
    """Test integration points with existing system"""
    print("\n🧪 Testing integration points...")
    
    # Test 1: Content type mapping
    print("\n📋 Test 1: Content type mapping")
    content_mapping = {
        "voice": ContentType.TELEGRAM_VOICE,
        "video_note": ContentType.TELEGRAM_VIDEO_NOTE,
        "audio": ContentType.TELEGRAM_AUDIO,
        "document": ContentType.TELEGRAM_DOCUMENT,
        "video": ContentType.TELEGRAM_VIDEO,
        "url": ContentType.UPLOADED_URL,
        "text": ContentType.TEXT_INPUT,
    }
    
    for telegram_type, content_type in content_mapping.items():
        mode = content_type.value
        print(f"  {telegram_type} → {content_type.value} → {mode}")
    
    # Test 2: Mode routing logic
    print("\n📋 Test 2: Mode routing logic")
    summary_engine = create_summary_engine()
    
    routing_test_cases = [
        (ContentType.TELEGRAM_VOICE, "Короткое сообщение", 30, "CHAT"),
        (ContentType.TELEGRAM_VIDEO_NOTE, "Видео заметка", 45, "CHAT"),
        (ContentType.TELEGRAM_DOCUMENT, "Документ", None, "LONGFORM"),
        (ContentType.TELEGRAM_VIDEO, "Длинное видео", 900, "LONGFORM"),  # 15 minutes
        (ContentType.UPLOADED_URL, "Внешняя ссылка", None, "LONGFORM"),
    ]
    
    for content_type, text, duration, expected in routing_test_cases:
        mode = summary_engine.determine_mode(content_type, text, duration)
        status = "✅" if mode.value.upper() == expected else "❌"
        print(f"  {status} {content_type.value} ({duration}s) → {mode.value} (expected: {expected})")
    
    print("\n✅ Integration points tests completed!")


def main():
    """Main test function"""
    print("🚀 Starting SummaryEngine basic tests...\n")
    
    # Test basic functionality
    test_summary_engine_basic()
    
    # Test integration points
    test_integration_points()
    
    print("\n🎉 All basic tests completed!")
    print("\n📝 Next steps:")
    print("  1. Set OPENAI_API_KEY environment variable")
    print("  2. Run test_summary_engine.py for full API testing")
    print("  3. Integrate with main.py for production use")


if __name__ == "__main__":
    main() 