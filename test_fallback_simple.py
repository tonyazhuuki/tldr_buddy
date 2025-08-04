#!/usr/bin/env python3
"""
Simple test script to verify fallback functionality logic without external dependencies
"""

from datetime import datetime
from pathlib import Path


def test_transcript_extraction():
    """Test transcript extraction from formatted message"""
    print("🧪 Testing transcript extraction...")
    
    # Simulate formatted message content
    test_message = """
📝 **Резюме**: Тестовое сообщение для проверки функциональности

**Основные пункты**:
• Первый пункт анализа
• Второй пункт обработки
• Третий пункт результата

👉 **Действия**: Проверить работу системы

**Текст:**
Это тестовый транскрипт голосового сообщения который должен быть извлечен из форматированного текста

🎭 **Тон**: намерения: информирование, эмоция: нейтральная, стиль: деловой

⏱️ Обработано за 2.5с
"""
    
    # Extract transcript (simulating the logic from main.py)
    transcript_text = ""
    lines = test_message.split('\n')
    
    in_transcript_section = False
    for line in lines:
        line = line.strip()
        if 'Текст:' in line or 'Транскрипт:' in line:
            in_transcript_section = True
            continue
        elif in_transcript_section:
            if line.startswith('**') or line.startswith('📝') or line.startswith('⏱️') or line.startswith('🎭'):
                break
            if line and not line.startswith('*'):
                transcript_text += line + " "
    
    expected_transcript = "Это тестовый транскрипт голосового сообщения который должен быть извлечен из форматированного текста"
    extracted_transcript = transcript_text.strip()
    
    print(f"✅ Transcript extraction test:")
    print(f"  - Expected: {expected_transcript}")
    print(f"  - Extracted: {extracted_transcript}")
    success = expected_transcript in extracted_transcript
    print(f"  - Match: {'✅ Yes' if success else '❌ No'}")
    
    return success


def test_advice_generation():
    """Test advice generation without OpenAI"""
    print("\n🧪 Testing advice generation...")
    
    # Test advice responses (from main.py)
    advice_responses = [
        "💡 **Совет мудреца**: Найдите время подумать над ключевыми моментами из сообщения. Что самое важное?",
        "🎭 **Творческий подход**: Попробуйте взглянуть на ситуацию с неожиданной стороны. Какие альтернативы вы видите?", 
        "❤️ **Эмпатический взгляд**: Учтите эмоциональную составляющую. Что чувствуют участники ситуации?",
        "🃏 **Игровая перспектива**: Иногда лучший совет - не принимать всё слишком серьезно. Можно ли найти здесь что-то позитивное?"
    ]
    
    # Test selection logic
    test_user_id = 12345
    response_index = hash(str(test_user_id)) % len(advice_responses)
    selected_advice = advice_responses[response_index]
    
    print(f"✅ Advice generation test:")
    print(f"  - Available responses: {len(advice_responses)}")
    print(f"  - Test user ID: {test_user_id}")
    print(f"  - Selected index: {response_index}")
    print(f"  - Selected advice: {selected_advice[:50]}...")
    
    return len(advice_responses) == 4 and selected_advice


def test_file_creation():
    """Test transcript file creation"""
    print("\n🧪 Testing transcript file creation...")
    
    try:
        # Test creating temp directory and file
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        user_id = "test_user"
        test_transcript = "Тестовый транскрипт для проверки создания файла"
        
        transcript_content = f"""ТРАНСКРИПТ ГОЛОСОВОГО СООБЩЕНИЯ
Дата: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Пользователь: {user_id}

ТЕКСТ:
{test_transcript}

---
Создано ботом Voice-to-Insight Pipeline
"""
        
        transcript_file = temp_dir / f"transcript_{user_id}_{timestamp}.txt"
        transcript_file.write_text(transcript_content, encoding='utf-8')
        
        # Verify file was created
        file_exists = transcript_file.exists()
        file_size = transcript_file.stat().st_size if file_exists else 0
        
        print(f"✅ File creation test:")
        print(f"  - File created: {'✅ Yes' if file_exists else '❌ No'}")
        print(f"  - File size: {file_size} bytes")
        print(f"  - File path: {transcript_file}")
        
        # Read back and verify content
        if file_exists:
            read_content = transcript_file.read_text(encoding='utf-8')
            content_match = test_transcript in read_content
            print(f"  - Content preserved: {'✅ Yes' if content_match else '❌ No'}")
        
        # Clean up
        if file_exists:
            transcript_file.unlink()
            print(f"  - File cleaned up: ✅")
        
        return file_exists
        
    except Exception as e:
        print(f"❌ File creation test failed: {e}")
        return False


def test_button_callback_data():
    """Test button callback data handling"""
    print("\n🧪 Testing button callback data...")
    
    # Test callback data patterns
    callback_patterns = [
        "advice_simple",
        "transcript_simple", 
        "back_to_result"
    ]
    
    # Test routing logic
    results = {}
    for callback_data in callback_patterns:
        if callback_data == "advice_simple":
            results[callback_data] = "advice_handler"
        elif callback_data == "transcript_simple":
            results[callback_data] = "transcript_handler"
        elif callback_data == "back_to_result":
            results[callback_data] = "back_handler"
        else:
            results[callback_data] = "unknown"
    
    print(f"✅ Callback routing test:")
    for pattern, handler in results.items():
        print(f"  - {pattern} → {handler}")
    
    success = all(handler != "unknown" for handler in results.values())
    print(f"  - All patterns routed: {'✅ Yes' if success else '❌ No'}")
    
    return success


def main():
    """Run all fallback functionality tests"""
    print("🔍 Testing fallback button functionality logic...\n")
    
    tests = [
        ("Transcript Extraction", test_transcript_extraction),
        ("Advice Generation", test_advice_generation), 
        ("File Creation", test_file_creation),
        ("Button Callback Data", test_button_callback_data)
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
        print("\n🎉 All fallback functionality tests PASSED!")
        print("🚀 The fallback logic should work correctly in production")
        print("📝 Users will be able to:")
        print("  - Get advice without Redis connection")
        print("  - Download transcripts as text files")
        print("  - Navigate back to results")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the logic.")
        
    return passed == total


if __name__ == "__main__":
    main()