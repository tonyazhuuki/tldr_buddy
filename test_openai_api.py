#!/usr/bin/env python3
"""
Тест OpenAI API для TLDRBuddy
Проверяет реальную работу SummaryEngine с OpenAI API
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from summary_engine import (
    SummaryEngine, 
    SummaryMode, 
    ContentType, 
    create_summary_engine
)


class OpenAIAPITester:
    """Тестер для OpenAI API с TLDRBuddy"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Логирование результатов теста"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {details}")
    
    async def test_api_connection(self):
        """Тест подключения к OpenAI API"""
        try:
            # Проверяем наличие API ключа
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                self.log_test("API Connection", False, "OPENAI_API_KEY not set")
                return False
            
            # Создаем OpenAI клиент
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            
            # Создаем SummaryEngine с OpenAI клиентом
            summary_engine = create_summary_engine(openai_client)
            summary_engine.enable()
            
            if not summary_engine.client:
                self.log_test("API Connection", False, "OpenAI client not created")
                return False
            
            # Простой тест API
            test_text = "Привет, это тестовое сообщение для проверки API."
            
            result = await summary_engine.process_summary(
                text=test_text,
                content_type=ContentType.TELEGRAM_VOICE
            )
            
            if result.success:
                self.log_test("API Connection", True, f"Success! Tokens: {result.token_count}")
                return True
            else:
                self.log_test("API Connection", False, f"API Error: {result.error_message}")
                return False
                
        except Exception as e:
            self.log_test("API Connection", False, f"Exception: {e}")
            return False
    
    async def test_chat_mode(self):
        """Тест CHAT режима"""
        try:
            # Создаем OpenAI клиент
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            openai_client = OpenAI(api_key=api_key)
            
            summary_engine = create_summary_engine(openai_client)
            summary_engine.enable()
            
            # Короткий текст для CHAT режима
            chat_text = """
            Привет! Я хочу рассказать о своем проекте. Мы разрабатываем новое приложение 
            для управления задачами. Основные функции: создание задач, установка приоритетов, 
            отслеживание прогресса. Проект планируем завершить через 2 месяца.
            """
            
            result = await summary_engine.process_summary(
                text=chat_text,
                content_type=ContentType.TELEGRAM_VOICE,
                duration=45
            )
            
            if result.success:
                success = (result.mode == SummaryMode.CHAT and 
                          result.token_count <= 1100 and
                          "ОСНОВНЫЕ МЫСЛИ" in result.summary)
                
                self.log_test("CHAT Mode", success, 
                            f"Mode: {result.mode.value}, Tokens: {result.token_count}, "
                            f"Time: {result.processing_time:.1f}s")
                
                if success:
                    print(f"📄 Summary preview: {result.summary[:200]}...")
                
                return success
            else:
                self.log_test("CHAT Mode", False, f"Error: {result.error_message}")
                return False
                
        except Exception as e:
            self.log_test("CHAT Mode", False, f"Exception: {e}")
            return False
    
    async def test_longform_mode(self):
        """Тест LONGFORM режима"""
        try:
            # Создаем OpenAI клиент
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            openai_client = OpenAI(api_key=api_key)
            
            summary_engine = create_summary_engine(openai_client)
            summary_engine.enable()
            
            # Длинный текст для LONGFORM режима
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
            
            result = await summary_engine.process_summary(
                text=longform_text,
                content_type=ContentType.TELEGRAM_DOCUMENT
            )
            
            if result.success:
                success = (result.mode == SummaryMode.LONGFORM and 
                          result.token_count <= 1600 and
                          "ТЕЗИС" in result.summary)
                
                self.log_test("LONGFORM Mode", success, 
                            f"Mode: {result.mode.value}, Tokens: {result.token_count}, "
                            f"Time: {result.processing_time:.1f}s")
                
                if success:
                    print(f"📄 Summary preview: {result.summary[:300]}...")
                
                return success
            else:
                self.log_test("LONGFORM Mode", False, f"Error: {result.error_message}")
                return False
                
        except Exception as e:
            self.log_test("LONGFORM Mode", False, f"Exception: {e}")
            return False
    
    async def test_mode_determination(self):
        """Тест определения режимов с реальными данными"""
        try:
            # Создаем OpenAI клиент
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            openai_client = OpenAI(api_key=api_key)
            
            summary_engine = create_summary_engine(openai_client)
            summary_engine.enable()
            
            test_cases = [
                (ContentType.TELEGRAM_VOICE, "Короткое голосовое сообщение", 30, SummaryMode.CHAT),
                (ContentType.TELEGRAM_VIDEO_NOTE, "Видео заметка", 45, SummaryMode.CHAT),
                (ContentType.TELEGRAM_DOCUMENT, "Длинный документ с много текста", None, SummaryMode.LONGFORM),
                (ContentType.TELEGRAM_VIDEO, "Длинное видео", 900, SummaryMode.LONGFORM),
            ]
            
            all_passed = True
            for content_type, text, duration, expected_mode in test_cases:
                try:
                    mode = summary_engine.determine_mode(content_type, text, duration)
                    success = mode == expected_mode
                    if not success:
                        all_passed = False
                    
                    self.log_test(f"Mode: {content_type.value}", success, 
                                f"Expected: {expected_mode.value}, Got: {mode.value}")
                    
                except Exception as e:
                    all_passed = False
                    self.log_test(f"Mode: {content_type.value}", False, f"Error: {e}")
            
            self.log_test("Mode Determination Overall", all_passed, f"{len(test_cases)} test cases")
            return all_passed
            
        except Exception as e:
            self.log_test("Mode Determination", False, f"Exception: {e}")
            return False
    
    async def test_performance(self):
        """Тест производительности"""
        try:
            # Создаем OpenAI клиент
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            openai_client = OpenAI(api_key=api_key)
            
            summary_engine = create_summary_engine(openai_client)
            summary_engine.enable()
            
            test_text = "Это тестовое сообщение для проверки производительности API."
            
            start_time = time.time()
            result = await summary_engine.process_summary(
                text=test_text,
                content_type=ContentType.TELEGRAM_VOICE
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if result.success:
                # Проверяем производительность
                time_ok = processing_time < 10.0  # Максимум 10 секунд
                tokens_ok = result.token_count <= 1100  # Лимит токенов
                
                success = time_ok and tokens_ok
                
                self.log_test("Performance", success, 
                            f"Time: {processing_time:.1f}s, Tokens: {result.token_count}")
                
                return success
            else:
                self.log_test("Performance", False, f"Error: {result.error_message}")
                return False
                
        except Exception as e:
            self.log_test("Performance", False, f"Exception: {e}")
            return False
    
    def generate_report(self):
        """Генерация отчета о тестировании"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 ОТЧЕТ О ТЕСТИРОВАНИИ OPENAI API")
        print(f"=" * 60)
        print(f"⏱️ Время тестирования: {duration}")
        print(f"📋 Всего тестов: {total_tests}")
        print(f"✅ Успешных: {passed_tests}")
        print(f"❌ Неудачных: {failed_tests}")
        print(f"📈 Успешность: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ НЕУДАЧНЫЕ ТЕСТЫ:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        # Сохранение отчета в файл
        report_data = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": duration.total_seconds(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": passed_tests/total_tests*100,
            "results": self.test_results
        }
        
        report_file = f"openai_api_test_report_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Отчет сохранен в: {report_file}")
        
        return passed_tests == total_tests


async def main():
    """Основная функция тестирования OpenAI API"""
    print("🚀 Тестирование OpenAI API для TLDRBuddy")
    print("=" * 60)
    print("📋 Этот тест проверяет реальную работу с OpenAI API")
    print("💰 Требует OpenAI API ключ и может потреблять токены")
    print("=" * 60)
    
    # Проверяем API ключ
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен!")
        print("💡 Установите переменную окружения: export OPENAI_API_KEY='your_key'")
        return
    
    print(f"✅ API ключ найден: {api_key[:10]}...")
    
    tester = OpenAIAPITester()
    
    # Тестирование различных компонентов
    await tester.test_api_connection()
    await tester.test_chat_mode()
    await tester.test_longform_mode()
    await tester.test_mode_determination()
    await tester.test_performance()
    
    # Генерация отчета
    all_passed = tester.generate_report()
    
    print(f"\n🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ OPENAI API ПРОШЛИ УСПЕШНО!")
        print("🟢 TLDRBuddy полностью готов к работе")
        print("🚀 Можно безопасно развертывать в продакшн")
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("🔴 Требуется исправление перед развертыванием")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print("1. Проверьте отчет для деталей неудачных тестов")
    print("2. Исправьте выявленные проблемы")
    print("3. Запустите тест снова для подтверждения")
    print("4. Только после успешного прохождения всех тестов развертывайте в продакшн")


if __name__ == "__main__":
    asyncio.run(main()) 