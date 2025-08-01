#!/usr/bin/env python3
"""
Test Script for Telegram Voice-to-Insight Pipeline
Allows testing enhanced features without affecting production bot
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ErrorEvent, CallbackQuery
from dotenv import load_dotenv

# Import modules
from text_processor import TextProcessor
from emotion_analyzer import EmotionAnalyzer
from archetype_system import ArchetypeSystem, create_archetype_system
from button_ui_manager import ButtonUIManager, create_button_ui_manager
import redis.asyncio as redis

# Load test environment
load_dotenv('.env.test')

# Configure logging for test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TEST - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/test_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Test bot configuration
TELEGRAM_TOKEN = os.getenv('TEST_TELEGRAM_TOKEN') or os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not TELEGRAM_TOKEN:
    logger.error("TEST_TELEGRAM_TOKEN or TELEGRAM_TOKEN not found")
    sys.exit(1)

if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found")
    sys.exit(1)

# Initialize test bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Global instances
text_processor = None
redis_client = None
archetype_system = None
button_ui_manager = None

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command for test bot"""
    welcome_text = """
🧪 **TEST: Enhanced Telegram Bot**

Привет! Это тестовая версия бота с новыми возможностями:

**Новые функции:**
• 📝 Анализ текстовых сообщений
• 😈 Определение эмоций (сарказм, токсичность, манипуляция)
• 🤖 Архетипные советы (EMPATH, META-SAGE, TRICKSTER, CRAZY-WISDOM)
• 🎛️ Интерактивные кнопки для выбора стиля

**Отправьте любой текст для тестирования!**
"""
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(F.text & ~F.command)
async def handle_test_text_message(message: Message):
    """Handle text messages for testing enhanced features"""
    try:
        if not message.text:
            await message.reply("❌ Ошибка: Текст сообщения не найден")
            return
            
        if not message.from_user:
            await message.reply("❌ Ошибка: Информация о пользователе недоступна")
            return
            
        user_id = str(message.from_user.id)
        text_content = message.text.strip()
        
        if len(text_content) < 5:
            await message.reply("📝 Слишком короткий текст для анализа. Минимум 5 символов.")
            return
        
        logger.info(f"TEST: Processing text from user {user_id}, length: {len(text_content)}")
        
        processing_msg = await message.answer("🧪 **TEST MODE**: Анализируем текст с новыми возможностями...")
        
        if text_processor:
            try:
                # Process with enhanced pipeline
                processing_result = await text_processor.process_parallel(text_content)
                formatted_output = text_processor.format_output(processing_result)
                
                # Add test prefix
                test_output = f"🧪 **ТЕСТОВЫЕ РЕЗУЛЬТАТЫ**:\n\n{formatted_output}"
                
                # Add enhanced button UI if available
                reply_markup = None
                if button_ui_manager is not None and processing_result.emotion_scores:
                    try:
                        reply_markup = await button_ui_manager.create_initial_buttons(
                            user_id=int(user_id),
                            message_id=processing_msg.message_id,
                            emotion_scores=processing_result.emotion_scores,
                            emotion_levels=processing_result.emotion_levels or {},
                            original_text=text_content,
                            transcript_available=False,
                            transcript_file_id=None
                        )
                        test_output += "\n\n🎛️ **Новые интерактивные кнопки готовы!**"
                    except Exception as button_error:
                        logger.warning(f"Button UI creation failed: {button_error}")
                        test_output += f"\n\n⚠️ Button UI disabled: {button_error}"
                
                await processing_msg.edit_text(test_output, reply_markup=reply_markup, parse_mode="Markdown")
                
            except Exception as text_error:
                logger.error(f"Test processing error: {text_error}")
                fallback_text = f"""
🧪 **TEST ERROR**

**Исходный текст:**
{text_content}

⚠️ Ошибка: {str(text_error)}
"""
                await processing_msg.edit_text(fallback_text, parse_mode="Markdown")
        else:
            await processing_msg.edit_text("❌ TEST: Text processor not initialized")
            
    except Exception as e:
        logger.error(f"Test handler error: {e}")
        await message.answer("❌ TEST: Неожиданная ошибка")

@dp.callback_query()
async def handle_test_button_callback(callback_query: CallbackQuery):
    """Handle button callbacks for testing"""
    try:
        logger.info(f"TEST: Button callback from user {callback_query.from_user.id}")
        if button_ui_manager is not None:
            await button_ui_manager.handle_callback(callback_query, bot)
        else:
            await callback_query.answer("❌ TEST: Button UI not available", show_alert=True)
    except Exception as e:
        logger.error(f"TEST: Error handling button callback: {e}")
        await callback_query.answer("❌ TEST: Ошибка обработки", show_alert=True)

@dp.error()
async def test_error_handler(event: ErrorEvent):
    """Test error handler"""
    logger.error(f"TEST: Update {event.update} caused error {event.exception}")

async def init_test_systems():
    """Initialize test systems"""
    global text_processor, redis_client, archetype_system, button_ui_manager
    
    try:
        logger.info("🧪 === TEST INITIALIZATION ===")
        
        # Initialize text processor
        logger.info("Initializing text processor...")
        if OPENAI_API_KEY:
            text_processor = TextProcessor(OPENAI_API_KEY)
            logger.info("✓ Text processor initialized")
        else:
            logger.error("OPENAI_API_KEY is required")
            raise ValueError("OPENAI_API_KEY not found")
        
        # Initialize Redis (optional for testing)
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_password = os.getenv("REDIS_PASSWORD")
            
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True
            )
            await redis_client.ping()
            logger.info("✓ Redis connected for testing")
        except Exception as redis_error:
            logger.warning(f"Redis connection failed (testing without buttons): {redis_error}")
            redis_client = None
        
        # Initialize archetype system
        if text_processor and text_processor.client:
            archetype_system = create_archetype_system(text_processor.client)
            logger.info("✓ Archetype system initialized")
        else:
            logger.warning("Archetype system disabled")
            archetype_system = None
        
        # Initialize button UI manager
        if redis_client and archetype_system:
            button_ui_manager = create_button_ui_manager(redis_client, archetype_system)
            logger.info("✓ Button UI manager initialized")
        else:
            logger.warning("Button UI disabled (testing basic features only)")
            button_ui_manager = None
        
        logger.info("🧪 === TEST INITIALIZATION COMPLETE ===")
        
    except Exception as e:
        logger.error(f"Test initialization failed: {e}")
        logger.exception("Full error details:")

async def main():
    """Main test function"""
    logger.info("🧪 Starting TEST bot...")
    
    try:
        # Initialize systems
        await init_test_systems()
        
        # Start polling (should work even if webhook is active on production)
        logger.info("🧪 Starting test polling...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Test bot error: {e}")
        logger.exception("Full error details:")

if __name__ == "__main__":
    # Check for test token
    if TELEGRAM_TOKEN == "7665257525:AAHrv28hH-7FxuJ_CljqLW9gRNCJRGKkKME":
        print("\n⚠️  WARNING: Using PRODUCTION token!")
        print("Recommended: Create test bot via @BotFather")
        print("Commands:")
        print("1. Message @BotFather: /newbot")
        print("2. Name: TL;DR Buddy Test")
        print("3. Username: TLDRBuddy_test_bot")
        print("4. Add TEST_TELEGRAM_TOKEN=<new_token> to .env.test")
        print("\nPress Ctrl+C to stop, or Enter to continue with PRODUCTION token...")
        try:
            input()
        except KeyboardInterrupt:
            sys.exit(0)
    
    asyncio.run(main()) 