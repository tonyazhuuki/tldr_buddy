#!/usr/bin/env python3
"""
Тестовый бот для безопасного тестирования TLDRBuddy
Использует отдельный токен и не влияет на продакшн бота
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

# Импорт SummaryEngine
from summary_engine import SummaryEngine, ContentType, create_summary_engine

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_bot_tldrbuddy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация тестового бота
TEST_TELEGRAM_TOKEN = os.getenv('TEST_TELEGRAM_TOKEN')  # Отдельный токен для тестов
if not TEST_TELEGRAM_TOKEN:
    logger.error("TEST_TELEGRAM_TOKEN environment variable not set")
    logger.error("Создайте тестового бота через @BotFather и установите TEST_TELEGRAM_TOKEN")
    sys.exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=TEST_TELEGRAM_TOKEN)
dp = Dispatcher()

# Глобальные переменные для тестирования
summary_engine = None
test_results = []


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start для тестового бота"""
    welcome_text = """
🧪 **TLDRBuddy Test Bot**

Это тестовый бот для безопасного тестирования TLDRBuddy функционала.

**🔒 Безопасность:**
• Использует отдельный токен
• Не влияет на продакшн бота
• Все тесты изолированы

**📋 Команды для тестирования:**
• `/test_summary` - Тест SummaryEngine
• `/test_mode` - Тест определения режимов
• `/test_fallback` - Тест fallback ответов
• `/test_config` - Тест конфигурации
• `/status` - Статус системы
• `/help` - Справка

**⚠️ Внимание:** Этот бот только для тестирования!
"""
    await message.answer(welcome_text, parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам тестового бота"""
    help_text = """
🧪 **TLDRBuddy Test Bot - Справка**

**🔍 ТЕСТОВЫЕ КОМАНДЫ:**
• `/test_summary` - Тест SummaryEngine без OpenAI
• `/test_mode` - Тест определения режимов CHAT/LONGFORM
• `/test_fallback` - Тест fallback ответов
• `/test_config` - Тест обновления конфигурации
• `/test_enable` - Тест включения/отключения
• `/test_integration` - Тест интеграции с main.py

**📊 МОНИТОРИНГ:**
• `/status` - Статус SummaryEngine
• `/results` - Результаты последних тестов
• `/logs` - Последние логи

**🛠️ УПРАВЛЕНИЕ:**
• `/init` - Инициализация SummaryEngine
• `/reset` - Сброс результатов тестов
• `/cleanup` - Очистка логов

**💡 ПОДСКАЗКА:** Начните с `/init` для инициализации системы
"""
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("init"))
async def cmd_init(message: Message):
    """Инициализация SummaryEngine для тестирования"""
    global summary_engine
    
    try:
        await message.answer("🔄 Инициализация SummaryEngine...")
        
        # Создание SummaryEngine без OpenAI клиента
        summary_engine = create_summary_engine()
        
        # Проверка статуса
        status_text = f"""
✅ **SummaryEngine инициализирован**

**📊 Статус:**
• Создан: ✅
• Включен: {'✅' if summary_engine.enabled else '❌'}
• OpenAI клиент: {'✅' if summary_engine.client else '❌'}

**⚙️ Конфигурация:**
• CHAT режим: {summary_engine.configs[summary_engine.SummaryMode.CHAT].max_tokens} токенов
• LONGFORM режим: {summary_engine.configs[summary_engine.SummaryMode.LONGFORM].max_tokens} токенов

**🔧 Следующие шаги:**
• `/test_summary` - Протестировать обработку
• `/test_mode` - Протестировать определение режимов
• `/status` - Проверить статус
"""
        
        await message.answer(status_text, parse_mode="Markdown")
        logger.info("SummaryEngine initialized for testing")
        
    except Exception as e:
        error_text = f"❌ Ошибка инициализации: {str(e)}"
        await message.answer(error_text)
        logger.error(f"SummaryEngine initialization failed: {e}")


@dp.message(Command("status"))
async def cmd_status(message: Message):
    """Проверка статуса системы"""
    global summary_engine
    
    if not summary_engine:
        await message.answer("❌ SummaryEngine не инициализирован. Используйте `/init`")
        return
    
    status_text = f"""
📊 **Статус TLDRBuddy Test Bot**

**🔧 SummaryEngine:**
• Инициализирован: ✅
• Включен: {'✅' if summary_engine.enabled else '❌'}
• OpenAI клиент: {'✅' if summary_engine.client else '❌'}

**⚙️ Конфигурация:**
• CHAT режим: {summary_engine.configs[summary_engine.SummaryMode.CHAT].max_tokens} токенов
• LONGFORM режим: {summary_engine.configs[summary_engine.SummaryMode.LONGFORM].max_tokens} токенов

**📈 Тестирование:**
• Выполнено тестов: {len(test_results)}
• Успешных: {sum(1 for r in test_results if r.get('success', False))}
• Неудачных: {sum(1 for r in test_results if not r.get('success', True))}

**🕐 Время работы:** {datetime.now().strftime('%H:%M:%S')}
"""
    
    await message.answer(status_text, parse_mode="Markdown")


@dp.message(Command("test_summary"))
async def cmd_test_summary(message: Message):
    """Тест SummaryEngine без OpenAI"""
    global summary_engine, test_results
    
    if not summary_engine:
        await message.answer("❌ SummaryEngine не инициализирован. Используйте `/init`")
        return
    
    await message.answer("🧪 Тестирование SummaryEngine...")
    
    try:
        test_text = "Это тестовый текст для проверки SummaryEngine без OpenAI клиента."
        
        result = await summary_engine.process_summary(
            text=test_text,
            content_type=ContentType.TELEGRAM_VOICE
        )
        
        # Ожидаем, что обработка не удастся без OpenAI клиента
        expected_failure = not result.success and "OpenAI client not available" in result.error_message
        
        test_result = {
            "test": "SummaryEngine Processing",
            "success": expected_failure,
            "details": f"Success: {result.success}, Error: {result.error_message}",
            "timestamp": datetime.now().isoformat()
        }
        test_results.append(test_result)
        
        result_text = f"""
🧪 **Тест SummaryEngine**

**📝 Тестовый текст:** {test_text}

**📊 Результат:**
• Успех: {'✅' if expected_failure else '❌'}
• Ожидалось: Неудача (без OpenAI клиента)
• Получено: {'Неудача' if not result.success else 'Успех'}
• Ошибка: {result.error_message}

**🎯 Вывод:** {'✅ Тест пройден' if expected_failure else '❌ Тест не пройден'}
"""
        
        await message.answer(result_text, parse_mode="Markdown")
        
    except Exception as e:
        error_text = f"❌ Ошибка тестирования: {str(e)}"
        await message.answer(error_text)
        logger.error(f"SummaryEngine test failed: {e}")


@dp.message(Command("test_mode"))
async def cmd_test_mode(message: Message):
    """Тест определения режимов"""
    global summary_engine, test_results
    
    if not summary_engine:
        await message.answer("❌ SummaryEngine не инициализирован. Используйте `/init`")
        return
    
    await message.answer("🧪 Тестирование определения режимов...")
    
    try:
        test_cases = [
            (ContentType.TELEGRAM_VOICE, "Короткое сообщение", 30, "CHAT"),
            (ContentType.TELEGRAM_VIDEO_NOTE, "Видео заметка", 45, "CHAT"),
            (ContentType.TELEGRAM_DOCUMENT, "Длинный документ", None, "LONGFORM"),
            (ContentType.TELEGRAM_VIDEO, "Длинное видео", 900, "LONGFORM"),
        ]
        
        results_text = "🧪 **Тест определения режимов**\n\n"
        all_passed = True
        
        for content_type, text, duration, expected in test_cases:
            try:
                mode = summary_engine.determine_mode(content_type, text, duration)
                success = mode.value.upper() == expected
                if not success:
                    all_passed = False
                
                status = "✅" if success else "❌"
                results_text += f"{status} {content_type.value}: {expected} → {mode.value}\n"
                
            except Exception as e:
                all_passed = False
                results_text += f"❌ {content_type.value}: Ошибка - {str(e)}\n"
        
        test_result = {
            "test": "Mode Determination",
            "success": all_passed,
            "details": f"{len(test_cases)} test cases, {'All passed' if all_passed else 'Some failed'}",
            "timestamp": datetime.now().isoformat()
        }
        test_results.append(test_result)
        
        results_text += f"\n🎯 **Итог:** {'✅ Все тесты пройдены' if all_passed else '❌ Некоторые тесты не пройдены'}"
        
        await message.answer(results_text, parse_mode="Markdown")
        
    except Exception as e:
        error_text = f"❌ Ошибка тестирования режимов: {str(e)}"
        await message.answer(error_text)
        logger.error(f"Mode determination test failed: {e}")


@dp.message(Command("test_fallback"))
async def cmd_test_fallback(message: Message):
    """Тест fallback ответов"""
    global summary_engine, test_results
    
    if not summary_engine:
        await message.answer("❌ SummaryEngine не инициализирован. Используйте `/init`")
        return
    
    await message.answer("🧪 Тестирование fallback ответов...")
    
    try:
        test_cases = [
            ("", "Пустой текст"),
            ("шум и музыка", "Шумовой текст"),
            ("Обычный текст для анализа", "Нормальный текст"),
        ]
        
        results_text = "🧪 **Тест Fallback Ответов**\n\n"
        all_passed = True
        
        for text, description in test_cases:
            try:
                fallback = summary_engine.get_fallback_response(text)
                success = len(fallback) > 0 and "НЕ АНАЛИЗИРУЮ" in fallback
                if not success:
                    all_passed = False
                
                status = "✅" if success else "❌"
                preview = fallback[:50] + "..." if len(fallback) > 50 else fallback
                results_text += f"{status} {description}: {preview}\n"
                
            except Exception as e:
                all_passed = False
                results_text += f"❌ {description}: Ошибка - {str(e)}\n"
        
        test_result = {
            "test": "Fallback Responses",
            "success": all_passed,
            "details": f"{len(test_cases)} test cases, {'All passed' if all_passed else 'Some failed'}",
            "timestamp": datetime.now().isoformat()
        }
        test_results.append(test_result)
        
        results_text += f"\n🎯 **Итог:** {'✅ Все тесты пройдены' if all_passed else '❌ Некоторые тесты не пройдены'}"
        
        await message.answer(results_text, parse_mode="Markdown")
        
    except Exception as e:
        error_text = f"❌ Ошибка тестирования fallback: {str(e)}"
        await message.answer(error_text)
        logger.error(f"Fallback test failed: {e}")


@dp.message(Command("results"))
async def cmd_results(message: Message):
    """Показать результаты последних тестов"""
    global test_results
    
    if not test_results:
        await message.answer("📊 Нет результатов тестов. Запустите тесты с помощью команд `/test_*`")
        return
    
    results_text = "📊 **Результаты последних тестов**\n\n"
    
    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r.get('success', False))
    failed_tests = total_tests - passed_tests
    
    results_text += f"📋 Всего тестов: {total_tests}\n"
    results_text += f"✅ Успешных: {passed_tests}\n"
    results_text += f"❌ Неудачных: {failed_tests}\n"
    results_text += f"📈 Успешность: {(passed_tests/total_tests*100):.1f}%\n\n"
    
    # Последние 5 тестов
    recent_tests = test_results[-5:]
    results_text += "🕐 **Последние тесты:**\n"
    
    for test in recent_tests:
        status = "✅" if test.get('success', False) else "❌"
        test_name = test.get('test', 'Unknown')
        timestamp = test.get('timestamp', 'Unknown')
        time_str = datetime.fromisoformat(timestamp).strftime('%H:%M:%S')
        
        results_text += f"{status} {test_name} ({time_str})\n"
    
    await message.answer(results_text, parse_mode="Markdown")


@dp.message(Command("reset"))
async def cmd_reset(message: Message):
    """Сброс результатов тестов"""
    global test_results
    
    test_results.clear()
    await message.answer("🔄 Результаты тестов сброшены")


@dp.message(Command("cleanup"))
async def cmd_cleanup(message: Message):
    """Очистка логов"""
    try:
        # Очистка лог файла
        log_file = Path('logs/test_bot_tldrbuddy.log')
        if log_file.exists():
            log_file.unlink()
        
        await message.answer("🧹 Логи очищены")
    except Exception as e:
        await message.answer(f"❌ Ошибка очистки логов: {str(e)}")


@dp.message(F.text & ~F.command)
async def handle_text_message(message: Message):
    """Обработчик текстовых сообщений для тестирования"""
    global summary_engine
    
    if not summary_engine:
        await message.answer("❌ SummaryEngine не инициализирован. Используйте `/init`")
        return
    
    await message.answer("🧪 Тестирование обработки текстового сообщения...")
    
    try:
        # Симуляция обработки текста
        text = message.text
        
        # Определение режима
        mode = summary_engine.determine_mode(ContentType.TEXT_INPUT, text)
        
        # Попытка обработки (ожидаем неудачу без OpenAI)
        result = await summary_engine.process_summary(
            text=text,
            content_type=ContentType.TEXT_INPUT
        )
        
        response_text = f"""
🧪 **Тест обработки текста**

**📝 Исходный текст:** {text[:100]}{'...' if len(text) > 100 else ''}

**🎯 Определенный режим:** {mode.value.upper()}

**📊 Результат обработки:**
• Успех: {'✅' if result.success else '❌'}
• Ошибка: {result.error_message}

**💡 Ожидалось:** Неудача (без OpenAI клиента)
"""
        
        await message.answer(response_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка обработки: {str(e)}")


async def main():
    """Основная функция тестового бота"""
    logger.info("🚀 Запуск TLDRBuddy Test Bot...")
    
    # Создание директории для логов
    Path('logs').mkdir(exist_ok=True)
    
    logger.info(f"✅ Test Bot инициализирован с токеном: {TEST_TELEGRAM_TOKEN[:10]}...")
    logger.info("📋 Доступные команды: /start, /help, /init, /test_*")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("🛑 Test Bot остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Test Bot: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 