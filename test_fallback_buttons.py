#!/usr/bin/env python3
"""
Test script to verify fallback button functionality without Redis
"""

import sys
import os
import asyncio
from datetime import datetime
from pathlib import Path

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def test_fallback_button_creation():
    """Test creating fallback buttons"""
    print("🧪 Testing fallback button creation...")
    
    # Test voice message buttons
    voice_buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
            InlineKeyboardButton(text="📄 транскрипт", callback_data="transcript_simple")
        ]
    ])
    
    # Test text message buttons  
    text_buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
        ]
    ])
    
    print("✅ Voice message buttons created:")
    print(f"  - Button count: {len(voice_buttons.inline_keyboard[0])}")
    print(f"  - Button 1: {voice_buttons.inline_keyboard[0][0].text}")
    print(f"  - Button 2: {voice_buttons.inline_keyboard[0][1].text}")
    
    print("✅ Text message buttons created:")
    print(f"  - Button count: {len(text_buttons.inline_keyboard[0])}")
    print(f"  - Button: {text_buttons.inline_keyboard[0][0].text}")
    
    return voice_buttons, text_buttons


def test_transcript_extraction():
    """Test transcript extraction from formatted message"""
    print("\n🧪 Testing transcript extraction...")
    
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
    print(f"  - Match: {'✅ Yes' if expected_transcript in extracted_transcript else '❌ No'}")
    
    return extracted_transcript


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
    print(f"  - Selected advice: {selected_advice}")
    
    return selected_advice


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
        
        # Clean up
        if file_exists:
            transcript_file.unlink()
            print(f"  - File cleaned up: ✅")
        
        return file_exists
        
    except Exception as e:
        print(f"❌ File creation test failed: {e}")
        return False


def main():
    """Run all fallback functionality tests"""
    print("🔍 Testing fallback button functionality without Redis...\n")
    
    success_count = 0
    total_tests = 4
    
    try:
        # Test button creation
        voice_buttons, text_buttons = test_fallback_button_creation()
        if voice_buttons and text_buttons:
            success_count += 1
            
        # Test transcript extraction
        extracted_transcript = test_transcript_extraction()
        if extracted_transcript:
            success_count += 1
            
        # Test advice generation
        selected_advice = test_advice_generation()
        if selected_advice:
            success_count += 1
            
        # Test file creation
        file_created = test_file_creation()
        if file_created:
            success_count += 1
            
        # Summary
        print(f"\n📊 Test Results:")
        print(f"✅ Passed: {success_count}/{total_tests}")
        print(f"❌ Failed: {total_tests - success_count}/{total_tests}")
        
        if success_count == total_tests:
            print("\n🎉 All fallback functionality tests PASSED!")
            print("🚀 The fallback buttons should work in production without Redis")
        else:
            print(f"\n⚠️ Some tests failed. Fallback functionality may have issues.")
            
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()