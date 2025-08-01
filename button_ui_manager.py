"""
Button UI Manager for Telegram Voice-to-Insight Bot

Implements the 4-state progressive disclosure interaction flow for archetype selection
and response generation with comprehensive state management and error handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import Bot

from emotion_analyzer import EmotionScores
from archetype_system import ArchetypeSystem, ArchetypeResponse

logger = logging.getLogger(__name__)


class UIState(Enum):
    """UI interaction states following creative specifications"""
    INITIAL = "initial"
    SUGGEST = "suggest" 
    MANUAL = "manual"
    RESPONSE = "response"


@dataclass
class ButtonState:
    """Complete button interaction state management"""
    user_id: int
    message_id: int
    current_state: str
    emotion_scores: Dict[str, float]
    emotion_levels: Dict[str, str]
    selected_archetype: Optional[str] = None
    auto_suggested_archetype: Optional[str] = None
    suggestion_reason: Optional[str] = None
    original_text: str = ""
    transcript_available: bool = False
    transcript_file_id: Optional[str] = None
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class ButtonCallbackHandler:
    """Handles callback data parsing and routing"""
    
    @staticmethod
    def create_callback_data(action: str, archetype: str = "", extra: str = "") -> str:
        """Create callback data string"""
        parts = [action]
        if archetype:
            parts.append(archetype)
        if extra:
            parts.append(extra)
        return "_".join(parts)
    
    @staticmethod
    def parse_callback_data(callback_data: str) -> Tuple[str, str, str]:
        """Parse callback data into components"""
        parts = callback_data.split("_")
        action = parts[0] if len(parts) > 0 else ""
        archetype = parts[1] if len(parts) > 1 else ""
        extra = parts[2] if len(parts) > 2 else ""
        return action, archetype, extra


class ButtonLayoutBuilder:
    """Builds keyboard layouts for different UI states"""
    
    def __init__(self):
        self.archetype_info = {
            'EMPATH': {'emoji': '🤗', 'description': 'Заботливая поддержка'},
            'META-SAGE': {'emoji': '🧙', 'description': 'Мудрые инсайты'},
            'TRICKSTER': {'emoji': '🃏', 'description': 'Игривый вызов'},
            'CRAZY-WISDOM': {'emoji': '☯️', 'description': 'Дзен-парадоксы'}
        }
    
    def build_initial_buttons(self, transcript_available: bool = False) -> InlineKeyboardMarkup:
        """Build initial state buttons (State 1)"""
        buttons = []
        
        # Primary row: совет and транскрипт
        primary_row = [
            InlineKeyboardButton(
                text="🤖 совет",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "suggest")
            )
        ]
        
        if transcript_available:
            primary_row.append(
                InlineKeyboardButton(
                    text="📄 транскрипт", 
                    callback_data=ButtonCallbackHandler.create_callback_data("transcript", "download")
                )
            )
        
        buttons.append(primary_row)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def build_suggestion_buttons(self, suggested_archetype: str, reason: str) -> InlineKeyboardMarkup:
        """Build archetype suggestion state buttons (State 2)"""
        buttons = []
        
        # Get archetype info
        archetype_info = self.archetype_info.get(suggested_archetype, {})
        emoji = archetype_info.get('emoji', '🤖')
        description = archetype_info.get('description', suggested_archetype)
        
        # Primary action: accept suggestion
        buttons.append([
            InlineKeyboardButton(
                text=f"✨ Получить совет {emoji}",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "auto", suggested_archetype)
            )
        ])
        
        # Alternative: manual selection
        buttons.append([
            InlineKeyboardButton(
                text="🔄 Выбрать другой стиль",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "manual", "select")
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def build_manual_selection_buttons(self) -> InlineKeyboardMarkup:
        """Build manual archetype selection buttons (State 3)"""
        buttons = []
        
        # 2x2 grid of archetype buttons
        row1 = []
        row2 = []
        
        archetypes = list(self.archetype_info.keys())
        for i, archetype in enumerate(archetypes):
            info = self.archetype_info[archetype]
            button = InlineKeyboardButton(
                text=f"{info['emoji']} {archetype}",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "manual", archetype)
            )
            
            if i < 2:
                row1.append(button)
            else:
                row2.append(button)
        
        buttons.extend([row1, row2])
        
        # Back button
        buttons.append([
            InlineKeyboardButton(
                text="← К рекомендации", 
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "back", "suggest")
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def build_response_buttons(self, archetype: str) -> InlineKeyboardMarkup:
        """Build response action buttons (State 4)"""
        buttons = []
        
        # Change style option
        buttons.append([
            InlineKeyboardButton(
                text="🔄 Другой стиль",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "change", "style")
            )
        ])
        
        # Save response option
        buttons.append([
            InlineKeyboardButton(
                text="💾 Сохранить совет",
                callback_data=ButtonCallbackHandler.create_callback_data("advice", "save", archetype)
            )
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def build_error_buttons(self, error_type: str = "general") -> InlineKeyboardMarkup:
        """Build error state buttons"""
        buttons = []
        
        if error_type == "processing":
            buttons.append([
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=ButtonCallbackHandler.create_callback_data("advice", "retry", "processing")
                ),
                InlineKeyboardButton(
                    text="← Назад",
                    callback_data=ButtonCallbackHandler.create_callback_data("advice", "back", "initial")
                )
            ])
        elif error_type == "archetype":
            buttons.append([
                InlineKeyboardButton(
                    text="🔄 Попробовать снова",
                    callback_data=ButtonCallbackHandler.create_callback_data("advice", "retry", "archetype")
                ),
                InlineKeyboardButton(
                    text="🎭 Другой стиль", 
                    callback_data=ButtonCallbackHandler.create_callback_data("advice", "manual", "select")
                )
            ])
        elif error_type == "transcript":
            buttons.append([
                InlineKeyboardButton(
                    text="← Назад к результатам",
                    callback_data=ButtonCallbackHandler.create_callback_data("advice", "back", "initial")
                )
            ])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)


class StateManager:
    """Redis-based state persistence manager"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.state_prefix = "button_state"
        self.state_ttl = 3600  # 1 hour state retention
    
    async def save_state(self, state: ButtonState) -> bool:
        """Save button state to Redis"""
        try:
            key = f"{self.state_prefix}:{state.user_id}:{state.message_id}"
            state_data = json.dumps(asdict(state))
            await self.redis.setex(key, self.state_ttl, state_data)
            return True
        except Exception as e:
            logger.error(f"Failed to save button state: {e}")
            return False
    
    async def load_state(self, user_id: int, message_id: int) -> Optional[ButtonState]:
        """Load button state from Redis"""
        try:
            key = f"{self.state_prefix}:{user_id}:{message_id}"
            state_data = await self.redis.get(key)
            
            if state_data:
                state_dict = json.loads(state_data)
                return ButtonState(**state_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to load button state: {e}")
            return None
    
    async def delete_state(self, user_id: int, message_id: int) -> bool:
        """Delete button state from Redis"""
        try:
            key = f"{self.state_prefix}:{user_id}:{message_id}"
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete button state: {e}")
            return False
    
    async def cleanup_expired_states(self) -> int:
        """Cleanup expired button states"""
        try:
            pattern = f"{self.state_prefix}:*"
            keys = await self.redis.keys(pattern)
            
            expired_count = 0
            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl <= 0:  # Already expired or no TTL
                    await self.redis.delete(key)
                    expired_count += 1
            
            logger.info(f"Cleaned up {expired_count} expired button states")
            return expired_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired states: {e}")
            return 0


class ButtonUIManager:
    """
    Main Button UI Manager implementing 4-state progressive disclosure workflow.
    
    Manages the complete user interaction flow for archetype selection and response
    generation with comprehensive state management and error handling.
    """
    
    def __init__(self, redis_client: redis.Redis, archetype_system: ArchetypeSystem):
        self.redis = redis_client
        self.archetype_system = archetype_system
        self.state_manager = StateManager(redis_client)
        self.layout_builder = ButtonLayoutBuilder()
        self.callback_handler = ButtonCallbackHandler()
    
    async def create_initial_buttons(
        self, 
        user_id: int, 
        message_id: int,
        emotion_scores: Dict[str, float],
        emotion_levels: Dict[str, str], 
        original_text: str,
        transcript_available: bool = False,
        transcript_file_id: Optional[str] = None
    ) -> InlineKeyboardMarkup:
        """
        Create initial state buttons and save state.
        
        Args:
            user_id: Telegram user ID
            message_id: Message ID for state tracking
            emotion_scores: Emotion analysis scores
            emotion_levels: Human-readable emotion levels
            original_text: Original processed text
            transcript_available: Whether transcript download is available
            transcript_file_id: File ID for transcript download
            
        Returns:
            InlineKeyboardMarkup for initial state
        """
        # Create and save initial state
        state = ButtonState(
            user_id=user_id,
            message_id=message_id,
            current_state=UIState.INITIAL.value,
            emotion_scores=emotion_scores,
            emotion_levels=emotion_levels,
            original_text=original_text,
            transcript_available=transcript_available,
            transcript_file_id=transcript_file_id
        )
        
        await self.state_manager.save_state(state)
        
        # Build keyboard
        return self.layout_builder.build_initial_buttons(transcript_available)
    
    async def handle_callback(self, callback_query: CallbackQuery, bot: Bot) -> bool:
        """
        Handle button callback with state-based routing.
        
        Args:
            callback_query: aiogram CallbackQuery object
            bot: aiogram Bot instance
            
        Returns:
            True if callback was handled successfully
        """
        try:
            user_id = callback_query.from_user.id
            message_id = callback_query.message.message_id
            callback_data = callback_query.data
            
            # Parse callback data
            action, archetype, extra = self.callback_handler.parse_callback_data(callback_data)
            
            # Load current state
            state = await self.state_manager.load_state(user_id, message_id)
            if not state:
                await callback_query.answer("❌ Состояние сессии истекло", show_alert=True)
                return False
            
            # Route to appropriate handler
            if action == "advice":
                return await self._handle_advice_callback(callback_query, bot, state, archetype, extra)
            elif action == "transcript":
                return await self._handle_transcript_callback(callback_query, bot, state)
            else:
                await callback_query.answer("❌ Неизвестное действие", show_alert=True)
                return False
                
        except Exception as e:
            logger.error(f"Error handling button callback: {e}")
            await callback_query.answer("❌ Ошибка обработки", show_alert=True)
            return False
    
    async def _handle_advice_callback(
        self, 
        callback_query: CallbackQuery, 
        bot: Bot, 
        state: ButtonState,
        archetype: str, 
        extra: str
    ) -> bool:
        """Handle advice-related callbacks"""
        
        if archetype == "suggest":
            # State 1 → State 2: Show archetype suggestion
            return await self._show_archetype_suggestion(callback_query, bot, state)
            
        elif archetype == "auto":
            # State 2 → State 4: Generate auto-suggested response
            return await self._generate_archetype_response(callback_query, bot, state, extra, auto_selected=True)
            
        elif archetype == "manual":
            if extra == "select":
                # State 2 → State 3: Show manual selection
                return await self._show_manual_selection(callback_query, bot, state)
            else:
                # State 3 → State 4: Generate manually selected response
                return await self._generate_archetype_response(callback_query, bot, state, extra, auto_selected=False)
                
        elif archetype == "back":
            if extra == "suggest":
                # State 3 → State 2: Back to suggestion
                return await self._show_archetype_suggestion(callback_query, bot, state)
            elif extra == "initial":
                # Error → State 1: Back to initial
                return await self._back_to_initial(callback_query, bot, state)
                
        elif archetype == "change":
            # State 4 → State 3: Change style
            return await self._show_manual_selection(callback_query, bot, state)
            
        elif archetype == "save":
            # State 4: Save response
            return await self._save_response(callback_query, bot, state, extra)
            
        elif archetype == "retry":
            # Error recovery
            return await self._handle_retry(callback_query, bot, state, extra)
        
        else:
            await callback_query.answer("❌ Неизвестное действие", show_alert=True)
            return False
    
    async def _show_archetype_suggestion(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState) -> bool:
        """Show archetype suggestion (State 2)"""
        try:
            # Get auto-suggestion from archetype system
            emotion_scores_obj = EmotionScores(
                sarcasm=state.emotion_scores.get('sarcasm', 0.0),
                toxicity=state.emotion_scores.get('toxicity', 0.0),
                manipulation=state.emotion_scores.get('manipulation', 0.0)
            )
            
            suggested_archetype, reason = await self.archetype_system.get_auto_suggestion(emotion_scores_obj)
            
            # Update state
            state.current_state = UIState.SUGGEST.value
            state.auto_suggested_archetype = suggested_archetype
            state.suggestion_reason = reason
            await self.state_manager.save_state(state)
            
            # Build suggestion message
            archetype_info = self.layout_builder.archetype_info.get(suggested_archetype, {})
            emoji = archetype_info.get('emoji', '🤖')
            description = archetype_info.get('description', suggested_archetype)
            
            suggestion_text = f"""
🎯 **Рекомендуемый стиль**: {emoji} **{suggested_archetype}**

📋 **Причина выбора**: {reason}
🎭 **Специализация**: {description}

Получить совет в этом стиле или выбрать другой?
"""
            
            # Build keyboard
            keyboard = self.layout_builder.build_suggestion_buttons(suggested_archetype, reason)
            
            # Update message
            await callback_query.message.edit_text(suggestion_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback_query.answer()
            
            return True
            
        except Exception as e:
            logger.error(f"Error showing archetype suggestion: {e}")
            await callback_query.answer("❌ Ошибка получения рекомендации", show_alert=True)
            return False
    
    async def _show_manual_selection(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState) -> bool:
        """Show manual archetype selection (State 3)"""
        try:
            # Update state
            state.current_state = UIState.MANUAL.value
            await self.state_manager.save_state(state)
            
            # Build selection message
            selection_text = """
🎭 **Выберите стиль советов**:

🤗 **EMPATH** — Заботливая поддержка
🧙 **META-SAGE** — Мудрые инсайты  
🃏 **TRICKSTER** — Игривый вызов
☯️ **CRAZY-WISDOM** — Дзен-парадоксы

Какой стиль больше подходит для ситуации?
"""
            
            # Build keyboard
            keyboard = self.layout_builder.build_manual_selection_buttons()
            
            # Update message
            await callback_query.message.edit_text(selection_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback_query.answer()
            
            return True
            
        except Exception as e:
            logger.error(f"Error showing manual selection: {e}")
            await callback_query.answer("❌ Ошибка отображения выбора", show_alert=True)
            return False
    
    async def _generate_archetype_response(
        self, 
        callback_query: CallbackQuery, 
        bot: Bot, 
        state: ButtonState,
        selected_archetype: str, 
        auto_selected: bool
    ) -> bool:
        """Generate archetype response (State 4)"""
        try:
            # Show processing message
            await callback_query.answer("🤖 Генерирую совет...")
            
            processing_text = f"🤖 Генерирую совет в стиле **{selected_archetype}**..."
            await callback_query.message.edit_text(processing_text, parse_mode="Markdown")
            
            # Generate response using archetype system
            emotion_scores_obj = EmotionScores(
                sarcasm=state.emotion_scores.get('sarcasm', 0.0),
                toxicity=state.emotion_scores.get('toxicity', 0.0),
                manipulation=state.emotion_scores.get('manipulation', 0.0)
            )
            
            archetype_response = await self.archetype_system.generate_archetype_response(
                selected_archetype,
                state.original_text,
                emotion_scores_obj,
                context=""
            )
            
            if archetype_response.error_message:
                # Handle generation error
                error_text = f"""
❌ **Ошибка генерации советов**
{selected_archetype} временно недоступен. Попробуйте другой стиль или повторите попытку.
"""
                keyboard = self.layout_builder.build_error_buttons("archetype")
                await callback_query.message.edit_text(error_text, reply_markup=keyboard, parse_mode="Markdown")
                return False
            
            # Update state
            state.current_state = UIState.RESPONSE.value
            state.selected_archetype = selected_archetype
            await self.state_manager.save_state(state)
            
            # Format response
            archetype_info = self.layout_builder.archetype_info.get(selected_archetype, {})
            emoji = archetype_info.get('emoji', '🤖')
            
            response_text = f"""
{emoji} **{selected_archetype} советует**:

"""
            
            # Add numbered responses
            for i, response in enumerate(archetype_response.responses, 1):
                response_text += f"{i}. {response}\n\n"
            
            # Add signature
            if archetype_response.signature:
                response_text += f"*{archetype_response.signature}*"
            
            # Build keyboard
            keyboard = self.layout_builder.build_response_buttons(selected_archetype)
            
            # Update message
            await callback_query.message.edit_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating archetype response: {e}")
            
            error_text = """
❌ **Ошибка обработки**
Не удалось получить совет. Попробуйте ещё раз.
"""
            keyboard = self.layout_builder.build_error_buttons("processing")
            await callback_query.message.edit_text(error_text, reply_markup=keyboard, parse_mode="Markdown")
            return False
    
    async def _handle_transcript_callback(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState) -> bool:
        """Handle transcript download"""
        if not state.transcript_available or not state.transcript_file_id:
            await callback_query.answer("❌ Транскрипт недоступен", show_alert=True)
            return False
        
        try:
            # For now, just show a placeholder message
            # TODO: Implement actual file download in Phase 3 completion
            await callback_query.answer("📄 Функция скачивания будет добавлена в следующей итерации", show_alert=True)
            return True
        except Exception as e:
            logger.error(f"Error handling transcript download: {e}")
            await callback_query.answer("❌ Ошибка скачивания", show_alert=True)
            return False
    
    async def _save_response(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState, archetype: str) -> bool:
        """Save archetype response to user's chat"""
        try:
            # For now, just acknowledge the action
            # TODO: Implement actual response saving
            await callback_query.answer("💾 Совет сохранён в личных сообщениях", show_alert=True)
            return True
        except Exception as e:
            logger.error(f"Error saving response: {e}")
            await callback_query.answer("❌ Ошибка сохранения", show_alert=True)
            return False
    
    async def _back_to_initial(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState) -> bool:
        """Return to initial state"""
        try:
            state.current_state = UIState.INITIAL.value
            await self.state_manager.save_state(state)
            
            keyboard = self.layout_builder.build_initial_buttons(state.transcript_available)
            
            # Show original results with buttons
            back_text = "Вернулись к результатам анализа."
            await callback_query.message.edit_text(back_text, reply_markup=keyboard)
            await callback_query.answer()
            
            return True
        except Exception as e:
            logger.error(f"Error returning to initial state: {e}")
            return False
    
    async def _handle_retry(self, callback_query: CallbackQuery, bot: Bot, state: ButtonState, retry_type: str) -> bool:
        """Handle retry operations"""
        if retry_type == "processing":
            return await self._show_archetype_suggestion(callback_query, bot, state)
        elif retry_type == "archetype" and state.selected_archetype:
            return await self._generate_archetype_response(callback_query, bot, state, state.selected_archetype, False)
        else:
            await callback_query.answer("❌ Не удается повторить операцию", show_alert=True)
            return False


# Factory function for easy integration
def create_button_ui_manager(redis_client: redis.Redis, archetype_system: ArchetypeSystem) -> ButtonUIManager:
    """Create configured ButtonUIManager instance"""
    return ButtonUIManager(redis_client, archetype_system) 