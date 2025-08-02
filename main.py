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

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ErrorEvent
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
    help_text = """
📖 **Справка по использованию**

**Основные функции:**
1. **Анализ голосовых сообщений** - отправьте войс для получения текста
2. **Анализ видео сообщений** - поддержка круглых видео с аудио
3. **Умное распознавание языка** - автоматическое определение русского/английского
4. **Обучение предпочтениям** - система запоминает ваш язык для ускорения

**Технические особенности:**
• Использует faster-whisper для максимальной точности
• Оптимизирован для быстрой обработки
• Поддерживает различные аудиоформаты (OGG, MP3, MP4, WAV)
• Кеширование результатов для повторных запросов

**Поддерживаемые форматы:**
• Голосовые сообщения Telegram (OGG Opus) ⚡ быстро
• Аудиофайлы MP3, MP4, WAV 🔄 с конвертацией
• Видео сообщения с аудиодорожкой

Максимальный размер файла: 50 МБ
Максимальная длительность: 10 минут
"""
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
            
            # Update processing message
            await processing_msg.edit_text("🔄 Анализируем содержание...")
            
            # Process text through DEFAULT and TONE modes
            if text_processor:
                try:
                    processing_result = await text_processor.process_parallel(transcribed_text)
                    formatted_output = text_processor.format_output(processing_result)
                    
                    # Add enhanced button UI if available
                    reply_markup = None
                    # Temporarily show buttons even with emotion errors for testing
                    if button_ui_manager is not None: # and processing_result.emotion_scores:
                        try:
                            # Use dummy emotion scores if real ones failed
                            emotion_scores = processing_result.emotion_scores or {'sarcasm': 0.3, 'toxicity': 0.2, 'manipulation': 0.1}
                            emotion_levels = processing_result.emotion_levels or {'sarcasm': 'средний', 'toxicity': 'низкий', 'manipulation': 'низкий'}
                            
                            reply_markup = await button_ui_manager.create_initial_buttons(
                                user_id=int(user_id),
                                message_id=processing_msg.message_id,
                                emotion_scores=emotion_scores,
                                emotion_levels=emotion_levels,
                                original_text=transcribed_text,
                                transcript_available=True,
                                transcript_file_id=file_id
                            )
                        except Exception as button_error:
                            logger.error(f"Button UI creation failed: {button_error}")
                            import traceback
                            logger.error(f"Button error traceback: {traceback.format_exc()}")
                            reply_markup = None
                    else:
                        logger.warning("Button UI Manager is None - buttons will not be created")
                        logger.info("🔥🔥🔥 CREATING FALLBACK BUTTONS WITHOUT REDIS 🔥🔥🔥")
                        # Create simple buttons without Redis as fallback
                        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                            [
                                InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
                                InlineKeyboardButton(text="📄 транскрипт", callback_data="transcript_simple")
                            ]
                        ])
                        logger.info("✅✅✅ Created simple buttons without Redis ✅✅✅")
                    
                    # Edit the processing message with final result and buttons
                    await processing_msg.edit_text(formatted_output, reply_markup=reply_markup, parse_mode="Markdown")
                    
                except Exception as text_error:
                    logger.error(f"Text processing error: {text_error}")
                    # Fallback to transcription only
                    fallback_text = f"""
📝 **Результат распознавания речи**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена
"""
                    # Add simple buttons for voice messages
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    simple_buttons = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
                            InlineKeyboardButton(text="📄 транскрипт", callback_data="transcript_simple")
                        ]
                    ])
                    await processing_msg.edit_text(fallback_text, reply_markup=simple_buttons, parse_mode="Markdown")
            else:
                # Text processor not initialized - fallback to transcription only
                fallback_text = f"""
📝 **Результат распознавания речи**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (процессор не инициализирован)
⏱️ Обработка завершена
"""
                await processing_msg.edit_text(fallback_text, parse_mode="Markdown")
            
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
            
            # Update processing message
            await processing_msg.edit_text("🔄 Анализируем содержание...")
            
            # Process text through DEFAULT and TONE modes
            if text_processor:
                try:
                    processing_result = await text_processor.process_parallel(transcribed_text)
                    formatted_output = text_processor.format_output(processing_result)
                    
                    # Edit the processing message with final result
                    # Add simple buttons for user interaction
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    simple_buttons = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
                            InlineKeyboardButton(text="📄 транскрипт", callback_data="transcript_simple")
                        ]
                    ])
                    await processing_msg.edit_text(formatted_output, reply_markup=simple_buttons, parse_mode="Markdown")
                    
                except Exception as text_error:
                    logger.error(f"Text processing error: {text_error}")
                    # Fallback to transcription only
                    fallback_text = f"""
📝 **Результат распознавания видео сообщения**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена
"""
                    await processing_msg.edit_text(fallback_text, parse_mode="Markdown")
            else:
                # Text processor not initialized - fallback to transcription only
                fallback_text = f"""
📝 **Результат распознавания видео сообщения**

**Текст:**
{transcribed_text}

⚠️ Анализ недоступен (процессор не инициализирован)
⏱️ Обработка завершена
"""
                await processing_msg.edit_text(fallback_text, parse_mode="Markdown")
            
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
        
        # Send processing notification
        processing_msg = await message.answer("📝 Анализируем текст...")
        
        # Process text through enhanced pipeline with emotion analysis
        if text_processor:
            try:
                processing_result = await text_processor.process_parallel(text_content)
                formatted_output = text_processor.format_output(processing_result)
                
                # Add enhanced button UI if available
                reply_markup = None
                # Temporarily show buttons even with emotion errors for testing
                logger.info(f"Button UI Manager available: {button_ui_manager is not None}")
                if button_ui_manager is not None: # and processing_result.emotion_scores:
                    try:
                        logger.info(f"Attempting to create buttons for text message...")
                        # Use dummy emotion scores if real ones failed
                        emotion_scores = processing_result.emotion_scores or {'sarcasm': 0.3, 'toxicity': 0.2, 'manipulation': 0.1}
                        emotion_levels = processing_result.emotion_levels or {'sarcasm': 'средний', 'toxicity': 'низкий', 'manipulation': 'низкий'}
                        
                        reply_markup = await button_ui_manager.create_initial_buttons(
                            user_id=int(user_id),
                            message_id=processing_msg.message_id,
                            emotion_scores=emotion_scores,
                            emotion_levels=emotion_levels,
                            original_text=text_content,
                            transcript_available=False,
                            transcript_file_id=None
                        )
                        logger.info(f"Buttons created successfully: {reply_markup is not None}")
                    except Exception as button_error:
                        logger.warning(f"Button UI creation failed: {button_error}")
                        reply_markup = None
                else:
                    logger.warning("Button UI Manager is None - creating simple buttons")
                    logger.info("🔥🔥🔥 CREATING FALLBACK BUTTONS WITHOUT REDIS 🔥🔥🔥")
                    # Create simple buttons without Redis as fallback
                    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                        [
                            InlineKeyboardButton(text="🤖 совет", callback_data="advice_simple"),
                        ]
                    ])
                    logger.info("✅✅✅ Created simple buttons without Redis for text ✅✅✅")
                
                # Edit the processing message with final result and buttons
                await processing_msg.edit_text(formatted_output, reply_markup=reply_markup, parse_mode="Markdown")
                
            except Exception as text_error:
                logger.error(f"Text processing error: {text_error}")
                # Fallback to basic response
                fallback_text = f"""
📝 **Анализ текста**

**Исходный текст:**
{text_content}

⚠️ Анализ недоступен (ошибка обработки)
⏱️ Обработка завершена
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
    """Handle button interactions with enhanced archetype responses"""
    try:
        if button_ui_manager:
            # Use the full button UI manager if available
            result = await button_ui_manager.handle_callback(
                callback_query=callback_query,
                bot=bot
            )
            
            if not result:
                await callback_query.answer("❌ Не удалось обработать запрос", show_alert=True)
        else:
            # Simple fallback for when Redis is not available
            callback_data = callback_query.data
            
            if callback_data == "advice_simple":
                await callback_query.answer("💡 Совет: Эта функция временно недоступна без Redis", show_alert=True)
            elif callback_data == "transcript_simple":
                await callback_query.answer("📄 Транскрипт: Эта функция временно недоступна без Redis", show_alert=True)
            else:
                await callback_query.answer("❓ Неизвестная команда", show_alert=True)
                
    except Exception as e:
        logger.error(f"Error handling button callback: {e}")
        await callback_query.answer("❌ Ошибка обработки", show_alert=True)


# Simple button callback handler for Railway compatibility
@dp.callback_query(lambda callback_query: callback_query.data in ["advice_simple", "transcript_simple"])
async def handle_simple_buttons(callback_query: CallbackQuery):
    """Handle simple button callbacks without Redis"""
    try:
        callback_data = callback_query.data
        
        if callback_data == "advice_simple":
            await callback_query.answer("💡 Совет: Функции советов пока разрабатываются. Скоро будут готовы архетипы ответов!", show_alert=True)
        elif callback_data == "transcript_simple":
            await callback_query.answer("📄 Транскрипт: Функция скачивания транскриптов в разработке. Скоро будет доступна!", show_alert=True)
        else:
            await callback_query.answer("❓ Неизвестная команда", show_alert=True)
            
        logger.info(f"Button callback handled: {callback_data}")
        
    except Exception as e:
        logger.error(f"Error handling simple button callback: {e}")
        await callback_query.answer("❌ Ошибка обработки кнопки", show_alert=True)


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
    global openai_client, text_processor, speech_pipeline, redis_client, archetype_system, button_ui_manager
    
    logger.info("🚀 BOT STARTUP - Railway Deployment Check")
    logger.info("========================================")
    logger.info("🆕 VERSION: 2025-08-02 BUTTONS FALLBACK v1.5")
    logger.info("🆕 EXPECTED: Fallback buttons without Redis")
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
        try:
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port, 
                password=redis_password,
                decode_responses=True
            )
            # Test connection
            await redis_client.ping()
            logger.info("✓ Redis client initialized and connected")
        except Exception as redis_error:
            logger.error(f"Redis connection failed: {redis_error}")
            logger.error("Enhanced UI features will be disabled")
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
            logger.error(f"Button UI disabled - Redis available: {redis_client is not None}, Archetype available: {archetype_system is not None}")
        
        logger.info("=== STARTUP COMPLETED SUCCESSFULLY ===")
        
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