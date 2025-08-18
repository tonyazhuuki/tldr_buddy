#!/usr/bin/env python3
"""
Простой тест существующей системы с TLDRBuddy
Использует уже настроенные компоненты
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from text_processor import TextProcessor
from summary_engine import create_summary_engine, ContentType


async def test_existing_system():
    """Тест существующей системы с TLDRBuddy"""
    print("🧪 Тестирование существующей системы с TLDRBuddy")
    print("=" * 60)
    
    try:
        # 1. Проверяем API ключ
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY не найден в .env")
            return False
        
        print(f"✅ API ключ найден: {api_key[:20]}...")
        
        # 2. Создаем TextProcessor (как в main.py)
        print("📝 Создаем TextProcessor...")
        text_processor = TextProcessor(api_key)
        
        if not text_processor.client:
            print("❌ TextProcessor не создал OpenAI клиент")
            return False
        
        print("✅ TextProcessor создан успешно")
        
        # 3. Создаем SummaryEngine с существующим клиентом
        print("🔧 Создаем SummaryEngine...")
        summary_engine = create_summary_engine(text_processor.client)
        summary_engine.enable()
        
        print("✅ SummaryEngine создан и включен")
        
        # 4. Тестируем обработку текста
        print("🧪 Тестируем обработку текста...")
        
        test_text = """
        Привет! Я хочу рассказать о своем проекте. Мы разрабатываем новое приложение 
        для управления задачами. Основные функции: создание задач, установка приоритетов, 
        отслеживание прогресса. Проект планируем завершить через 2 месяца.
        """
        
        result = await summary_engine.process_summary(
            text=test_text,
            content_type=ContentType.TELEGRAM_VOICE,
            duration=45
        )
        
        if result.success:
            print("✅ Обработка текста успешна!")
            print(f"📊 Режим: {result.mode.value}")
            print(f"⏱️ Время: {result.processing_time:.1f}с")
            print(f"🎯 Токены: {result.token_count}")
            print(f"📄 Саммари: {result.summary[:200]}...")
            
            return True
        else:
            print(f"❌ Ошибка обработки: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False


async def main():
    """Основная функция"""
    success = await test_existing_system()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("✅ TLDRBuddy работает с существующей системой")
        print("🚀 Можно безопасно включать в продакшн")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
        print("🔴 Требуется исправление")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 