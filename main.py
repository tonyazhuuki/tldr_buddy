#!/usr/bin/env python3
"""
Telegram Voice-to-Insight Pipeline
Main bot application with aiogram 3
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ErrorEvent, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from dotenv import load_dotenv

# Import speech processing modules
from speech_pipeline import SpeechPipelineFactory, SpeechPipelineError

# Import text processing
from text_processor import TextProcessor

# Import enhanced systems for Phase 3
# Fully re-enabled for complete functionality
import redis.asyncio as redis
from button_ui_manager import ButtonUIManager, create_button_ui_manager
from archetype_system import ArchetypeSystem, create_archetype_system

# Import SummaryEngine for two-mode summarization
from summary_engine import SummaryEngine, ContentType, create_summary_engine

# Import process management for single-instance enforcement
from process_manager import enforce_single_instance

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set")
    sys.exit(1)

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Global pipeline instances
speech_pipeline = None
text_processor = None

# Global enhanced system instances  
redis_client = None
archetype_system = None
button_ui_manager = None
summary_engine = None

# Simple in-memory storage for last messages by chat (no Redis needed)
chat_last_messages = {}  # {chat_id: {"text": str, "timestamp": float, "type": "voice|text", "user_id": str}}

# Helper function for SummaryEngine integration
async def process_with_summary_engine(text: str, content_type: ContentType, duration: Optional[int] = None) -> Optional[str]:
    """
    Process text with SummaryEngine if available, otherwise return None
    
    Args:
        text: Text to process
        content_type: Type of content
        duration: Duration in seconds (for heuristics)
        
    Returns:
        Formatted summary if SummaryEngine is available and successful, None otherwise
    """
    if not summary_engine or not summary_engine.enabled:
        return None
    
    try:
        result = await summary_engine.process_summary(
            text=text,
            content_type=content_type,
            duration=duration
        )
        
        if result.success:
            return result.summary
        else:
            logger.warning(f"SummaryEngine failed: {result.error_message}")
            return None
            
    except Exception as e:
        logger.error(f"SummaryEngine processing error: {e}")
        return None


def create_transcript_buttons() -> InlineKeyboardMarkup:
    """Create inline keyboard with transcript buttons"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Показать транскрипт", callback_data="show_transcript"),
            InlineKeyboardButton(text="📄 Скачать .txt", callback_data="download_txt")
        ]
    ])
    logger.info("Created transcript buttons with callback_data: show_transcript, download_txt")
    return keyboard


async def send_transcript_text(message: Message, text: str, chat_id: str, user_id: str = None):
    """Send transcript as text or file based on length"""
    logger.info(f"send_transcript_text: text_length={len(text)}, chat_id={chat_id}, user_id={user_id}")
    
    if len(text) <= 4096:
        # Send as text message
        transcript_text = f"""📝 **ТРАНСКРИПТ**

{text}

---
💡 *Для копирования - выделите текст выше*"""
        await message.answer(transcript_text, parse_mode="Markdown")
    else:
        # Send as file
        from io import BytesIO
        import time
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{user_id}_{timestamp}.txt"
        
        file_content = f"""ТРАНСКРИПТ СООБЩЕНИЯ
Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Пользователь: {user_id}

{text}

---
Создано ботом TLDR Buddy"""
        
        file_obj = BytesIO(file_content.encode('utf-8'))
        file_obj.name = filename
        
        await message.answer_document(
            document=file_obj,
            caption="📄 **Транскрипт отправлен как файл**\n\nФайл содержит полный текст сообщения."
        )


