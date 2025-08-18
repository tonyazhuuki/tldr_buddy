#!/usr/bin/env python3
"""
Тест LONGFORM режима TLDRBuddy
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


async def test_longform_mode():
    """Тест LONGFORM режима"""
    print("🧪 Тестирование LONGFORM режима TLDRBuddy")
    print("=" * 60)
    
    try:
        # 1. Создаем компоненты
        api_key = os.getenv('OPENAI_API_KEY')
        text_processor = TextProcessor(api_key)
        summary_engine = create_summary_engine(text_processor.client)
        summary_engine.enable()
        
        print("✅ Компоненты созданы")
        
        # 2. Длинный текст для LONGFORM режима
        longform_text = """
        КОМПЛЕКСНЫЙ АНАЛИЗ РЫНКА ИТ-УСЛУГ В 2024 ГОДУ
        
        Введение
        Современный рынок информационных технологий переживает период активной трансформации, 
        обусловленной внедрением искусственного интеллекта, облачных технологий и цифровизацией 
        бизнес-процессов. Данный анализ представляет собой комплексное исследование текущего 
        состояния рынка ИТ-услуг, выявление ключевых трендов и прогнозирование развития отрасли 
        на ближайшие годы.
        
        Методология исследования
        Исследование проводилось на основе анализа данных из более чем 500 компаний, 
        работающих в сфере ИТ-услуг, включая как крупные корпорации, так и стартапы. 
        Использовались методы статистического анализа, экспертных интервью и изучения 
        публичных финансовых отчетов.
        
        Ключевые выводы
        1. Объем рынка ИТ-услуг в 2024 году составил $1.2 трлн, что на 8.5% больше 
           показателей предыдущего года.
        2. Наибольший рост демонстрируют сегменты облачных услуг (23%) и ИИ-решений (45%).
        3. Средняя стоимость разработки мобильного приложения составляет $50,000-150,000.
        4. Время вывода продукта на рынок сократилось с 18 до 12 месяцев.
        
        Технологические тренды
        Искусственный интеллект и машинное обучение становятся основными драйверами роста 
        рынка. Компании активно внедряют ИИ-решения для автоматизации процессов, 
        улучшения клиентского опыта и оптимизации бизнес-операций.
        
        Облачные технологии продолжают доминировать в архитектуре современных решений. 
        Мультиоблачные стратегии и гибридные подходы становятся стандартом для крупных 
        предприятий, обеспечивая гибкость и масштабируемость.
        
        Заключение
        Рынок ИТ-услуг демонстрирует устойчивый рост и высокий потенциал для дальнейшего 
        развития. Ключевыми факторами успеха становятся инновационность решений, 
        качество сервиса и способность адаптироваться к быстро меняющимся требованиям рынка.
        """
        
        print("📄 Обрабатываем длинный текст...")
        
        result = await summary_engine.process_summary(
            text=longform_text,
            content_type=ContentType.TELEGRAM_DOCUMENT
        )
        
        if result.success:
            print("✅ LONGFORM обработка успешна!")
            print(f"📊 Режим: {result.mode.value}")
            print(f"⏱️ Время: {result.processing_time:.1f}с")
            print(f"🎯 Токены: {result.token_count}")
            print(f"📄 Саммари (первые 500 символов):")
            print("-" * 50)
            print(result.summary[:500])
            print("-" * 50)
            
            # Проверяем, что это действительно LONGFORM режим
            if result.mode.value == "longform":
                print("✅ Режим определен правильно: LONGFORM")
                return True
            else:
                print(f"❌ Неправильный режим: ожидался longform, получен {result.mode.value}")
                return False
        else:
            print(f"❌ Ошибка обработки: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False


async def main():
    """Основная функция"""
    success = await test_longform_mode()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 LONGFORM ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("✅ TLDRBuddy корректно обрабатывает длинные документы")
        print("🚀 LONGFORM режим готов к работе")
    else:
        print("❌ LONGFORM ТЕСТ НЕ ПРОЙДЕН")
        print("🔴 Требуется исправление")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main()) 