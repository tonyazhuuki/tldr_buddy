#!/usr/bin/env python3
"""
Two-Mode Summary Engine (TLDRBuddy)
Handles CHAT and LONGFORM summarization modes with automatic routing
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)


class SummaryMode(Enum):
    """Summary processing modes"""
    CHAT = "chat"
    LONGFORM = "longform"


class ContentType(Enum):
    """Content source types for routing"""
    TELEGRAM_VOICE = "telegram_voice"
    TELEGRAM_VIDEO_NOTE = "telegram_video_note"
    TELEGRAM_AUDIO = "telegram_audio"
    TELEGRAM_DOCUMENT = "telegram_document"
    TELEGRAM_VIDEO = "telegram_video"
    UPLOADED_URL = "uploaded_url"
    TEXT_INPUT = "text_input"


@dataclass
class SummaryConfig:
    """Configuration for summary processing"""
    mode: SummaryMode
    model: str
    max_tokens: int
    temperature: float
    frequency_penalty: float
    reasoning_effort: Optional[str] = None


@dataclass
class SummaryResult:
    """Result of summary processing"""
    success: bool
    summary: Optional[str] = None
    mode: Optional[SummaryMode] = None
    processing_time: Optional[float] = None
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    confidence: Optional[float] = None


class SummaryEngine:
    """
    Two-mode summary engine for TLDRBuddy
    Handles automatic routing between CHAT and LONGFORM modes
    """
    
    def __init__(self, openai_client: Optional[OpenAI] = None):
        self.client = openai_client
        
        # Default configurations for each mode
        self.configs = {
            SummaryMode.CHAT: SummaryConfig(
                mode=SummaryMode.CHAT,
                model="gpt-5-mini",
                max_tokens=1100,
                temperature=0.25,
                frequency_penalty=0.2,
                reasoning_effort="minimal"
            ),
            SummaryMode.LONGFORM: SummaryConfig(
                mode=SummaryMode.LONGFORM,
                model="gpt-5-mini",
                max_tokens=1500,
                temperature=0.25,
                frequency_penalty=0.2,
                reasoning_effort="minimal"
            )
        }
        
        # Content type to mode routing
        self.content_routing = {
            ContentType.TELEGRAM_VOICE: SummaryMode.CHAT,
            ContentType.TELEGRAM_VIDEO_NOTE: SummaryMode.CHAT,
            ContentType.TELEGRAM_AUDIO: SummaryMode.CHAT,
            ContentType.TELEGRAM_DOCUMENT: SummaryMode.LONGFORM,
            ContentType.TELEGRAM_VIDEO: SummaryMode.LONGFORM,
            ContentType.UPLOADED_URL: SummaryMode.LONGFORM,
            ContentType.TEXT_INPUT: SummaryMode.CHAT  # Default for text
        }
        
        # System prompts for each mode
        self.system_prompts = {
            SummaryMode.CHAT: self._get_chat_system_prompt(),
            SummaryMode.LONGFORM: self._get_longform_system_prompt()
        }
        
        # Feature flag for enabling new functionality
        self.enabled = os.getenv('TLDRBUDDY_ENABLED', 'false').lower() == 'true'
        
        logger.info(f"SummaryEngine initialized, enabled: {self.enabled}")
    
    def _get_chat_system_prompt(self) -> str:
        """Get system prompt for CHAT mode"""
        from datetime import datetime
        import pytz
        
        # Get current date in Europe/Amsterdam timezone
        amsterdam_tz = pytz.timezone('Europe/Amsterdam')
        today_iso = datetime.now(amsterdam_tz).strftime('%Y-%m-%d')
        
        return f"""Ты — TLDRBuddy. Пиши на языке входа (если смесь — русский). Не выдумывай факты и ссылки.
Если вход пуст/шум/музыка без речи — верни: «🧯 НЕ АНАЛИЗИРУЮ: [причина]».

ДАТЫ/ЧИСЛА:
— Всегда выделяй отдельным блоком «ДАННЫЕ/ЦИФРЫ».
— Подсвечивай: относительные даты («сегодня», «завтра», «15-го»), абсолютные даты, суммы, проценты, количества, диапазоны.
— Нормализуй относительные даты к ISO (YYYY-MM-DD), используя опорную дату {today_iso} и часовой пояс Europe/Amsterdam. 
  Пример: «завтра» → {today_iso}+1; «15-го» → ближайшее будущее 15 число (если месяц не указан и неочевидно — пометь «месяц не указан» и укажи обе версии).
— Если нормализация двусмысленна — отдай и сырое, и нормализованное (с пометкой «неоднозначно»).