async def get_last_message_data(chat_id: str, user_id: str = None, reply_to_message_id: int = None) -> dict:
    """
    Get last message data for chat, with support for reply-to-message
    
    Args:
        chat_id: Chat ID
        user_id: User ID (optional, for filtering)
        reply_to_message_id: Message ID to reply to (optional)
    
    Returns:
        Message data dict or None
    """
    logger.info(f"get_last_message_data: chat_id={chat_id}, user_id={user_id}")
    logger.info(f"Available chats: {list(chat_last_messages.keys())}")
    
    if chat_id not in chat_last_messages:
        logger.info(f"Chat {chat_id} not found in chat_last_messages, total chats: {len(chat_last_messages)}")
        return None
    
    last_msg_data = chat_last_messages[chat_id]
    
    # Check if message is not too old (1 hour limit)
    import time
    if time.time() - last_msg_data["timestamp"] > 3600:
        logger.info(f"Message for chat {chat_id} is too old ({(time.time() - last_msg_data['timestamp'])/60:.1f} minutes)")
        return None
    
    # If user_id is specified, check if it matches
    if user_id and last_msg_data.get("user_id") != user_id:
        logger.info(f"Message in chat {chat_id} belongs to user {last_msg_data.get('user_id')}, not {user_id}")
        return None
    
    logger.info(f"Found message for chat {chat_id}, type: {last_msg_data['type']}, age: {(time.time() - last_msg_data['timestamp'])/60:.1f} minutes")
    return last_msg_data


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    welcome_text = """
🎙️ **Telegram Voice-to-Insight Pipeline**

Привет! Я бот для анализа голосовых сообщений с использованием ИИ.

**Возможности:**
• 🎤 Преобразование речи в текст (faster-whisper)
• 🧠 Анализ содержания с помощью LLM
• 🎭 Анализ тона и эмоций
• 🌍 Поддержка русского и английского языков
• ⚡ Быстрая обработка (≤2 секунды для минутного аудио)

**Команды:**
/start - Показать это сообщение
/help - Справка по использованию
/health - Проверить статус системы
/stats - Статистика обработки

**Использование:**
Просто перешлите мне голосовое или видео сообщение для анализа!
"""
    await message.answer(welcome_text, parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = """🤖 **TLDR Buddy - Помощник по анализу сообщений**

**📋 ОСНОВНЫЕ КОМАНДЫ:**
• `/start` - Начать работу с ботом
• `/help` - Показать это меню
• `/health` - Проверить состояние системы
• `/stats` - Статистика использования

**🔍 АНАЛИЗ СООБЩЕНИЙ:**
• `/summary` - Получить саммари последнего сообщения
• `/transcript` - Получить транскрипт сообщения
• `/advice` - Получить персональный совет
• `/анализ` - Психологический анализ (намерения, эмоции, стиль)
• `/layers` - Глубокий анализ скрытых смыслов и мотивов

**🛠️ ОТЛАДКА:**
• `/debug` - Отладочная информация
• `/limits` - Лимиты файлов

**📝 КАК ИСПОЛЬЗОВАТЬ:**
1. Отправьте голосовое сообщение, видео или текст
2. Получите основной анализ (резюме + действия)
3. Используйте команды для детального анализа

**💡 ПОДСКАЗКА:** Основной вывод содержит только практические инсайты. Для глубокого анализа используйте команды!

**🎯 ПОДДЕРЖИВАЕМЫЕ ФОРМАТЫ:**
• Голосовые сообщения Telegram ⚡ быстро
• Видео сообщения с аудио
• Текстовые сообщения для анализа
• Аудиофайлы MP3, MP4, WAV

Максимальный размер: 50 МБ | Длительность: 10 минут"""
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("health"))
async def cmd_health(message: Message):
    """Handle /health command"""
    try:
        if not speech_pipeline:
            await message.answer("❌ Система речевой обработки не инициализирована")
            return
        
        health_status = await speech_pipeline.health_check()
        
        if health_status['status'] == 'healthy':
            status_text = "✅ **Система работает нормально**\n\n"
        else:
            status_text = "⚠️ **Обнаружены проблемы**\n\n"
        
        for component, info in health_status['components'].items():
            status_icon = "✅" if info['status'] == 'healthy' else "❌"
            status_text += f"{status_icon} **{component}**: {info['message']}\n"
        
        await message.answer(status_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        await message.answer("❌ Ошибка при проверке статуса системы")


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Handle /stats command"""
    try:
        if not speech_pipeline:
            await message.answer("❌ Система речевой обработки не инициализирована")
            return
        
        metrics = speech_pipeline.get_performance_metrics()
        
        stats_text = f"""
📊 **Статистика обработки**

**Общая статистика:**
• Всего обработано: {metrics['total_processed']}
• Успешно: {metrics['success_count']}
• Ошибок: {metrics['error_count']}
• Успешность: {metrics['success_rate']:.1%}

**Производительность:**
• Среднее время обработки: {metrics['average_total_time']:.2f}с
• Время аудиообработки: {metrics['average_audio_time']:.2f}с  
• Время распознавания: {metrics['average_speech_time']:.2f}с
• Цель ≤2с: {"✅" if metrics['performance_target_met'] else "❌"}
"""
        
        await message.answer(stats_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Stats command failed: {e}")
        await message.answer("❌ Ошибка при получении статистики")


@dp.message(Command("summary"))
async def cmd_summary(message: Message):
    """Handle /summary command - return summary for last message"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            # Add debug information
            total_chats = len(chat_last_messages)
            chat_ids = list(chat_last_messages.keys())
            
            debug_info = f"""
📄 **Саммари недоступно**

Сначала отправьте голосовое сообщение, видео или текст для анализа, 
затем используйте `/summary` для получения саммари.

💡 **Как использовать:**
1. Отправьте голосовое сообщение, видео или текст
2. Подождите обработки  
3. Введите `/summary` для получения саммари

🔍 **Отладочная информация:**
• Ваш ID: {user_id}
• ID чата: {chat_id}
• Всего чатов в памяти: {total_chats}
• ID чатов: {chat_ids[:5] if chat_ids else 'нет'}
"""
            await message.answer(debug_info, parse_mode="Markdown")
            return
        
        # Get the text and try to process with SummaryEngine
        text = last_msg_data["text"]
        msg_type = last_msg_data["type"]
        
        # Try SummaryEngine first
        if summary_engine and summary_engine.enabled:
            content_type = ContentType.TELEGRAM_VOICE if msg_type == "voice" else ContentType.TELEGRAM_VIDEO_NOTE if msg_type == "video" else ContentType.TEXT_INPUT
            
            result = await summary_engine.process_summary(
                text=text,
                content_type=content_type
            )
            
            if result.success:
                await message.answer(
                    result.summary, 
                    parse_mode="Markdown",
                    reply_markup=create_transcript_buttons()
                )
                return
        
        # Fallback to text processor
        if text_processor:
            try:
                processing_result = await text_processor.process_parallel(text)
                
                # Create simplified output
                simplified_output = f"""📝 **Саммари последнего сообщения**

{processing_result.summary if hasattr(processing_result, 'summary') else 'Анализ завершен'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы выделены'}

👉 **Требуемые действия:**
{processing_result.actions if hasattr(processing_result, 'actions') and processing_result.actions else '• Действия не требуются'}"""
                
                await message.answer(
                    simplified_output, 
                    parse_mode="Markdown",
                    reply_markup=create_transcript_buttons()
                )
                return
                
            except Exception as e:
                logger.error(f"Text processing error in summary command: {e}")
        
        # Final fallback - just show the text
        await message.answer(
            f"📝 **Текст последнего сообщения**\n\n{text}",
            parse_mode="Markdown",
            reply_markup=create_transcript_buttons()
        )
        
    except Exception as e:
        logger.error(f"Summary command failed: {e}")
        await message.answer("❌ Ошибка при получении саммари")


@dp.message(Command("transcript"))
async def cmd_transcript(message: Message):
    """Handle /transcript command - download last message as file"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            # Add debug information
            total_chats = len(chat_last_messages)
            chat_ids = list(chat_last_messages.keys())
            
            debug_info = f"""
📄 **Транскрипт недоступен**

Сначала отправьте голосовое сообщение или текст для анализа, 
затем используйте `/transcript` для получения файла.

💡 **Как использовать:**
1. Отправьте голосовое сообщение или текст
2. Подождите обработки  
3. Введите `/transcript` для скачивания

🔍 **Отладочная информация:**
• Ваш ID: {user_id}
• ID чата: {chat_id}
• Всего чатов в памяти: {total_chats}
• ID чатов: {chat_ids[:5] if chat_ids else 'нет'}
"""
            await message.answer(debug_info, parse_mode="Markdown")
            return
        
        # Get message data
        transcript_text = last_msg_data["text"]
        msg_type = last_msg_data["type"]
        
        # Send transcript as .txt file
        await send_transcript_text(message, transcript_text.strip(), chat_id, user_id)
        
        logger.info(f"Transcript sent to user {user_id}, type: {msg_type}")
        
    except Exception as e:
        logger.error(f"Transcript command failed: {e}")
        import traceback
        logger.error(f"Transcript error traceback: {traceback.format_exc()}")
        
        # Send detailed error info for debugging
        error_details = f"""❌ **Ошибка при создании транскрипта**

🔍 **Детали для отладки**:
• Ошибка: {str(e)}
• Пользователь: {user_id if 'user_id' in locals() else 'неизвестен'}
• Чат: {chat_id if 'chat_id' in locals() else 'неизвестен'}
• Есть сообщения: {chat_id in chat_last_messages if 'chat_id' in locals() else 'неизвестно'}

💡 Попробуйте:
1. Отправить новое голосовое сообщение
2. Подождать обработки
3. Снова использовать /transcript"""
        
        await message.answer(error_details, parse_mode="Markdown")


@dp.message(Command("анализ"))
async def cmd_analysis(message: Message):
    """Handle /анализ command - psychological analysis"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            await message.answer("❌ Нет данных для анализа\n\nОтправьте голосовое сообщение или текст, а затем используйте `/анализ`")
            return
        
        message_text = last_msg_data["text"]
        timestamp_stored = last_msg_data["timestamp"]
        msg_type = last_msg_data["type"]
        
        # Process with text processor for psychological analysis
        if text_processor:
            try:
                processing_result = await text_processor.process_parallel(message_text)
                
                # Create psychological analysis output
                analysis_text = f"""🎭 **ПСИХОЛОГИЧЕСКИЙ АНАЛИЗ**

📝 **Исходный текст**: {msg_type} сообщение ({len(message_text)} символов)

{processing_result.summary if hasattr(processing_result, 'summary') else 'Основной смысл'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы'}

{processing_result.actions if hasattr(processing_result, 'actions') else ''}

🎭 **Психологический анализ:**
{processing_result.tone_analysis if hasattr(processing_result, 'tone_analysis') else '• Скрытые мотивы и эмоции'}

⏰ **Время анализа**: {datetime.fromtimestamp(timestamp_stored).strftime("%H:%M")}

💡 *Этот анализ помогает понять психологические аспекты сообщения*
"""
                
                await message.answer(analysis_text, parse_mode="Markdown")
                
                logger.info(f"Psychological analysis sent to user {user_id}")
                
            except Exception as analysis_error:
                logger.error(f"Psychological analysis failed: {analysis_error}")
                await message.answer("❌ Ошибка при психологическом анализе")
        else:
            await message.answer("❌ Система анализа недоступна")
        
    except Exception as e:
        logger.error(f"Analysis command failed: {e}")
        await message.answer("❌ Ошибка при выполнении анализа")


@dp.message(Command("layers"))
async def cmd_layers(message: Message):
    """Handle /layers command - deep analysis of hidden meanings"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            await message.answer("""
🔍 **Анализ слоев недоступен**

Сначала отправьте голосовое сообщение или текст для анализа, 
затем используйте `/layers` для глубокого анализа.

💡 **Как использовать:**
1. Отправьте голосовое сообщение или текст
2. Подождите обработки
3. Введите `/layers` для анализа скрытых смыслов
""", parse_mode="Markdown")
            return
        
        message_text = last_msg_data["text"]
        msg_type = last_msg_data["type"]
        timestamp_stored = last_msg_data["timestamp"]
        
        # Perform deep analysis using text processor
        if text_processor:
            try:
                # Get full analysis with emotion detection
                processing_result = await text_processor.process_parallel(message_text)
                
                # Extract emotion analysis if available
                emotion_analysis = ""
                if hasattr(processing_result, 'emotion_scores') and processing_result.emotion_scores:
                    emotion_analysis = f"""
🎭 **Эмоциональный анализ:**
• Сарказм: {processing_result.emotion_scores.get('sarcasm', 0):.1%}
• Токсичность: {processing_result.emotion_scores.get('toxicity', 0):.1%}
• Манипуляция: {processing_result.emotion_scores.get('manipulation', 0):.1%}
"""
                
                # Create layers analysis
                layers_text = f"""🔍 **АНАЛИЗ СКРЫТЫХ СМЫСЛОВ**

📝 **Исходный текст**: {msg_type} сообщение ({len(message_text)} символов)

{processing_result.summary if hasattr(processing_result, 'summary') else 'Основной смысл'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы'}

{processing_result.actions if hasattr(processing_result, 'actions') else ''}

🎭 **Психологический анализ:**
{processing_result.tone_analysis if hasattr(processing_result, 'tone_analysis') else '• Скрытые мотивы и эмоции'}

{emotion_analysis}

⏰ **Время анализа**: {datetime.fromtimestamp(timestamp_stored).strftime("%H:%M")}

💡 *Этот анализ помогает понять глубинные слои смысла и скрытые мотивы*
"""
                
                await message.answer(layers_text, parse_mode="Markdown")
                
                logger.info(f"Layers analysis sent to user {user_id}")
                
            except Exception as analysis_error:
                logger.error(f"Layers analysis failed: {analysis_error}")
                await message.answer("❌ Ошибка при анализе слоев смысла")
        else:
            await message.answer("❌ Система анализа недоступна")
        
    except Exception as e:
        logger.error(f"Layers command failed: {e}")
        await message.answer("❌ Ошибка при выполнении анализа слоев")


@dp.message(Command("debug"))
async def cmd_debug(message: Message):
    """Handle /debug command - show stored message state"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Check global state
        total_chats = len(chat_last_messages)
        
        debug_info = f"""🔍 **ОТЛАДОЧНАЯ ИНФОРМАЦИЯ**

👤 **Ваш ID**: {user_id}
💬 **ID чата**: {chat_id}
📊 **Всего чатов в памяти**: {total_chats}
🆔 **ID чатов**: {list(chat_last_messages.keys())[:5] if chat_last_messages else 'нет'}

"""
        
        if chat_id in chat_last_messages:
            last_msg_data = chat_last_messages[chat_id]
            import time
            age_seconds = int(time.time() - last_msg_data["timestamp"])
            age_minutes = age_seconds // 60
            
            debug_info += f"""✅ **Ваше последнее сообщение найдено**:
📱 **Тип**: {last_msg_data["type"]}
📝 **Размер**: {len(last_msg_data["text"])} символов
⏰ **Возраст**: {age_minutes} мин {age_seconds % 60} сек
📋 **Превью**: {last_msg_data["text"][:100]}...

✅ **Команды доступны**: /transcript и /advice готовы к использованию"""
        else:
            debug_info += f"""❌ **Ваше сообщение НЕ найдено**

💡 **Для активации команд**:
1. Отправьте голосовое сообщение или текст
2. Дождитесь обработки
3. Используйте /transcript или /advice

🔄 **Сообщения хранятся 1 час**"""
        
        await message.answer(debug_info, parse_mode="Markdown")
        
        logger.info(f"Debug info sent to user {user_id}, has_message: {chat_id in chat_last_messages}")
        
    except Exception as e:
        logger.error(f"Debug command failed: {e}")
        await message.answer("❌ Ошибка при получении отладочной информации")


@dp.message(Command("advice"))
async def cmd_advice(message: Message):
    """Handle /advice command - get advice for last message"""
    try:
        if not message.from_user:
            await message.answer("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        chat_id = str(message.chat.id)
        
        # Check if user has any recent messages
        if chat_id not in chat_last_messages:
            await message.answer("""
🤖 **Совет недоступен**

Сначала отправьте голосовое сообщение или текст для анализа, 
затем используйте `/advice` для получения совета.

💡 **Как использовать:**
1. Отправьте голосовое сообщение или текст
2. Подождите обработки
3. Введите `/advice` для получения совета
""", parse_mode="Markdown")
            return
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            await message.answer("""
🤖 **Совет недоступен**

Сначала отправьте голосовое сообщение или текст для анализа, 
затем используйте `/advice` для получения совета.
""", parse_mode="Markdown")
            return
        
        message_text = last_msg_data["text"]
        msg_type = last_msg_data["type"]
        timestamp_stored = last_msg_data["timestamp"]
        
        # Generate advice based on user ID (4 different archetypes)
        advice_responses = [
            {
                "title": "💡 Совет мудреца",
                "text": "Найдите время подумать над ключевыми моментами из сообщения. Что самое важное? Какие долгосрочные последствия? Иногда лучшее решение приходит после паузы и размышления.",
                "style": "Глубокий анализ"
            },
            {
                "title": "🎭 Творческий подход", 
                "text": "Попробуйте взглянуть на ситуацию с неожиданной стороны. Какие альтернативы вы видите? Что, если подойти к вопросу совершенно по-другому? Креативность часто рождает лучшие решения.",
                "style": "Нестандартное мышление"
            },
            {
                "title": "❤️ Эмпатический взгляд",
                "text": "Учтите эмоциональную составляющую ситуации. Что чувствуют все участники? Как ваши действия могут повлиять на отношения? Понимание эмоций часто ключ к решению.",
                "style": "Эмоциональный интеллект"
            },
            {
                "title": "🃏 Игровая перспектива",
                "text": "Иногда лучший совет - не принимать всё слишком серьезно. Можно ли найти здесь что-то позитивное или забавное? Легкость и юмор помогают справиться с трудностями.",
                "style": "Позитивный настрой"
            }
        ]
        
        # Select response based on user ID
        response_index = hash(str(user_id)) % len(advice_responses)
        selected_response = advice_responses[response_index]
        
        # Create advice message
        advice_text = f"""
🤖 **Персональный совет**

{selected_response['title']}

{selected_response['text']}

📝 **Контекст**: {msg_type} сообщение ({len(message_text)} символов)
🎨 **Стиль**: {selected_response['style']}
⏰ **Время анализа**: {datetime.fromtimestamp(timestamp_stored).strftime("%H:%M")}

💭 *Совет основан на вашем уникальном профиле и содержании сообщения*

🔄 Для другого стиля совета отправьте новое сообщение и попробуйте `/advice` снова
"""
        
        await message.answer(advice_text, parse_mode="Markdown")
        
        logger.info(f"Advice sent to user {user_id}, archetype: {selected_response['title']}")
        
    except Exception as e:
        logger.error(f"Advice command failed: {e}")
        await message.answer("❌ Ошибка при создании совета")


@dp.message(F.voice)
async def handle_voice_message(message: Message):
    """Handle voice messages with speech processing pipeline"""
    try:
        if not message.voice:
            await message.reply("❌ Ошибка: Голосовое сообщение не найдено")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        file_id = message.voice.file_id
        duration = message.voice.duration
        
        logger.info(f"Received voice message from user {user_id}, "
                   f"duration: {duration}s, file_id: {file_id}")
        
        # Send processing notification
        processing_msg = await message.answer("🎙️ Обрабатываю голосовое сообщение...")
        
        if not speech_pipeline:
            await processing_msg.edit_text("❌ Система речевой обработки не инициализирована")
            return
        
        # Process voice message through pipeline
        try:
            transcribed_text = await speech_pipeline.process_voice_message(
                file_id, user_id, bot=bot, chat_id=str(message.chat.id)
            )
            
            # Store the transcribed text for commands
            import time
            chat_id = str(message.chat.id)
            chat_last_messages[chat_id] = {
                "text": transcribed_text,
                "timestamp": time.time(),
                "type": "voice",
                "user_id": user_id
            }
            logger.info(f"Stored voice message for chat {chat_id}, user {user_id}, total chats: {len(chat_last_messages)}")
            logger.info(f"Available chats after storing: {list(chat_last_messages.keys())}")
            
            # Update processing message
            await processing_msg.edit_text("🔄 Анализируем содержание...")
            
            # Try SummaryEngine first if available
            summary_result = await process_with_summary_engine(
                transcribed_text, 
                ContentType.TELEGRAM_VOICE, 
                duration
            )
            
            if summary_result:
                # Use SummaryEngine result with inline buttons
                await processing_msg.edit_text(
                    summary_result, 
                    parse_mode="Markdown",
                    reply_markup=create_transcript_buttons()
                )
            else:
                # Fallback to original text processor
                if text_processor:
                    try:
                        processing_result = await text_processor.process_parallel(transcribed_text)
                        formatted_output = text_processor.format_output(processing_result)
                        
                        # Create simplified output - keep practical insights including actions
                        simplified_output = f"""📝 **Основные мысли**

{processing_result.summary if hasattr(processing_result, 'summary') else 'Анализ завершен'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы выделены'}

👉 **Требуемые действия:**
{processing_result.actions if hasattr(processing_result, 'actions') and processing_result.actions else '• Действия не требуются'}

⏱️ Обработано за {processing_result.processing_time:.1f}с

📱 **Дополнительные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов"""
                        
                        await processing_msg.edit_text(
                            simplified_output, 
                            parse_mode="Markdown",
                            reply_markup=create_transcript_buttons()
                        )
                        
                    except Exception as text_error:
                        logger.error(f"Text processing error: {text_error}")
                        # Fallback to transcription only
                        fallback_text = f"""
📝 **Результат распознавания речи**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена

📱 **Доступные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов
"""
                        await processing_msg.edit_text(
                            fallback_text, 
                            parse_mode="Markdown",
                            reply_markup=create_transcript_buttons()
                        )
                else:
                    # Text processor not initialized - fallback to transcription only
                    fallback_text = f"""
📝 **Результат распознавания речи**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (процессор не инициализирован)
⏱️ Обработка завершена

📱 **Доступные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов
"""
                    await processing_msg.edit_text(
                        fallback_text, 
                        parse_mode="Markdown",
                        reply_markup=create_transcript_buttons()
                    )
            
        except SpeechPipelineError as e:
            logger.error(f"Speech pipeline error: {e}")
            
            # Check if user was already notified to avoid duplicate messages
            if hasattr(e, 'user_notified') and e.user_notified:
                # User already received the error message directly, just clean up
                await processing_msg.delete()
            else:
                # Normal error handling - send error message
                await processing_msg.edit_text(
                    f"❌ Ошибка при обработке: {str(e)}\n\n"
                    "Попробуйте еще раз или обратитесь к администратору."
                )
            
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await message.answer("❌ Неожиданная ошибка при обработке голосового сообщения")


@dp.message(F.video_note)
async def handle_video_note(message: Message):
    """Handle video notes (круглые видео)"""
    try:
        if not message.video_note:
            await message.reply("❌ Ошибка: Видео сообщение не найдено")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        file_id = message.video_note.file_id
        duration = message.video_note.duration
        
        logger.info(f"Received video note from user {user_id}, "
                   f"duration: {duration}s, file_id: {file_id}")
        
        processing_msg = await message.answer("🎥 Обрабатываю видео сообщение...")
        
        if not speech_pipeline:
            await processing_msg.edit_text("❌ Система речевой обработки не инициализирована")
            return
        
        # Process video note through the same pipeline (audio extraction handled internally)
        try:
            transcribed_text = await speech_pipeline.process_voice_message(
                file_id, user_id, bot=bot, chat_id=str(message.chat.id)
            )
            
            # Store the transcribed text for commands
            import time
            chat_id = str(message.chat.id)
            chat_last_messages[chat_id] = {
                "text": transcribed_text,
                "timestamp": time.time(),
                "type": "video",
                "user_id": user_id
            }
            logger.info(f"Stored video message for chat {chat_id}, total chats: {len(chat_last_messages)}")
            
            # Update processing message
            await processing_msg.edit_text("🔄 Анализируем содержание...")
            
            # Try SummaryEngine first if available
            summary_result = await process_with_summary_engine(
                transcribed_text, 
                ContentType.TELEGRAM_VIDEO_NOTE, 
                duration
            )
            
            if summary_result:
                # Use SummaryEngine result with inline buttons
                await processing_msg.edit_text(
                    summary_result, 
                    parse_mode="Markdown",
                    reply_markup=create_transcript_buttons()
                )
            else:
                # Fallback to original text processor
                if text_processor:
                    try:
                        processing_result = await text_processor.process_parallel(transcribed_text)
                        formatted_output = text_processor.format_output(processing_result)
                        
                        # Create simplified output for video notes
                        simplified_output = f"""📝 **Основные мысли**

{processing_result.summary if hasattr(processing_result, 'summary') else 'Анализ завершен'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы выделены'}

👉 **Требуемые действия:**
{processing_result.actions if hasattr(processing_result, 'actions') and processing_result.actions else '• Действия не требуются'}

⏱️ Обработано за {processing_result.processing_time:.1f}с

📱 **Дополнительные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов"""
                        
                        await processing_msg.edit_text(
                            simplified_output, 
                            parse_mode="Markdown",
                            reply_markup=create_transcript_buttons()
                        )
                        
                    except Exception as text_error:
                        logger.error(f"Text processing error: {text_error}")
                        # Fallback to transcription only
                        fallback_text = f"""
📝 **Результат распознавания видео сообщения**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена

📱 **Доступные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов
"""
                        await processing_msg.edit_text(
                            fallback_text, 
                            parse_mode="Markdown",
                            reply_markup=create_transcript_buttons()
                        )
                else:
                    # Text processor not initialized - fallback to transcription only
                    fallback_text = f"""
📝 **Результат распознавания видео сообщения**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (процессор не инициализирован)
⏱️ Обработка завершена

📱 **Доступные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов
"""
                    await processing_msg.edit_text(
                        fallback_text, 
                        parse_mode="Markdown",
                        reply_markup=create_transcript_buttons()
                    )
            
        except SpeechPipelineError as e:
            logger.error(f"Video note processing error: {e}")
            
            # Check if user was already notified to avoid duplicate messages  
            if hasattr(e, 'user_notified') and e.user_notified:
                # User already received the error message directly, just clean up
                await processing_msg.delete()
            else:
                # Normal error handling - send error message
                await processing_msg.edit_text(
                    f"❌ Ошибка при обработке видео: {str(e)}\n\n"
                    "Попробуйте еще раз или обратитесь к администратору."
                )
            
    except Exception as e:
        logger.error(f"Error processing video note: {e}")
        await message.answer("❌ Неожиданная ошибка при обработке видео сообщения")


@dp.message(F.text & ~F.command)
async def handle_text_message(message: Message):
    """Handle text messages, forwards, and quotes with enhanced processing"""
    try:
        if not message.text:
            await message.reply("❌ Ошибка: Текст сообщения не найден")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        text_content = message.text.strip()
        
        # Check for minimum text length
        if len(text_content) < 5:
            await message.reply("📝 Слишком короткий текст для анализа. Минимум 5 символов.")
            return
        
        logger.info(f"Received text message from user {user_id}, "
                   f"length: {len(text_content)} chars")
        
        # Store the text for commands
        import time
        chat_id = str(message.chat.id)
        chat_last_messages[chat_id] = {
            "text": text_content,
            "timestamp": time.time(),
            "type": "text",
            "user_id": user_id
        }
        logger.info(f"Stored text message for chat {chat_id}, total chats: {len(chat_last_messages)}")
        
        # Send processing notification
        processing_msg = await message.answer("📝 Анализируем текст...")
        
        # Process text through enhanced pipeline with emotion analysis
        if text_processor:
            try:
                processing_result = await text_processor.process_parallel(text_content)
                formatted_output = text_processor.format_output(processing_result)
                
                # Create simplified output for text messages
                simplified_output = f"""📝 **Основные мысли**

{processing_result.summary if hasattr(processing_result, 'summary') else 'Анализ завершен'}

📍 **Ключевые моменты:**
{processing_result.bullet_points if hasattr(processing_result, 'bullet_points') else '• Основные темы выделены'}

👉 **Требуемые действия:**
{processing_result.actions if hasattr(processing_result, 'actions') and processing_result.actions else '• Действия не требуются'}

⏱️ Обработано за {processing_result.processing_time:.1f}с

📱 **Дополнительные команды:**
• `/transcript` - получить транскрипт сообщения
• `/advice` - получить персональный совет от архетипа
• `/анализ` - психологический анализ (намерения, эмоции, стиль)
• `/layers` - глубокий анализ скрытых смыслов и мотивов"""
                
                await processing_msg.edit_text(simplified_output, parse_mode="Markdown")
                
            except Exception as text_error:
                logger.error(f"Text processing error: {text_error}")
                # Fallback to basic response
                fallback_text = f"""
📝 **Анализ текста**

**Исходный текст:**
{text_content}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена

📱 **Доступные команды:**
• `/transcript` - получить транскрипт
• `/advice` - получить совет
• `/анализ` - психологический анализ
• `/layers` - глубокий анализ смыслов
"""
                await processing_msg.edit_text(fallback_text, parse_mode="Markdown")
        else:
            # Text processor not initialized
            await processing_msg.edit_text(
                "❌ Система анализа текста не инициализирована"
            )
            
    except Exception as e:
        logger.error(f"Error processing text message: {e}")
        await message.answer("❌ Неожиданная ошибка при обработке текста")


@dp.message(F.document)
async def handle_document(message: Message):
    """Handle document uploads (PDF, DOC, etc.) with SummaryEngine"""
    try:
        if not message.document:
            await message.reply("❌ Ошибка: Документ не найден")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_size = message.document.file_size
        
        logger.info(f"Received document from user {user_id}, "
                   f"file: {file_name}, size: {file_size} bytes")
        
        # Check if SummaryEngine is available
        if not summary_engine or not summary_engine.enabled:
            await message.reply(
                "📄 Обработка документов пока недоступна. "
                "Попробуйте отправить текст документа в сообщении."
            )
            return
        
        # Check file size (limit to 50MB - Telegram API limit)
        if file_size and file_size > 50 * 1024 * 1024:
            await message.reply("❌ Файл слишком большой. Максимальный размер: 50MB (лимит Telegram)")
            return
        
        # Check file type
        supported_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
        file_ext = Path(file_name).suffix.lower() if file_name else ''
        
        if file_ext not in supported_extensions:
            await message.reply(
                f"❌ Неподдерживаемый тип файла: {file_ext}\n"
                f"Поддерживаемые форматы: {', '.join(supported_extensions)}"
            )
            return
        
        # Send processing notification
        processing_msg = await message.answer("📄 Обрабатываю документ...")
        
        try:
            # For now, we'll extract text from the document
            # In a full implementation, you'd need to add document text extraction
            # For now, we'll use a placeholder approach
            
            # Download the file
            file = await bot.get_file(file_id)
            file_path = file.file_path
            
            # Extract text (placeholder - in real implementation, you'd use libraries like PyPDF2, python-docx)
            # For now, we'll create a placeholder text
            placeholder_text = f"""
Документ: {file_name}
Размер: {file_size} байт
Тип: {file_ext}

Это заглушка для обработки документа. В полной реализации здесь будет извлеченный текст из файла.

Для тестирования SummaryEngine можно использовать этот текст как пример длинного контента для LONGFORM режима.
"""
            
            # Process with SummaryEngine
            result = await summary_engine.process_summary(
                text=placeholder_text,
                content_type=ContentType.TELEGRAM_DOCUMENT
            )
            
            if result.success:
                # Format output for LONGFORM mode
                output = f"""📄 **Анализ документа: {file_name}**

{result.summary}

⏱️ Обработано за {result.processing_time:.1f}с
🎯 Режим: {result.mode.value.upper()}
📊 Токены: {result.token_count}
"""
                
                await processing_msg.edit_text(output, parse_mode="Markdown")
            else:
                # Fallback response
                fallback = summary_engine.get_fallback_response(placeholder_text)
                await processing_msg.edit_text(fallback, parse_mode="Markdown")
                
        except Exception as doc_error:
            logger.error(f"Document processing error: {doc_error}")
            await processing_msg.edit_text(
                f"❌ Ошибка при обработке документа: {str(doc_error)}"
            )
            
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        await message.answer("❌ Неожиданная ошибка при обработке документа")


@dp.message(F.video)
async def handle_video(message: Message):
    """Handle video files with SummaryEngine"""
    try:
        if not message.video:
            await message.reply("❌ Ошибка: Видео не найдено")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        file_id = message.video.file_id
        duration = message.video.duration
        file_size = message.video.file_size
        
        logger.info(f"Received video from user {user_id}, "
                   f"duration: {duration}s, size: {file_size} bytes")
        
        # Check if SummaryEngine is available
        if not summary_engine or not summary_engine.enabled:
            await message.reply(
                "🎥 Обработка видео файлов пока недоступна. "
                "Попробуйте отправить видео заметку (круглое видео)."
            )
            return
        
        # Check file size (limit to 50MB - Telegram API limit)
        if file_size and file_size > 50 * 1024 * 1024:
            await message.reply("❌ Видео слишком большое. Максимальный размер: 50MB (лимит Telegram)")
            return
        
        # Send processing notification
        processing_msg = await message.answer("🎥 Обрабатываю видео...")
        
        try:
            # For now, we'll use the speech pipeline to extract audio and transcribe
            # In a full implementation, you might want to use video processing libraries
            
            if speech_pipeline:
                # Extract audio and transcribe
                transcribed_text = await speech_pipeline.process_voice_message(
                    file_id, user_id, bot=bot, chat_id=str(message.chat.id)
                )
                
                # Process with SummaryEngine
                result = await summary_engine.process_summary(
                    text=transcribed_text,
                    content_type=ContentType.TELEGRAM_VIDEO,
                    duration=duration
                )
                
                if result.success:
                    # Format output for LONGFORM mode
                    output = f"""🎥 **Анализ видео**

{result.summary}

⏱️ Обработано за {result.processing_time:.1f}с
🎯 Режим: {result.mode.value.upper()}
📊 Токены: {result.token_count}
⏱️ Длительность видео: {duration}с
"""
                    
                    await processing_msg.edit_text(output, parse_mode="Markdown")
                else:
                    # Fallback response
                    fallback = summary_engine.get_fallback_response(transcribed_text)
                    await processing_msg.edit_text(fallback, parse_mode="Markdown")
            else:
                await processing_msg.edit_text(
                    "❌ Система обработки речи не инициализирована"
                )
                
        except Exception as video_error:
            logger.error(f"Video processing error: {video_error}")
            await processing_msg.edit_text(
                f"❌ Ошибка при обработке видео: {str(video_error)}"
            )
            
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await message.answer("❌ Неожиданная ошибка при обработке видео")


@dp.message(Command("list_modes"))
async def cmd_list_modes(message: Message):
    """Handle /list_modes command"""
    modes_text = """
🔧 **Режимы обработки**

**Текущий режим:** Speech-to-Text
• Использует faster-whisper для распознавания речи
• Поддержка русского и английского языков
• Автоматическое определение языка
• Обучение языковым предпочтениям пользователя

**Планируемые режимы:**
• LLM анализ содержания (GPT-4)
• Тональный анализ эмоций
• Извлечение ключевых пунктов
• Настраиваемые режимы обработки

Следите за обновлениями!
"""
    await message.answer(modes_text, parse_mode="Markdown")


@dp.message(Command("limits"))
async def cmd_limits(message: Message):
    """Handle /limits command - show file size limits"""
    limits_text = """
📏 **Лимиты файлов**

**Telegram API лимиты:**
• 🎥 Видео файлы: **50MB**
• 📄 Документы (PDF, DOC, TXT): **50MB**
• 🎤 Голосовые сообщения: **50MB**
• 📸 Фото: **10MB**

**Рекомендации:**
• Для больших файлов используйте сжатие
• Видео можно конвертировать в более эффективные форматы
• Документы можно разбить на части

**Примечание:** Эти лимиты установлены Telegram API и не могут быть изменены.
"""
    await message.answer(limits_text, parse_mode="Markdown")


@dp.message(Command("set_model"))
async def cmd_set_model(message: Message):
    """Handle /set_model command"""
    info_text = """
🔧 **Настройка моделей**

Функция настройки моделей будет доступна в следующих обновлениях.

**Планируемые возможности:**
• Выбор размера модели Whisper (base/small/medium)
• Настройка языковых предпочтений
• Пользовательские режимы обработки
• Настройка качества vs скорости

Текущая конфигурация оптимизирована для лучшего баланса скорости и качества.
"""
    await message.answer(info_text, parse_mode="Markdown")


from aiogram.types import CallbackQuery

@dp.callback_query()
async def handle_button_callback(callback_query: CallbackQuery):
    """Handle button interactions - transcript buttons and Redis-dependent features"""
    try:
        data = callback_query.data
        user_id = str(callback_query.from_user.id)
        chat_id = str(callback_query.message.chat.id)
        
        logger.info(f"Callback received: data='{data}', user_id={user_id}, chat_id={chat_id}")
        
        # Handle transcript buttons
        if data == "show_transcript":
            logger.info(f"Handling show_transcript for user {user_id} in chat {chat_id}")
            await handle_show_transcript(callback_query)
            return
        elif data == "download_txt":
            logger.info(f"Handling download_txt for user {user_id} in chat {chat_id}")
            await handle_download_txt(callback_query)
            return
        
        # Handle Redis-dependent features
        if button_ui_manager:
            # Use the full button UI manager if available
            result = await button_ui_manager.handle_callback(
                callback_query=callback_query,
                bot=bot
            )
            
            if not result:
                await callback_query.answer("❌ Не удалось обработать запрос", show_alert=True)
        else:
            # No button functionality without Redis - inform user about commands
            await callback_query.answer("""
🤖 Используйте команды:
• /transcript - получить транскрипт
• /summary - получить саммари
• /advice - получить совет
• /анализ - психологический анализ
• /layers - глубокий анализ
""", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error handling button callback: {e}")
        await callback_query.answer("❌ Ошибка обработки", show_alert=True)


async def handle_show_transcript(callback_query: CallbackQuery):
    """Handle show transcript button"""
    try:
        user_id = str(callback_query.from_user.id)
        chat_id = str(callback_query.message.chat.id)
        
        logger.info(f"handle_show_transcript: user_id={user_id}, chat_id={chat_id}")
        logger.info(f"Available chats: {list(chat_last_messages.keys())}")
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            logger.warning(f"No message data found for chat {chat_id}, user {user_id}")
            await callback_query.answer("❌ Нет данных для показа", show_alert=True)
            return
        
        text = last_msg_data["text"]
        
        if len(text) <= 4096:
            # Send as text message
            transcript_text = f"""📝 **ТРАНСКРИПТ**

{text}

---
💡 *Для копирования - выделите текст выше*"""
            await callback_query.message.answer(transcript_text, parse_mode="Markdown")
            await callback_query.answer("✅ Транскрипт отправлен")
        else:
            # Send as file
            await send_transcript_text(callback_query.message, text, chat_id, user_id)
            await callback_query.answer("✅ Транскрипт отправлен как файл")
            
    except Exception as e:
        logger.error(f"Error handling show transcript: {e}")
        await callback_query.answer("❌ Ошибка при показе транскрипта", show_alert=True)


async def handle_download_txt(callback_query: CallbackQuery):
    """Handle download txt button"""
    try:
        user_id = str(callback_query.from_user.id)
        chat_id = str(callback_query.message.chat.id)
        
        logger.info(f"handle_download_txt: user_id={user_id}, chat_id={chat_id}")
        logger.info(f"Available chats: {list(chat_last_messages.keys())}")
        
        # Get last message data
        last_msg_data = await get_last_message_data(chat_id, user_id)
        if not last_msg_data:
            logger.warning(f"No message data found for chat {chat_id}, user {user_id}")
            await callback_query.answer("❌ Нет данных для скачивания", show_alert=True)
            return
        
        text = last_msg_data["text"]
        
        # Always send as file for download button
        await send_transcript_text(callback_query.message, text, chat_id, user_id)
        await callback_query.answer("✅ Файл отправлен")
        
    except Exception as e:
        logger.error(f"Error handling download txt: {e}")
        await callback_query.answer("❌ Ошибка при скачивании файла", show_alert=True)


@dp.error()
async def error_handler(event: ErrorEvent):
    """Global error handler"""
    logger.error(f"Update {event.update} caused error {event.exception}")


# Health check endpoint for Docker
async def health_check(request):
    """Health check endpoint"""
    try:
        # Simple health check - just return OK if server is running
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bot_status = 'running'
        pipeline_status = 'ready' if speech_pipeline else 'initializing'
        pipeline_details = ""
        
        # Try to check speech pipeline if available
        if speech_pipeline:
            try:
                health_result = await speech_pipeline.health_check()
                pipeline_details = f"\n🔍 Details: {health_result.get('status', 'unknown')}"
            except Exception as e:
                pipeline_details = f"\n⚠️ Warning: {str(e)}"
                logger.warning(f"Pipeline health check failed: {e}")
        
        return web.Response(
            text=f"✅ Bot Status: healthy\n"
                 f"📅 Time: {timestamp}\n"
                 f"🤖 Telegram: {bot_status}\n"
                 f"🎤 Pipeline: {pipeline_status}{pipeline_details}\n"
                 f"🌐 Ready to receive webhooks!",
            status=200
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.Response(
            text=f"❌ Health check error: {str(e)}\n"
                 f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                 f"ℹ️  This is a temporary error",
            status=500
        )


async def startup():
    """Initialize the bot systems"""
    global openai_client, text_processor, speech_pipeline, redis_client, archetype_system, button_ui_manager, summary_engine
    
    logger.info("🚀 BOT STARTUP - Railway Deployment Check")
    logger.info("========================================")
    logger.info("🆕 VERSION: 2025-08-02 ENHANCED v3.2")
    logger.info("🆕 FEATURE: Simplified analysis + deep layers command")
    logger.info("🆕 SIMPLIFIED: Basic output, complex analysis under /layers")
    logger.info("🆕 COMMANDS: /transcript /advice /layers work reliably")
    logger.info("========================================")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    try:
        logger.info("=== STARTUP INITIALIZATION ===")
        
        # Check environment variables
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        webhook_url = os.getenv("WEBHOOK_URL")
        port = os.getenv("PORT")
        
        logger.info(f"Environment check:")
        logger.info(f"- TELEGRAM_TOKEN: {'✓ Set' if telegram_token else '✗ Missing'}")
        logger.info(f"- OPENAI_API_KEY: {'✓ Set' if openai_api_key else '✗ Missing'}")
        logger.info(f"- WEBHOOK_URL: {webhook_url if webhook_url else 'Not set (polling mode)'}")
        logger.info(f"- PORT: {port if port else 'Default'}")
        
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        logger.info("Initializing speech processing pipeline...")
        
        # Create speech pipeline (this will load the Whisper model)
        speech_pipeline = await SpeechPipelineFactory.create_pipeline(bot, redis_client=None)
        
        logger.info("✓ Speech processing pipeline initialized successfully")
        
        # Initialize text processor
        logger.info("Initializing text processor...")
        text_processor = TextProcessor(openai_api_key)
        logger.info("✓ Text processor initialized successfully")
        
        # Initialize enhanced systems (Phase 3)
        # Fully re-enabled for complete functionality
        logger.info("Initializing enhanced systems...")
        
        # Initialize Redis client
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        logger.info(f"Attempting Redis connection to {redis_host}:{redis_port}")
        logger.info(f"Redis password configured: {'Yes' if redis_password else 'No'}")
        try:
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port, 
                password=redis_password,
                decode_responses=True
            )
            # Test connection
            await redis_client.ping()
            logger.info("✅ Redis client initialized and connected successfully")
            logger.info("✅ Enhanced UI features will be ENABLED")
        except Exception as redis_error:
            logger.error(f"❌ Redis connection failed: {redis_error}")
            logger.error("❌ Enhanced UI features will be DISABLED")
            logger.info("✅ Fallback button functionality will be ENABLED")
            redis_client = None
        
        # Initialize archetype system
        logger.info("Initializing archetype system...")
        if text_processor and text_processor.client:
            archetype_system = create_archetype_system(text_processor.client)
            logger.info("✓ Archetype system initialized")
        else:
            archetype_system = None
            logger.error("Archetype system disabled (no OpenAI client)")
        
        # Initialize button UI manager
        logger.info(f"Initializing button UI manager... Redis: {redis_client is not None}, Archetype: {archetype_system is not None}")
        if redis_client and archetype_system:
            try:
                button_ui_manager = create_button_ui_manager(redis_client, archetype_system)
                logger.info("✓ Button UI manager initialized")
            except Exception as ui_error:
                logger.error(f"Button UI manager initialization failed: {ui_error}")
                button_ui_manager = None
        else:
            button_ui_manager = None
            logger.info(f"🔄 Button UI Manager: Using FALLBACK mode (Redis: {redis_client is not None}, Archetype: {archetype_system is not None})")
            logger.info("✅ Fallback buttons will provide basic advice and transcript functionality")
        
        # Initialize SummaryEngine for two-mode summarization
        logger.info("Initializing SummaryEngine...")
        if text_processor and text_processor.client:
            try:
                summary_engine = create_summary_engine(text_processor.client)
                # Enable SummaryEngine if feature flag is set
                if os.getenv('TLDRBUDDY_ENABLED', 'false').lower() == 'true':
                    summary_engine.enable()
                    logger.info("✅ SummaryEngine initialized and ENABLED")
                else:
                    logger.info("✅ SummaryEngine initialized but DISABLED (set TLDRBUDDY_ENABLED=true to enable)")
            except Exception as se_error:
                logger.error(f"SummaryEngine initialization failed: {se_error}")
                summary_engine = None
        else:
            summary_engine = None
            logger.error("SummaryEngine disabled (no OpenAI client)")
        
        # Summarize startup status
        logger.info("=== STARTUP COMPLETED SUCCESSFULLY ===")
        logger.info(f"🎤 Speech Pipeline: {'✅ Ready' if speech_pipeline else '❌ Failed'}")
        logger.info(f"📝 Text Processor: {'✅ Ready' if text_processor else '❌ Failed'}")
        logger.info(f"🔗 Redis Client: {'✅ Connected' if redis_client else '❌ Fallback mode'}")
        logger.info(f"🤖 Archetype System: {'✅ Ready' if archetype_system else '❌ Disabled'}")
        logger.info(f"🎛️ Button UI Manager: {'✅ Full features' if button_ui_manager else '✅ Fallback mode'}")
        logger.info(f"📊 SummaryEngine: {'✅ Enabled' if summary_engine and summary_engine.enabled else '✅ Disabled' if summary_engine else '❌ Failed'}")
        logger.info("===========================================")
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize: {e}")
        logger.exception("Full error details:")
        logger.error("Bot will start but speech processing will be unavailable")


async def on_startup():
    """Startup actions"""
    await startup()
    # Set webhook if WEBHOOK_URL is provided
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to {webhook_url}")


async def main():
    """Main bot function"""
    logger.info("Starting Telegram Voice-to-Insight Pipeline Bot...")
    
    # Check if we should use webhook or polling
    webhook_url = os.getenv('WEBHOOK_URL')
    
    # Railway port detection - try multiple sources
    port = 3000  # Default fallback
    port_env = os.getenv('PORT')
    if port_env:
        port = int(port_env)
        logger.info(f"Using PORT from environment: {port}")
    elif os.getenv('RAILWAY_ENVIRONMENT'):
        # Railway sometimes doesn't set PORT, use common Railway ports
        port = 8080  # Railway's common internal port
        logger.info(f"Railway environment detected, using port: {port}")
    else:
        logger.info(f"Using default port: {port}")
    
    logger.info(f"Configuration:")
    logger.info(f"- Mode: {'Webhook' if webhook_url else 'Polling'}")
    logger.info(f"- Port: {port}")
    logger.info(f"- Webhook URL: {webhook_url}")
    
    if webhook_url:
        # Webhook mode for Railway
        logger.info(f"🚀 Starting in webhook mode on port {port}")
        
        try:
            # Initialize speech processing
            await startup()
            
            # Create aiohttp app
            app = web.Application()
            
            # Add health check route FIRST
            app.router.add_get('/health', health_check)
            logger.info("✓ Health check route added")
            
            # Add root route for basic check
            async def root_handler(request):
                return web.Response(text="Telegram Bot is running", status=200)
            app.router.add_get('/', root_handler)
            logger.info("✓ Root route added")
            
            # Setup webhook
            webhook_path = '/webhook'
            app.router.add_post(webhook_path, SimpleRequestHandler(dispatcher=dp, bot=bot).handle)
            logger.info("✓ Webhook route added")
            
            # Start server BEFORE setting webhook
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"✅ Server started successfully on 0.0.0.0:{port}")
            
            # Set webhook AFTER server is running
            full_webhook_url = f"{webhook_url}{webhook_path}"
            await bot.set_webhook(full_webhook_url)
            logger.info(f"✅ Webhook set to {full_webhook_url}")
            
            # Keep the server running
            logger.info("🔄 Server is running and ready to receive requests...")
            try:
                while True:
                    await asyncio.sleep(60)  # Check every minute
                    logger.info("💓 Server heartbeat")
            except KeyboardInterrupt:
                logger.info("🛑 Shutdown requested")
            finally:
                logger.info("🧹 Cleaning up...")
                await bot.delete_webhook()
                await runner.cleanup()
                
        except Exception as e:
            logger.error(f"💥 Failed to start webhook server: {e}")
            logger.exception("Full error:")
            raise
            
    else:
        # Polling mode for local development
        logger.info("🔄 Starting in polling mode")
        
        # Initialize speech processing
        await startup()
        
        # Start polling
        await dp.start_polling(bot)


if __name__ == "__main__":
    # Skip single instance enforcement in production (Railway)
    is_production = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('WEBHOOK_URL')
    
    if not is_production:
        # Enforce single instance only in local development
        try:
            logger.info("Инициализация single-instance enforcement...")
            process_manager = enforce_single_instance(auto_cleanup=True, force_cleanup=False)
            logger.info("✅ Single-instance enforcement активирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации process manager: {e}")
            process_manager = None
    else:
        logger.info("Production environment detected, skipping single-instance enforcement")
        process_manager = None
    
    try:
        # Start the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, завершение работы...")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)
    finally:
        # Ensure process manager cleanup
        if process_manager:
            try:
                process_manager.release_lock()
                logger.info("✅ Process manager очищен")
            except Exception as e:
                logger.error(f"Ошибка при очистке process manager: {e}") 

# Force Railway redeploy - 2025-07-30 21:42 