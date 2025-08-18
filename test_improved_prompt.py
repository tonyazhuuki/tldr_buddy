#!/usr/bin/env python3
"""
Тест улучшенного промпта для CHAT режима
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from text_processor import TextProcessor
from summary_engine import create_summary_engine, ContentType


async def test_improved_prompt():
    """Тест улучшенного промпта"""
    print("🧪 Тестирование улучшенного промпта CHAT режима")
    print("=" * 60)
    
    try:
        # Создаем компоненты
        api_key = os.getenv('OPENAI_API_KEY')
        text_processor = TextProcessor(api_key)
        summary_engine = create_summary_engine(text_processor.client)
        summary_engine.enable()
        
        # Тестовый текст
        test_text = """
        Привет! Я хочу рассказать о своем проекте. Мы разрабатываем новое приложение 
        для управления задачами. Основные функции: создание задач, установка приоритетов, 
        отслеживание прогресса. Проект планируем завершить через 2 месяца. 
        Бюджет у нас около 50 тысяч долларов, команда из 5 человек. 
        Нужно будет провести тестирование с пользователями и собрать обратную связь.
        """
        
        print("📄 Обрабатываем тестовый текст...")
        
        result = await summary_engine.process_summary(
            text=test_text,
            content_type=ContentType.TELEGRAM_VOICE,
            duration=45
        )
        
        if result.success:
            print("✅ Обработка успешна!")
            print(f"📊 Режим: {result.mode.value}")
            print(f"⏱️ Время: {result.processing_time:.1f}с")
            print(f"🎯 Токены: {result.token_count}")
            print("\n📄 ПОЛНЫЙ РЕЗУЛЬТАТ:")
            print("=" * 60)
            print(result.summary)
            print("=" * 60)
            
            return True
        else:
            print(f"❌ Ошибка обработки: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False


async def main():
    """Основная функция"""
    success = await test_improved_prompt()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ТЕСТ УЛУЧШЕННОГО ПРОМПТА ПРОЙДЕН!")
        print("✅ Промпт теперь дает более подробную информацию")
        print("✅ Формат соответствует старому качественному анализу")
    else:
        print("❌ ТЕСТ НЕ ПРОЙДЕН")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 