СТРУКТУРА:
— Не оставляй пустые секции. Если фактов нет — пиши «нет».
— Запрещены пустые фразы типа «Основные темы выделены».
— В «ДЕЙСТВИЯХ» не придумывай задачи. Если явных действий нет — напиши «нет».

Проанализируй текст/транскрипт ниже. Коротко и предметно. Язык ответа = язык входа.
Опорная дата: {today_iso} (Europe/Amsterdam).

Формат:
📝 РЕЗЮМЕ: 1–2 предложения — суть сообщения
📍 ОСНОВНЫЕ ПУНКТЫ (3–7): • конкретный факт/намерение/договорённость
📊 ДАННЫЕ/ЦИФРЫ:
• [тип] — [значение] — [контекст/цитата]
⚡ ДЕЙСТВИЯ: 
• [императив, измеримо] [— владелец/роль] [— срок] [— P1|P2|P3]
Если явных действий нет — «нет»
🎭 ТОН/ЭМОЦИИ: 1–3 слова (напр.: тёплый, усталость, воодушевление)

Правила:
- Убирай повторы, не пиши общие слова.
- В «ОСНОВНЫХ ПУНКТАХ» обязателен смысл: кто/что/когда; без «вода/про вид».
- Даты/числа всегда дублируй в «ДАННЫЕ/ЦИФРЫ» (с нормализацией, см. SYSTEM).
- Таймкоды используй только если они есть в тексте; не придумывай."""
    
    def _get_longform_system_prompt(self) -> str:
        """Get system prompt for LONGFORM mode"""
        return """Ты — TLDRBuddy. Не выдумывай факты и ссылки. Отвечай на языке входа; если он смешанный — русский.
Если вход пуст/шум/музыка без речи — возвращай короткое объяснение «НЕ АНАЛИЗИРУЮ: [причина]».
Если в тексте нет явных «действий» — так и пиши, раздел не наполняй мусором.
Цифры/данные — всегда выделяй отдельно (проценты, суммы, количества, даты, метрики). Нормализуй единицы, но не придумывай.
Таймкоды используй только если явно есть в тексте/транскрипте. Не выдумывай таймкоды.
В JSON-режимах — только JSON по схеме, ничего снаружи.

Анализируй материал (лекция/подкаст/интервью/рандомное аудио-видео). Не выдумывай. Язык ответа = язык входа.

