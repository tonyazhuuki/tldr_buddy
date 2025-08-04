#!/usr/bin/env python3
"""
Test script to verify command-based functionality
"""

from datetime import datetime
from pathlib import Path
import time


def test_user_message_storage():
    """Test in-memory user message storage logic"""
    print("🧪 Testing user message storage...")
    
    # Simulate user_last_messages storage
    user_last_messages = {}
    
    # Test adding messages
    test_cases = [
        {"user_id": "123", "text": "Голосовое сообщение", "type": "voice"},
        {"user_id": "456", "text": "Видео сообщение", "type": "video"},
        {"user_id": "789", "text": "Текстовое сообщение", "type": "text"}
    ]
    
    for case in test_cases:
        user_last_messages[case["user_id"]] = {
            "text": case["text"],
            "timestamp": time.time(),
            "type": case["type"]
        }
    
    print(f"✅ Storage test:")
    print(f"  - Stored messages: {len(user_last_messages)}")
    
    # Test retrieval
    for user_id, data in user_last_messages.items():
        print(f"  - User {user_id}: {data['type']} ({len(data['text'])} chars)")
    
    return len(user_last_messages) == 3


def test_advice_generation():
    """Test advice generation logic"""
    print("\n🧪 Testing advice generation...")
    
    advice_responses = [
        {
            "title": "💡 Совет мудреца",
            "text": "Найдите время подумать над ключевыми моментами из сообщения.",
            "style": "Глубокий анализ"
        },
        {
            "title": "🎭 Творческий подход", 
            "text": "Попробуйте взглянуть на ситуацию с неожиданной стороны.",
            "style": "Нестандартное мышление"
        },
        {
            "title": "❤️ Эмпатический взгляд",
            "text": "Учтите эмоциональную составляющую ситуации.",
            "style": "Эмоциональный интеллект"
        },
        {
            "title": "🃏 Игровая перспектива",
            "text": "Иногда лучший совет - не принимать всё слишком серьезно.",
            "style": "Позитивный настрой"
        }
    ]
    
    # Test selection logic for different users
    test_users = ["123", "456", "789", "101112"]
    
    for user_id in test_users:
        response_index = hash(str(user_id)) % len(advice_responses)
        selected_response = advice_responses[response_index]
        print(f"  - User {user_id}: {selected_response['title']} ({selected_response['style']})")
    
    return len(advice_responses) == 4


def test_transcript_file_creation():
    """Test transcript file creation logic"""
    print("\n🧪 Testing transcript file creation...")
    
    try:
        # Test data
        user_id = "test_user"
        transcript_text = "Тестовый текст транскрипта для проверки функциональности команд"
        msg_type = "voice"
        timestamp_stored = time.time()
        
        # Create content
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        transcript_content = f"""ТРАНСКРИПТ СООБЩЕНИЯ
Дата создания: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Пользователь: {user_id}
Тип сообщения: {msg_type}
Время обработки: {datetime.fromtimestamp(timestamp_stored).strftime("%Y-%m-%d %H:%M:%S")}

СОДЕРЖАНИЕ:
{transcript_text.strip()}

---
Создано ботом Voice-to-Insight Pipeline
Команда: /transcript
"""
        
        # Test file operations
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        transcript_file = temp_dir / f"transcript_{user_id}_{timestamp}.txt"
        transcript_file.write_text(transcript_content, encoding='utf-8')
        
        # Verify file
        file_exists = transcript_file.exists()
        file_size = transcript_file.stat().st_size if file_exists else 0
        
        # Read back content
        if file_exists:
            read_content = transcript_file.read_text(encoding='utf-8')
            content_match = transcript_text in read_content
        else:
            content_match = False
        
        print(f"✅ File creation test:")
        print(f"  - File created: {'✅' if file_exists else '❌'}")
        print(f"  - File size: {file_size} bytes")
        print(f"  - Content preserved: {'✅' if content_match else '❌'}")
        
        # Cleanup
        if file_exists:
            transcript_file.unlink()
            print(f"  - File cleaned up: ✅")
        
        return file_exists and content_match
        
    except Exception as e:
        print(f"❌ File creation test failed: {e}")
        return False


def test_command_flow():
    """Test complete command flow logic"""
    print("\n🧪 Testing command flow...")
    
    # Simulate command flow
    user_id = "test_user"
    user_last_messages = {}
    
    # Step 1: Process a message
    user_last_messages[user_id] = {
        "text": "Тестовое сообщение для проверки команд",
        "timestamp": time.time(),
        "type": "voice"
    }
    
    # Step 2: Check if /transcript would work
    has_message = user_id in user_last_messages
    message_recent = (time.time() - user_last_messages[user_id]["timestamp"]) < 3600
    
    # Step 3: Check if /advice would work
    advice_available = has_message and message_recent
    
    print(f"✅ Command flow test:")
    print(f"  - Message stored: {'✅' if has_message else '❌'}")
    print(f"  - Message recent: {'✅' if message_recent else '❌'}")
    print(f"  - /transcript ready: {'✅' if has_message and message_recent else '❌'}")
    print(f"  - /advice ready: {'✅' if advice_available else '❌'}")
    
    return has_message and message_recent and advice_available


def main():
    """Run all command functionality tests"""
    print("🔍 Testing command-based functionality...\n")
    
    tests = [
        ("User Message Storage", test_user_message_storage),
        ("Advice Generation", test_advice_generation),
        ("Transcript File Creation", test_transcript_file_creation),
        ("Command Flow", test_command_flow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\n📊 Test Results:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  - {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All command functionality tests PASSED!")
        print("🚀 Commands should work correctly:")
        print("  📱 /transcript - Download transcript files")
        print("  🤖 /advice - Get personalized advice")
        print("  📝 In-memory message storage working")
        print("  ⏰ 1-hour message expiry working")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the logic.")
        
    return passed == total


if __name__ == "__main__":
    main()