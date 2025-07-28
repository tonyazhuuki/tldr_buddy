#!/usr/bin/env python3
"""
OpenAI Whisper API Speech Recognizer for Telegram Voice-to-Insight Pipeline
Implements smart API integration with user preference learning for optimized performance
"""

import asyncio
import json
import logging
import time
import tempfile
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any, BinaryIO

import openai
import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result container for transcription operations"""
    text: str
    language: str
    confidence: float
    processing_time: float


@dataclass
class TranscriptionContext:
    """Context information for transcription requests"""
    user_id: Optional[str] = None
    file_id: Optional[str] = None
    language_hint: Optional[str] = None


class SpeechConfig:
    """Configuration for speech recognition system"""
    
    def __init__(self):
        # OpenAI API Configuration
        self.api_model = "whisper-1"  # whisper-1|gpt-4o-transcribe
        self.api_timeout = 30
        self.api_max_retries = 3
        self.priority_languages = ["ru", "en"]
        self.language_cache_ttl = 30 * 24 * 3600  # 30 days


class UserLanguageCache:
    """Learns and caches user language preferences for performance optimization"""
    
    def __init__(self, redis_client=None, ttl: int = 30 * 24 * 3600):
        self.redis = redis_client
        self.cache_ttl = ttl
        self.memory_cache = {}  # Fallback in-memory cache
        
    async def get_user_language(self, user_id: str) -> Optional[str]:
        """Get user's preferred language from cache"""
        
        cache_key = f"user_lang:{user_id}"
        
        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    
                    lang_data = json.loads(cached_data)
                    # Return language if confidence is high enough
                    if lang_data.get('confidence', 0) > 0.7:
                        logger.debug(f"User {user_id} preferred language: {lang_data['language']}")
                        return lang_data['language']
            except Exception as e:
                logger.warning(f"Redis language cache get failed: {e}")
        
        # Fallback to memory cache
        if user_id in self.memory_cache:
            lang_data = self.memory_cache[user_id]
            if lang_data.get('confidence', 0) > 0.7:
                return lang_data['language']
                
        return None
    
    async def update_user_language(self, 
                                  user_id: str, 
                                  detected_language: str,
                                  confidence: float = 1.0):
        """Update user language preference with exponential moving average"""
        
        cache_key = f"user_lang:{user_id}"
        
        # Get existing data
        existing_data = None
        if self.redis:
            try:
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    if isinstance(cached_data, bytes):
                        cached_data = cached_data.decode('utf-8')
                    existing_data = json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis language cache get failed during update: {e}")
        
        # Fallback to memory cache
        if not existing_data and user_id in self.memory_cache:
            existing_data = self.memory_cache[user_id]
        
        if existing_data:
            if existing_data['language'] == detected_language:
                # Increase confidence for same language
                new_confidence = min(1.0, existing_data['confidence'] * 0.9 + confidence * 0.1)
            else:
                # Reset confidence for different language
                new_confidence = confidence * 0.5
                
            lang_data = {
                'language': detected_language,
                'confidence': new_confidence,
                'last_updated': time.time()
            }
        else:
            # New user
            lang_data = {
                'language': detected_language,
                'confidence': confidence * 0.8,  # Start with lower confidence
                'last_updated': time.time()
            }
        
        # Store in Redis
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(lang_data)
                )
                logger.debug(f"Updated language preference for user {user_id}: "
                           f"{detected_language} (confidence: {lang_data['confidence']:.2f})")
            except Exception as e:
                logger.warning(f"Redis language cache set failed: {e}")
        
        # Store in memory cache as fallback
        self.memory_cache[user_id] = lang_data