🧠 **ТЕЗИС**: 1–2 предложения — суть материала
🔑 **КЛЮЧЕВЫЕ ИДЕИ (5–9)**: • коротко, без воды
🗺️ **СТРУКТУРА/СЕГМЕНТЫ**:
• [Название сегмента] — 1 строка смысла
(Таймкоды используй только если есть в тексте; если нет — не придумывай.)
⚖️ **АРГУМЕНТЫ ↔ ВОЗРАЖЕНИЯ**:
• тезис → факты/примеры из текста
• контртезис (если звучит) → факты/пример
📊 **ДАННЫЕ/ЦИФРЫ**:
• метрика — значение — контекст (проценты, суммы, кол-ва, даты, шаги/скорости/диапазоны)
📚 **ГЛОССАРИЙ (до 10)**: «термин — простое пояснение по тексту»
💬 **ЦИТАТЫ (3–7)**: «короткая точная цитата»
🧩 **НЕЯСНО**: важные вопросы, на которые материал не отвечает
🎛 **УВЕРЕННОСТЬ**: 0.0–1.0"""
    
    def determine_mode(self, 
                      content_type: ContentType, 
                      text: Optional[str] = None,
                      duration: Optional[int] = None) -> SummaryMode:
        """
        Determine summary mode based on content type and heuristics
        
        Args:
            content_type: Type of content source
            text: Transcribed text for heuristics
            duration: Duration in seconds for heuristics
            
        Returns:
            SummaryMode to use
        """
        # Primary routing by content type
        primary_mode = self.content_routing.get(content_type, SummaryMode.CHAT)
        
        # Apply heuristics if we have text or duration
        if text or duration:
            # Duration heuristic: > 10 minutes → LONGFORM
            if duration and duration > 600:  # 10 minutes
                logger.info(f"Duration heuristic: {duration}s > 600s, switching to LONGFORM")
                return SummaryMode.LONGFORM
            
            # Text length heuristic: > 1500 words → LONGFORM
            if text:
                word_count = len(text.split())
                if word_count > 1500:
                    logger.info(f"Text length heuristic: {word_count} words > 1500, switching to LONGFORM")
                    return SummaryMode.LONGFORM
                
                # Dialog style heuristic: if many "я/ты/мы" and from URL → can force CHAT
                if content_type == ContentType.UPLOADED_URL:
                    dialog_indicators = len(re.findall(r'\b(я|ты|мы|вы|он|она|они)\b', text, re.IGNORECASE))
                    if dialog_indicators > 10:  # High dialog indicator
                        logger.info(f"Dialog style heuristic: {dialog_indicators} dialog indicators, keeping CHAT")
                        return SummaryMode.CHAT
        
        logger.info(f"Using primary mode {primary_mode} for content type {content_type}")
        return primary_mode
    
    async def process_summary(self, 
                            text: str,
                            content_type: ContentType,
                            duration: Optional[int] = None,
                            force_mode: Optional[SummaryMode] = None) -> SummaryResult:
        """
        Process text through appropriate summary mode
        
        Args:
            text: Text to summarize
            content_type: Type of content source
            duration: Duration in seconds (for heuristics)
            force_mode: Force specific mode (for testing)
            
        Returns:
            SummaryResult with processing results
        """
        if not self.enabled:
            logger.warning("SummaryEngine is disabled, returning error")
            return SummaryResult(
                success=False,
                error_message="SummaryEngine is disabled"
            )
        
        if not self.client:
            logger.warning("OpenAI client not available, returning error")
            return SummaryResult(
                success=False,
                error_message="OpenAI client not available"
            )
        
        start_time = time.time()
        
        try:
            # Determine mode
            if force_mode:
                mode = force_mode
                logger.info(f"Using forced mode: {mode}")
            else:
                mode = self.determine_mode(content_type, text, duration)
            
            # Get configuration for mode
            config = self.configs[mode]
            system_prompt = self.system_prompts[mode]
            
            logger.info(f"Processing summary in {mode} mode with {config.model}")
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Материал:\n{text}"}
            ]
            
            # Prepare parameters
            params = {
                "model": config.model,
                "messages": messages,
                "max_completion_tokens": config.max_tokens
            }
            
            # Add optional parameters only if they're supported
            # Note: temperature and frequency_penalty may not be supported by all models
            # Add reasoning effort if specified
            if config.reasoning_effort:
                params["reasoning_effort"] = config.reasoning_effort
            
            # Call OpenAI API
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                **params
            )
            
            # Extract result
            summary = response.choices[0].message.content
            token_count = response.usage.total_tokens if response.usage else None
            
            processing_time = time.time() - start_time
            
            logger.info(f"Summary completed in {processing_time:.2f}s, "
                       f"tokens: {token_count}, mode: {mode}")
            
            return SummaryResult(
                success=True,
                summary=summary,
                mode=mode,
                processing_time=processing_time,
                token_count=token_count,
                confidence=0.9  # Default confidence
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Summary processing failed: {e}")
            
            return SummaryResult(
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
    
    def get_fallback_response(self, text: str) -> str:
        """
        Get fallback response when processing fails
        
        Args:
            text: Original text
            
        Returns:
            Fallback response
        """
        # Check if text is empty/noise/music
        if not text or len(text.strip()) < 10:
            return "🧯 НЕ АНАЛИЗИРУЮ: Пустой или неразборчивый контент"
        
        # Check for noise indicators
        noise_indicators = ["шум", "музыка", "звук", "noise", "music", "sound"]
        text_lower = text.lower()
        if any(indicator in text_lower for indicator in noise_indicators):
            return "🧯 НЕ АНАЛИЗИРУЮ: Музыка или шум без речи"
        
        # Default fallback
        return f"""🧯 НЕ АНАЛИЗИРУЮ: Ошибка обработки

Контент:
{text[:200]}{'...' if len(text) > 200 else ''}"""
    
    def update_config(self, mode: SummaryMode, **kwargs) -> None:
        """
        Update configuration for a specific mode
        
        Args:
            mode: Mode to update
            **kwargs: Configuration parameters to update
        """
        if mode not in self.configs:
            logger.error(f"Unknown mode: {mode}")
            return
        
        config = self.configs[mode]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
                logger.info(f"Updated {mode} config: {key} = {value}")
            else:
                logger.warning(f"Unknown config parameter: {key}")
    
    def enable(self) -> None:
        """Enable the summary engine"""
        self.enabled = True
        logger.info("SummaryEngine enabled")
    
    def disable(self) -> None:
        """Disable the summary engine"""
        self.enabled = False
        logger.info("SummaryEngine disabled")


# Factory function for creating SummaryEngine
def create_summary_engine(openai_client: Optional[OpenAI] = None) -> SummaryEngine:
    """
    Create and configure SummaryEngine instance
    
    Args:
        openai_client: OpenAI client instance
        
    Returns:
        Configured SummaryEngine instance
    """
    return SummaryEngine(openai_client) 