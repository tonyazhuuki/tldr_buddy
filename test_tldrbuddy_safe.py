#!/usr/bin/env python3
"""
Безопасное тестирование TLDRBuddy без влияния на продакшн
"""

import asyncio
import os
import sys
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from summary_engine import (
    SummaryEngine, 
    SummaryMode, 
    ContentType, 
    create_summary_engine
)


class SafeTLDRBuddyTester:
    """Безопасный тестер для TLDRBuddy функционала"""
    
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
    
    async def test_summary_engine_creation(self):
        """Тест создания SummaryEngine"""
        try:
            summary_engine = create_summary_engine()
            self.log_test("SummaryEngine Creation", True, "Engine created successfully")
            return summary_engine
        except Exception as e:
            self.log_test("SummaryEngine Creation", False, f"Error: {e}")
            return None
    
    async def test_mode_determination(self, summary_engine):
        """Тест определения режимов"""
        if not summary_engine:
            self.log_test("Mode Determination", False, "No engine available")
            return
        
        test_cases = [
            (ContentType.TELEGRAM_VOICE, "Короткое сообщение", 30, "CHAT"),
            (ContentType.TELEGRAM_VIDEO_NOTE, "Видео заметка", 45, "CHAT"),
            (ContentType.TELEGRAM_DOCUMENT, "Длинный документ", None, "LONGFORM"),
            (ContentType.TELEGRAM_VIDEO, "Длинное видео", 900, "LONGFORM"),
            (ContentType.UPLOADED_URL, "Внешняя ссылка", None, "LONGFORM"),
        ]
        
        all_passed = True
        for content_type, text, duration, expected in test_cases:
            try:
                mode = summary_engine.determine_mode(content_type, text, duration)
                success = mode.value.upper() == expected
                if not success:
                    all_passed = False
                self.log_test(
                    f"Mode: {content_type.value}", 
                    success, 
                    f"Expected: {expected}, Got: {mode.value}"
                )
            except Exception as e:
                all_passed = False
                self.log_test(f"Mode: {content_type.value}", False, f"Error: {e}")
        
        self.log_test("Mode Determination Overall", all_passed, f"{len(test_cases)} test cases")
    
    async def test_fallback_responses(self, summary_engine):
        """Тест fallback ответов"""
        if not summary_engine:
            self.log_test("Fallback Responses", False, "No engine available")
            return
        
        test_cases = [
            ("", "Empty text"),
            ("шум и музыка", "Noise text"),
            ("Обычный текст для анализа", "Normal text"),
        ]
        
        all_passed = True
        for text, description in test_cases:
            try:
                fallback = summary_engine.get_fallback_response(text)
                success = len(fallback) > 0 and "НЕ АНАЛИЗИРУЮ" in fallback
                if not success:
                    all_passed = False
                self.log_test(f"Fallback: {description}", success, f"Response length: {len(fallback)}")
            except Exception as e:
                all_passed = False
                self.log_test(f"Fallback: {description}", False, f"Error: {e}")
        
        self.log_test("Fallback Responses Overall", all_passed, f"{len(test_cases)} test cases")
    
    async def test_processing_without_openai(self, summary_engine):
        """Тест обработки без OpenAI клиента"""
        if not summary_engine:
            self.log_test("Processing Without OpenAI", False, "No engine available")
            return
        
        test_text = "Это тестовый текст для проверки обработки без OpenAI клиента."
        
        try:
            # Включаем SummaryEngine для теста
            summary_engine.enable()
            
            result = await summary_engine.process_summary(
                text=test_text,
                content_type=ContentType.TELEGRAM_VOICE
            )
            
            # Ожидаем, что обработка не удастся без OpenAI клиента
            expected_failure = not result.success and "OpenAI client not available" in result.error_message
            self.log_test(
                "Processing Without OpenAI", 
                expected_failure, 
                f"Success: {result.success}, Error: {result.error_message}"
            )
        except Exception as e:
            self.log_test("Processing Without OpenAI", False, f"Exception: {e}")
    
    async def test_configuration_updates(self, summary_engine):
        """Тест обновления конфигурации"""
        if not summary_engine:
            self.log_test("Configuration Updates", False, "No engine available")
            return
        
        try:
            original_tokens = summary_engine.configs[SummaryMode.CHAT].max_tokens
            summary_engine.update_config(SummaryMode.CHAT, max_tokens=1200)
            new_tokens = summary_engine.configs[SummaryMode.CHAT].max_tokens
            
            success = new_tokens == 1200
            self.log_test(
                "Configuration Updates", 
                success, 
                f"Updated max_tokens: {original_tokens} → {new_tokens}"
            )
        except Exception as e:
            self.log_test("Configuration Updates", False, f"Error: {e}")
    
    async def test_enable_disable_functionality(self, summary_engine):
        """Тест включения/отключения функционала"""
        if not summary_engine:
            self.log_test("Enable/Disable", False, "No engine available")
            return
        
        try:
            initial_state = summary_engine.enabled
            
            summary_engine.disable()
            disabled_state = summary_engine.enabled
            
            summary_engine.enable()
            enabled_state = summary_engine.enabled
            
            success = not disabled_state and enabled_state
            self.log_test(
                "Enable/Disable", 
                success, 
                f"States: {initial_state} → {disabled_state} → {enabled_state}"
            )
        except Exception as e:
            self.log_test("Enable/Disable", False, f"Error: {e}")
    
    async def test_integration_simulation(self):
        """Симуляция интеграции с main.py"""
        print("\n🧪 Тестирование интеграции с main.py...")
        
        # Симуляция helper функции
        async def simulate_process_with_summary_engine(text: str, content_type: ContentType, duration=None):
            summary_engine = create_summary_engine()
            
            if not summary_engine:
                return None
            
            # Включаем SummaryEngine для теста
            summary_engine.enable()
            
            try:
                result = await summary_engine.process_summary(
                    text=text,
                    content_type=content_type,
                    duration=duration
                )
                
                if result.success:
                    mode_label = "CHAT" if result.mode.value == "chat" else "LONGFORM"
                    return f"""📊 **TLDRBuddy Анализ** ({mode_label})

{result.summary}

⏱️ Обработано за {result.processing_time:.1f}с
🎯 Режим: {mode_label}
📊 Токены: {result.token_count}
"""
                else:
                    return None
                    
            except Exception as e:
                return None
        
        # Тестовые случаи
        test_cases = [
            ("Короткое сообщение для тестирования", ContentType.TELEGRAM_VOICE, 30),
            ("Длинный документ с много текста для проверки LONGFORM режима", ContentType.TELEGRAM_DOCUMENT, None),
        ]
        
        all_passed = True
        for text, content_type, duration in test_cases:
            try:
                result = await simulate_process_with_summary_engine(text, content_type, duration)
                # Ожидаем None без OpenAI клиента
                success = result is None
                self.log_test(
                    f"Integration: {content_type.value}", 
                    success, 
                    f"Result: {'None (expected)' if result is None else 'Unexpected success'}"
                )
                if not success:
                    all_passed = False
            except Exception as e:
                all_passed = False
                self.log_test(f"Integration: {content_type.value}", False, f"Error: {e}")
        
        self.log_test("Integration Simulation Overall", all_passed, f"{len(test_cases)} test cases")
    
    def generate_report(self):
        """Генерация отчета о тестировании"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 ОТЧЕТ О ТЕСТИРОВАНИИ")
        print(f"=" * 50)
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
        
        report_file = f"tldrbuddy_test_report_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 Отчет сохранен в: {report_file}")
        
        return passed_tests == total_tests


async def main():
    """Основная функция тестирования"""
    print("🚀 Безопасное тестирование TLDRBuddy")
    print("=" * 50)
    print("📋 Этот тест проверяет функциональность без влияния на продакшн")
    print("🔒 Все тесты выполняются в изолированной среде")
    print("=" * 50)
    
    tester = SafeTLDRBuddyTester()
    
    # Создание SummaryEngine
    summary_engine = await tester.test_summary_engine_creation()
    
    # Тестирование различных компонентов
    await tester.test_mode_determination(summary_engine)
    await tester.test_fallback_responses(summary_engine)
    await tester.test_processing_without_openai(summary_engine)
    await tester.test_configuration_updates(summary_engine)
    await tester.test_enable_disable_functionality(summary_engine)
    await tester.test_integration_simulation()
    
    # Генерация отчета
    all_passed = tester.generate_report()
    
    print(f"\n🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("🟢 TLDRBuddy готов к безопасному развертыванию")
        print("📝 Следующий шаг: тестирование с реальным OpenAI API ключом")
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