class OpenAIAPIClient:
    """Manages OpenAI API client and API calls with error handling"""
    
    def __init__(self, api_key: str, config: SpeechConfig):
        self.client = openai.OpenAI(api_key=api_key)
        self.config = config
        
    async def transcribe_audio(self, 
                              audio_file: BinaryIO, 
                              language: Optional[str] = None,
                              temperature: float = 0.0,
                              bot=None,
                              chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe audio using OpenAI Audio API with enhanced retry logic"""
        
        # Enhanced retry logic: 3 attempts with exponential backoff
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # Prepare transcription parameters
                params = {
                    "file": audio_file,
                    "model": self.config.api_model,
                    "response_format": "verbose_json",
                    "temperature": temperature
                }
                
                # Add language hint if provided
                if language and language in self.config.priority_languages:
                    params["language"] = language
                    logger.debug(f"Using language hint: {language}")
                
                # Make API call
                logger.debug(f"Making OpenAI API call (attempt {attempt + 1})")
                response = self.client.audio.transcriptions.create(**params)
                
                # Extract response data
                result = {
                    "text": response.text,
                    "language": getattr(response, 'language', language or 'unknown'),
                    "duration": getattr(response, 'duration', 0.0)
                }
                
                logger.debug(f"OpenAI API transcription successful: {len(result['text'])} chars")
                return result
                
            except openai.RateLimitError as e:
                # Enhanced rate limit handling with exponential backoff
                if attempt < max_attempts - 1:
                    # Exponential backoff: 1st retry -> 0s, 2nd retry -> 2s, 3rd retry -> 4s
                    delay = 2 ** attempt if attempt > 0 else 0
                    print(f"[ASR Retry] Attempt {attempt + 1}: waiting {delay}s due to rate limit")
                    logger.warning(f"OpenAI rate limit exceeded (attempt {attempt + 1}): {e}")
                    
                    if delay > 0:
                        logger.info(f"Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                else:
                    # After all retries failed, send user message directly if possible
                    logger.error(f"Rate limit exceeded after {max_attempts} attempts")
                    
                    if bot and chat_id:
                        # Send user-friendly message directly to avoid nested errors
                        try:
                            await bot.send_message(chat_id, "⚠️ Распознавание не удалось. Пожалуйста, попробуй позже.")
                            # Raise special exception indicating user was already notified
                            raise UserMessageAlreadySentError()
                        except Exception as send_error:
                            logger.warning(f"Failed to send user message: {send_error}")
                            # Fall back to regular exception if message sending fails
                            raise OpenAISpeechRecognitionError("Rate limit exceeded after retries")
                    else:
                        # No bot reference available, use technical error message
                        raise OpenAISpeechRecognitionError("Rate limit exceeded after retries")
                    
            except openai.APITimeoutError as e:
                logger.warning(f"OpenAI API timeout (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                else:
                    raise OpenAISpeechRecognitionError(f"API timeout after {max_attempts} attempts")
                    
            except openai.APIError as e:
                logger.error(f"OpenAI API error (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                else:
                    raise OpenAISpeechRecognitionError(f"API error after {max_attempts} attempts: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Unexpected error during OpenAI API call: {e}")
                raise OpenAISpeechRecognitionError(f"Unexpected error: {str(e)}")
        
        raise OpenAISpeechRecognitionError("⚠️ Распознавание не удалось. Пожалуйста, попробуй позже.")


class PerformanceMonitor:
    """Monitors and tracks speech recognition performance"""
    
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'total_processing_time': 0.0,
            'api_calls': 0,
            'language_distribution': {},
            'user_metrics': {}
        }
    
    async def record_transcription(self, 
                                  user_id: str,
                                  processing_time: float,
                                  audio_length: int,
                                  detected_language: str,
                                  api_call: bool = True):
        """Record transcription metrics"""
        
        self.metrics['total_requests'] += 1
        self.metrics['total_processing_time'] += processing_time
        
        if api_call:
            self.metrics['api_calls'] += 1
        
        # Update language distribution
        if detected_language not in self.metrics['language_distribution']:
            self.metrics['language_distribution'][detected_language] = 0
        self.metrics['language_distribution'][detected_language] += 1
        
        # Update user metrics
        if user_id not in self.metrics['user_metrics']:
            self.metrics['user_metrics'][user_id] = {
                'requests': 0,
                'total_time': 0.0,
                'avg_time': 0.0
            }
        
        user_stats = self.metrics['user_metrics'][user_id]
        user_stats['requests'] += 1
        user_stats['total_time'] += processing_time
        user_stats['avg_time'] = user_stats['total_time'] / user_stats['requests']
        
        logger.debug(f"Recorded metrics for user {user_id}: "
                    f"{processing_time:.2f}s, language: {detected_language}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        
        avg_time = (self.metrics['total_processing_time'] / 
                   max(1, self.metrics['total_requests']))
        
        return {
            'total_requests': self.metrics['total_requests'],
            'api_calls': self.metrics['api_calls'],
            'average_processing_time': avg_time,
            'language_distribution': self.metrics['language_distribution'],
            'top_users': sorted(
                self.metrics['user_metrics'].items(),
                key=lambda x: x[1]['requests'],
                reverse=True
            )[:5]
        }


class HybridSpeechRecognizer:
    """
    OpenAI API-based speech recognition with user preference learning and performance optimization
    """
    
    def __init__(self, config: SpeechConfig, api_key: str, redis_client=None):
        self.config = config
        self.api_client = OpenAIAPIClient(api_key, config)
        self.language_cache = UserLanguageCache(redis_client, config.language_cache_ttl)
        self.performance_monitor = PerformanceMonitor()
        
    async def initialize(self):
        """Initialize the speech recognition system"""
        
        logger.info("Initializing OpenAI API Speech Recognizer...")
        
        # Verify API access with a simple check
        try:
            # Test API connectivity (no actual transcription)
            logger.info("Verifying OpenAI API access...")
            # Note: We can't easily test without audio, so we'll defer to first actual use
            logger.info("OpenAI API Speech Recognizer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI API client: {e}")
            raise
        
    async def transcribe(self, 
                        audio_data: bytes, 
                        user_id: Optional[str] = None,
                        context: Optional[TranscriptionContext] = None,
                        bot=None,
                        chat_id: Optional[str] = None) -> TranscriptionResult:
        """
        Main transcription method with smart language detection and optimization
        """
        
        start_time = time.time()
        
        try:
            # 1. Get language hint from user preferences or context
            language_hint = await self._get_language_hint(user_id, context)
            
            # 2. Create temporary file for API upload
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                try:
                    # 3. Perform transcription via OpenAI API
                    with open(temp_file.name, "rb") as audio_file:
                        api_result = await self.api_client.transcribe_audio(
                            audio_file=audio_file,
                            language=language_hint,
                            temperature=0.0 if language_hint else 0.2,
                            bot=bot,
                            chat_id=chat_id
                        )
                    
                    # 4. Post-process and cache results
                    result = await self._post_process_result(
                        api_result, user_id, language_hint, start_time
                    )
                    
                    # 5. Monitor performance
                    processing_time = time.time() - start_time
                    if user_id:
                        await self.performance_monitor.record_transcription(
                            user_id, processing_time, len(audio_data), 
                            api_result.get('language', 'unknown'), api_call=True
                        )
                    
                    return result
                    
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_file.name):
                        os.remove(temp_file.name)
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise OpenAISpeechRecognitionError(f"Speech recognition failed: {str(e)}")
    
    async def _get_language_hint(self, 
                               user_id: Optional[str] = None, 
                               context: Optional[TranscriptionContext] = None) -> Optional[str]:
        """Smart language hint detection with user preference learning"""
        
        # Priority 1: User's cached language preference
        if user_id:
            cached_lang = await self.language_cache.get_user_language(user_id)
            if cached_lang and cached_lang in self.config.priority_languages:
                logger.debug(f"Using cached language for user {user_id}: {cached_lang}")
                return cached_lang
        
        # Priority 2: Context hints (if available)
        if context and context.language_hint:
            return context.language_hint
            
        # Default: Auto-detection (no language hint)
        return None
    
    async def _post_process_result(self, 
                                  api_result: Dict[str, Any], 
                                  user_id: Optional[str],
                                  language_hint: Optional[str],
                                  start_time: float) -> TranscriptionResult:
        """Post-process transcription results and update user preferences"""
        
        processing_time = time.time() - start_time
        detected_language = api_result.get('language', 'unknown')
        text = api_result.get('text', '')
        
        # Update user language preference if we have a user and detected language
        if user_id and detected_language and detected_language != 'unknown':
            # Calculate confidence based on text length and language consistency
            confidence = min(1.0, len(text) / 100.0)  # Basic confidence scoring
            
            await self.language_cache.update_user_language(
                user_id, detected_language, confidence
            )
        
        return TranscriptionResult(
            text=text.strip(),
            language=detected_language,
            confidence=1.0,  # OpenAI doesn't provide confidence scores directly
            processing_time=processing_time
        )


class OpenAISpeechRecognitionError(Exception):
    """Custom exception for OpenAI speech recognition errors"""
    
    def __init__(self, message, user_message_sent=False):
        super().__init__(message)
        self.user_message_sent = user_message_sent


class UserMessageAlreadySentError(OpenAISpeechRecognitionError):
    """Special exception indicating user has already been notified of the error"""
    
    def __init__(self, technical_message="Rate limit exceeded - user notified"):
        super().__init__(technical_message, user_message_sent=True)


# Example usage and testing
async def main():
    """Test function for development"""
    
    config = SpeechConfig()
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not api_key:
        print("OPENAI_API_KEY environment variable required for testing")
        return
    
    recognizer = HybridSpeechRecognizer(config, api_key)
    
    print("OpenAI HybridSpeechRecognizer module loaded successfully")
    print("Key components:")
    print("- HybridSpeechRecognizer: Main recognizer with OpenAI API integration")
    print("- UserLanguageCache: User preference learning system")
    print("- OpenAIAPIClient: API client with error handling and retries")
    print("- PerformanceMonitor: Metrics and performance tracking")
    
    await recognizer.initialize()


if __name__ == "__main__":
    asyncio.run(main()) 